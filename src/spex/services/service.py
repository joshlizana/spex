import signal
import threading
import time

from multiprocessing import connection, get_context

SpawnProcess = get_context("spawn").Process


class ServiceProcess(SpawnProcess):
    """Provide shared process lifecycle and Hub control for worker services."""

    def __init__(self, pipe: connection.Connection):
        super().__init__()
        self._pipe: connection.Connection = pipe
        self._shutdown: bool = False
        self._telemetry_snapshot: dict | None = None
        self._phase: str = "live"

    def run(self) -> None:
        """Run service work while monitoring the pipe for Hub loss."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        pipe_thread = threading.Thread(target=self.pipe_thread, daemon=True)
        telemetry_thread = threading.Thread(target=self._reporter, daemon=True)
        try:
            pipe_thread.start()
            telemetry_thread.start()
            try:
                while not self._shutdown:
                    # Observe shutdown after each bounded unit of work.
                    self._run_cycle()
            finally:
                self._shutdown = True
                pipe_thread.join()
                telemetry_thread.join()
        finally:
            self._pipe.close()

    def _reporter(self) -> None:
        """Send a telemetry report to the Hub."""
        while not self._shutdown:
            phase = self._phase
            if self._telemetry_snapshot is not None:
                self._pipe.send(
                    {
                        "type": "telemetry",
                        "payload": self._telemetry_snapshot,
                    }
                )
            time.sleep(0.25)
            if phase != self._phase:
                self._pipe.send(
                    {
                        "type": "state",
                        "payload": {
                            "running": True,
                            "phase": self._phase,
                        },
                    }
                )

    def pipe_thread(self) -> None:
        """Monitor the service control-plane pipe."""
        while not self._shutdown:
            try:
                if self._pipe.poll(timeout=0.1):
                    message = self._pipe.recv()
                    # Worker pipes carry no Hub commands in M0.
            except (EOFError, OSError):
                self._shutdown = True

    def _signal_handler(self, signum, frame) -> None:
        """Handle signals sent to the service process."""
        if signum in (signal.SIGTERM, signal.SIGINT):
            # Record the request; run() checks this after the current cycle.
            self._shutdown = True

    def _run_cycle(self) -> None:
        """Perform one bounded unit of service-specific work."""
        raise NotImplementedError("Subclasses must implement this method.")
