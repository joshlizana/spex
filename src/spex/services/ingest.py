import threading
import time

from collections import deque
from multiprocessing import connection

from spex.services.service import ServiceProcess


class IngestionService(ServiceProcess):
    """Represent the Jetstream replay and live ingestion scaffold."""

    def __init__(self, pipe: connection.Connection):
        super().__init__(pipe)
        self._events_received: int = 0
        self._events_received_past_ten_seconds: deque = deque([])
        self._events_per_second: float = 0.0
        self._cycle_stop: bool = False

    def _run_cycle(self) -> None:
        """Run one cycle of the ingestion service."""
        self._cycle_stop = False
        telemetry_thread = threading.Thread(
            target=self._telemetry_snap,
            daemon=True,
        )
        telemetry_thread.start()

        # Keep the scaffold alive while the service is running.
        self._events_received += 1
        self._events_received_past_ten_seconds.append(time.time())
        self._throughput()
        time.sleep(0.1)
        # Join the telemetry thread after this bounded work cycle completes.
        self._cycle_stop = True
        telemetry_thread.join()

    def _phase_change(self, new_phase: str) -> None:
        """Change the current ingestion service phase."""
        self._phase = new_phase

    def _throughput(self) -> None:
        """Update the current ingestion service throughput."""
        while (
            self._events_received_past_ten_seconds
            and self._events_received_past_ten_seconds[0]
            < time.time() - 10.0
        ):
            self._events_received_past_ten_seconds.popleft()

        self._events_per_second = len(self._events_received_past_ten_seconds) / 10.0

    def _telemetry_snap(self) -> None:
        """Update snapshot of the ingestion service telemetry."""
        while not self._shutdown and not self._cycle_stop:
            self._telemetry_snapshot = {
                "events_received": self._events_received,
                "events_per_second": self._events_per_second,
            }
            time.sleep(0.25)
