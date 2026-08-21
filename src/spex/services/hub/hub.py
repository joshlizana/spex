import multiprocessing
import threading
import time
import uuid
from contextlib import ExitStack

import orjson

from spex.services.backfill.backfill import BackfillService
from spex.services.hub.ipc_listener import HubListener
from spex.services.lock import Lock
from spex.services.live.live import LiveService


class Hub:
    """Represent the main-process Spex Hub scaffold."""

    def __init__(self):
        self._running: bool = True
        self._hub_listener: HubListener | None = None
        self._hub_listener_thread: threading.Thread | None = None
        self._instance_id: str = str(uuid.uuid4())
        self._session_id: str = self._instance_id
        self._lock: Lock | None = None
        self._live_service: LiveService | None = None
        self._backfill_service: BackfillService | None = None
        self._spawn_context: multiprocessing.context.SpawnContext = (
            multiprocessing.get_context("spawn")
        )
        self._address: str | None = None
        self._authkey: bytes | None = None
        self._resources: ExitStack = ExitStack()

    def __enter__(self):
        with ExitStack() as stack:
            lock = Lock("hub", self._session_id, self._instance_id)
            lock.acquire()
            stack.callback(lock.release)

            listener = stack.enter_context(HubListener())
            address = listener.address
            authkey = listener.authkey

            listener_thread = threading.Thread(target=listener.run)
            listener_thread.start()

            self._lock = lock
            self._hub_listener = listener
            self._hub_listener_thread = listener_thread
            self._address = address
            self._authkey = authkey
            self._resources = stack.pop_all()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self._resources:
            self._running = False
            self._hub_listener_shutdown()
            self._hub_listener_thread.join()
            self._join()

    def run(self):
        """Run the Spex Hub supervision loop."""

        while self._running:
            # Reserve this branch for process supervision and IPC work.
            time.sleep(1)

    def _spawn(self, service: str):
        """Spawn a new instance of a Spex spoke service."""

        if service == "live":
            if not self._live_service or not self._live_service.is_alive():
                self._live_service = LiveService()
                self._live_service.start()
        elif service == "backfill":
            if not self._backfill_service or not self._backfill_service.is_alive():
                self._backfill_service = BackfillService()
                self._backfill_service.start()
        else:
            # Surface unsupported roles until structured logging is available.
            raise ValueError(f"Unknown service: {service}")

    def _join(self):
        """Join all child processes."""
        if self._live_service and self._live_service.is_alive():
            self._live_service.join()
        if self._backfill_service and self._backfill_service.is_alive():
            self._backfill_service.join()

    def _hub_listener_shutdown(self):
        """Send the message that stops the Hub listener."""
        if self._hub_listener is not None:
            conn = multiprocessing.connection.Client(
                self._address,
                authkey=self._authkey,
            )
            conn.send_bytes(
                orjson.dumps(
                    {
                        "message_type": "shutdown",
                        "message_id": None,
                        "payload": {},
                    }
                )
            )
            conn.close()
