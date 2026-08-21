import multiprocessing.connection
import time
from collections.abc import Callable
from contextlib import ExitStack
from multiprocessing.connection import Client

import orjson

from spex.services.lock import Lock


class ServiceClient:
    """Connect a service spoke to the Spex Hub control plane."""

    def __init__(
        self,
        service: str,
        session_id: str,
        instance_id: str,
        address: str,
        authkey: bytes,
        _state: Callable,
        _stop: Callable,
        _pause: Callable,
        _resume: Callable,
    ):
        self._lock: Lock | None = None
        self._active: bool = True
        self._address: str = address
        self._authkey: bytes = authkey
        self._stop: Callable[[], None] = _stop
        self._pause: Callable[[], None] = _pause
        self._resume: Callable[[], None] = _resume
        self._state: Callable[[], dict[str, bool]] = _state
        self._conn: multiprocessing.connection.Connection | None = None
        self._session_id: str = session_id
        self._instance_id: str = instance_id
        self._role: str = service
        self._resources: ExitStack = ExitStack()

    def __enter__(self):
        with ExitStack() as stack:
            lock = Lock(self._role, self._session_id, self._instance_id)
            lock.acquire()
            stack.callback(lock.release)
            stack.callback(self._stop)
            stack.callback(self._close_connection)
            stack.callback(lambda: setattr(self, "_active", False))

            self._hello()

            self._lock = lock
            self._resources = stack.pop_all()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._resources.close()


    def run(self):
        """Run the Spex client."""

        retry = 0
        while self._active:
            try:
                if self._conn.poll(timeout=2**retry):
                    message = self._conn.recv_bytes()
                    message = self._open_message(message)
                    self._message_control(message)
                    retry = 0
                else:
                    retry += 1
                    if retry > 3:
                        raise RuntimeError(
                            "Lost connection to Spex Hub. Shutting down service client."
                        )
            except (ValueError, EOFError, OSError):
                raise RuntimeError(
                    "Lost connection to Spex Hub. Shutting down service client."
                )

    def _open_message(self, message: bytes):
        """Open a message from the Spex Hub."""

        try:
            msg = orjson.loads(message)
        except orjson.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON message: {e}")

        return msg

    def _message_control(self, message: dict):
        """Handle control messages from the Spex Hub."""

        message_type = message.get("message_type")
        message_id = message.get("message_id")

        match message_type:
            case "hello_ack":
                # The hello_ack message is handled in the _hello method.
                self._send_state(message_id)
            case "stop":
                self._active = False
            case "pause":
                self._pause()
                self._send_state(message_id)
            case "resume":
                self._resume()
                self._send_state(message_id)
            case "state":
                self._send_state(message_id)
            case "heartbeat":
                self._conn.send_bytes(
                    orjson.dumps(
                        {
                            "message_type": "heartbeat_ack",
                            "message_id": message_id,
                            "payload": {},
                        }
                    )
                )
            case _:
                self._conn.send_bytes(
                    orjson.dumps(
                        {
                            "message_type": "error",
                            "message_id": message_id,
                            "payload": {
                                "error": f"Unknown message type: {message_type}"
                            },
                        }
                    )
                )

    def _close_connection(self):
        """Close the active IPC connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _hello(self):
        """Identify the service to the Hub and await acknowledgment."""

        for retry in range(4):
            started = time.monotonic()
            timeout = 2**retry
            success = False
            try:
                if self._hello_attempt(timeout):
                    success = True
                    return
            except (
                OSError,
                EOFError,
                ValueError,
                multiprocessing.connection.AuthenticationError,
            ):
                # Reserve connection-failure and retry diagnostics for structured logging.
                pass
            finally:
                if not success:
                    self._close_connection()
                    remaining_timeout = timeout - (time.monotonic() - started)
                    if remaining_timeout > 0:
                        time.sleep(remaining_timeout)

        raise RuntimeError("No acknowledgment received from Spex Hub.")

    def _hello_attempt(self, timeout) -> bool:
        """Perform one Hub connection and hello exchange."""

        message: dict | None = None
        self._conn = Client(self._address, authkey=self._authkey)
        self._send_hello()

        if self._conn.poll(timeout=timeout):
            message = self._open_message(self._conn.recv_bytes())

        if not message or message.get("message_type") != "hello_ack":
            return False

        self._resume()
        self._send_state(message.get("message_id"))
        return True

    def _send_hello(self):
        """Send the hello message to the Spex Hub."""
        self._conn.send_bytes(
            orjson.dumps(
                {
                    "message_type": "hello",
                    "message_id": None,
                    "payload": {
                        "protocol_version": 1,
                        "role": self._role,
                        "session_id": self._session_id,
                        "instance_id": self._instance_id,
                    },
                }
            )
        )

    def _send_state(self, message_id: str | None):
        """Send the current state of the service to the Hub."""

        state = self._state()
        self._conn.send_bytes(
            orjson.dumps(
                {
                    "message_type": "state",
                    "message_id": message_id,
                    "payload": state,
                }
            )
        )
