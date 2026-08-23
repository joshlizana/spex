import time

from multiprocessing import connection, get_context

SpawnProcess = get_context("spawn").Process


class DashboardService(SpawnProcess):
    """Represent the dashboard service scaffold."""

    def __init__(self, pipe: connection.Connection):
        super().__init__()
        self._pipe: connection.Connection = pipe
        self._shutdown: bool = False

    def run(self):
        """Run dashboard work, releasing the Hub pipe on exit."""
        try:
            # Run dashboard work.
            pass
        finally:
            self._pipe.close()
