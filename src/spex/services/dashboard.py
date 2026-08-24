import threading
import time

from multiprocessing import connection, get_context

SpawnProcess = get_context("spawn").Process


class DashboardService(SpawnProcess):
    """Represent the dashboard service scaffold."""

    def __init__(self, pipe: connection.Connection):
        super().__init__()
        self._pipe: connection.Connection = pipe
        self._shutdown: bool = False

    def run(self) -> None:
        """Run dashboard work, releasing the Hub pipe on exit."""
        pipe_thread = threading.Thread(target=self.pipe_thread, daemon=True)
        try:
            # Run dashboard work.
            pipe_thread.start()
            try:
                while not self._shutdown:
                    time.sleep(0.1)
            finally:
                self._shutdown = True
                pipe_thread.join()
        finally:
            self._pipe.close()

    def pipe_thread(self) -> None:
        """Monitor the dashboard control-plane pipe."""
        while not self._shutdown:
            try:
                if self._pipe.poll(timeout=0.1):
                    message = self._pipe.recv()
                    # Dashboard receives no application messages in M0.
            except (EOFError, OSError):
                self._shutdown = True
