import multiprocessing.connection
import threading
import uuid
from multiprocessing.connection import Listener
from pathlib import Path

import orjson

from spex.config import SpexConfig


class HubListener:
    """Represent the IPC listener for the Spex Hub."""

    def __init__(self):
        self._active: bool = True
        self._address: str = str(
            SpexConfig().config.runtime_dir / "ipc" / "hub.port"
        )
        self._authkey: bytes = str(uuid.uuid4()).encode("utf-8")
        self._listener: Listener | None = None
        self._handlers: list[threading.Thread] = []
        self._handlers_lock: threading.Lock = threading.Lock()

    def __enter__(self):
        self._listener = Listener(self._address, authkey=self._authkey)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        handlers = []
        # Snapshot under the lock, then join without blocking handler publication.
        with self._handlers_lock:
            if self._handlers:
                handlers = self._handlers[:]
        for handler in handlers:
            handler.join()

        if self._listener is not None:
            self._listener.close()
            self._listener = None
        Path(self._address).unlink(missing_ok=True)

    @property
    def address(self) -> str:
        """Return the IPC address for the Spex Hub."""
        return self._address

    @property
    def authkey(self) -> bytes:
        """Return the authentication key for the Spex Hub."""
        return self._authkey

    def run(self):
        """Run the IPC listener for the Spex Hub."""
        if self._listener is None:
            raise RuntimeError("Listener is not initialized.")
        while self._active:
            try:
                conn = self._listener.accept()
                message = self._decode_message(conn)
                if message is None:
                    conn.close()
                    continue
                message_type = message.get("message_type")
                match message_type:
                    case "shutdown":
                        self._active = False
                        conn.close()
                        break
                    case "hello":
                        handler_thread = threading.Thread(
                            target=self._handle_connection,
                            args=(conn, message),
                        )
                        # Publish only a successfully started handler.
                        with self._handlers_lock:
                            handler_thread.start()
                            self._handlers.append(handler_thread)
                    case _:
                        # Record unrecognized messages when logging is available.
                        conn.close()
            except multiprocessing.connection.AuthenticationError:
                # Record authentication failures when logging is available.
                pass

    def _handle_connection(
        self,
        conn: multiprocessing.connection.Connection,
        initial_message: dict,
    ):
        """Handle messages for one persistent client connection."""
        with conn:
            self._handle_message(conn, initial_message)
            while self._active:
                # Bound the wait so the handler observes listener shutdown.
                if not conn.poll(timeout=1):
                    continue
                message = self._decode_message(conn)
                if message is None:
                    break
                self._handle_message(conn, message)

    def _decode_message(self, conn: multiprocessing.connection.Connection):
        """Receive and decode one message from a client connection."""
        try:
            message = orjson.loads(conn.recv_bytes())
            return message
        except (orjson.JSONDecodeError, OSError, EOFError):
            return None

    def _handle_message(
        self,
        conn: multiprocessing.connection.Connection,
        message: dict,
    ):
        """Dispatch one decoded message from a client connection."""
        message_type = message.get("message_type")
        match message_type:
            case "hello":
                conn.send_bytes(
                    orjson.dumps(
                        {
                            "message_type": "hello_ack",
                            "message_id": None,
                            "payload": {},
                        }
                    )
                )
            case _:
                # Record unrecognized messages when logging is available.
                pass
