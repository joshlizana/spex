import signal
from multiprocessing import connection, get_context

SpawnProcess = get_context("spawn").Process


class ServiceProcess(SpawnProcess):
    """Provide shared process lifecycle and Hub control for worker services."""

    def __init__(self, pipe: connection.Connection):
        super().__init__()
        self._pipe: connection.Connection = pipe
        self._shutdown: bool = False

    def run(self):
        """Run service work, polling the pipe for Hub loss between cycles."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        try:
            while True:
                # Return to control-state evaluation after each bounded unit.
                self._run_cycle()
                if self._pipe.poll() or self._shutdown:
                    break
        finally:
            self._pipe.close()

    def _run_cycle(self) -> None:
        """Perform one bounded unit of service-specific work."""
        raise NotImplementedError("Subclasses must implement this method.")

    def _signal_handler(self, signum, frame):
        """Handle signals sent to the service process."""
        if signum in (signal.SIGTERM, signal.SIGINT):
            # Record the request; run() checks this after the current cycle.
            self._shutdown = True
