import threading
import time
from multiprocessing import connection, get_context

SpawnProcess = get_context("spawn").Process


class ServiceProcess(SpawnProcess):
    """Provide shared process lifecycle and Hub control for worker services."""

    def __init__(self, pipe: connection.Connection):
        super().__init__()
        self._running: bool = True
        self._paused: bool = False
        self._pipe: connection.Connection = pipe
        self._receive_thread: threading.Thread | None = None
        self._receive_thread_shutdown_event: threading.Event | None = None
        self._receive_thread_error: Exception | None = None
        self._send_lock: threading.Lock | None = None

    def run(self):
        """Run service work alongside the Hub control receiver."""

        # Keep the scaffold alive while the service is running.
        try:
            self._send_lock = threading.Lock()
            self._receive_thread_shutdown_event = threading.Event()
            self._receive_thread = threading.Thread(target=self._receive)
            self._receive_thread.start()
            while self._running and not self._receive_thread_shutdown_event.is_set():
                if self._running and not self._paused:
                    # Return to control-state evaluation after each bounded unit.
                    self._run_cycle()
                if self._running and self._paused:
                    time.sleep(0.1)
        finally:
            self._stop()
            if self._receive_thread_shutdown_event is not None:
                self._receive_thread_shutdown_event.set()
            if self._receive_thread is not None:
                self._receive_thread.join()
            self._pipe.close()

        if self._receive_thread_error is not None:
            raise self._receive_thread_error

    def _run_cycle(self) -> None:
        """Perform one bounded unit of service-specific work."""
        raise NotImplementedError("Subclasses must implement this method.")

    def _send(self, message: dict):
        """Send a message to the parent process."""
        with self._send_lock:
            try:
                self._pipe.send(message)
            except (EOFError, OSError):
                self._stop()
                self._receive_thread_shutdown_event.set()
            except Exception as e:
                self._stop()
                self._receive_thread_shutdown_event.set()
                self._receive_thread_error = e

    def _handle_message(self, message: dict):
        """Reject a message type unless a subclass implements it."""
        raise ValueError(f"Unknown message type: {message['type']}")

    def _receive(self):
        """Receive messages from the parent process."""
        while self._running and not self._receive_thread_shutdown_event.is_set():
            try:
                if self._pipe.poll(0.1):
                    message = self._pipe.recv()
                    if message["type"] == "pause":
                        self._pause()
                        self._send(self._state(message["message_id"]))
                    elif message["type"] == "resume":
                        self._resume()
                        self._send(self._state(message["message_id"]))
                    elif message["type"] == "stop":
                        self._stop()
                        self._send(self._state(message["message_id"]))
                    elif message["type"] == "state_request":
                        self._send(self._state(message["message_id"]))
                    else:
                        self._handle_message(message)
            except (EOFError, OSError):
                self._stop()
                self._receive_thread_shutdown_event.set()
            except Exception as e:
                self._stop()
                self._receive_thread_shutdown_event.set()
                self._receive_thread_error = e

    def _pause(self):
        """Pause service work while keeping Hub control responsive."""
        if not self._paused:
            self._paused = True

    def _resume(self):
        """Resume service work."""
        if self._paused:
            self._paused = False

    def _stop(self):
        """Stop service work and its Hub control receiver."""
        if self._running:
            self._running = False


    def _state(self, message_id: str):
        """Return the current operational state in a correlated envelope."""
        if self._running and not self._paused:
            return {
                "type": "state",
                "message_id": message_id,
                "payload": {"running": True, "paused": False},
            }
        elif self._running and self._paused:
            return {
                "type": "state",
                "message_id": message_id,
                "payload": {"running": True, "paused": True},
            }
        elif not self._running:
            return {
                "type": "state",
                "message_id": message_id,
                "payload": {"running": False, "paused": False},
            }
