import threading
import time

from collections import deque
from multiprocessing import connection

from spex.services.service import ServiceProcess


class PipelineService(ServiceProcess):
    """Represent the validation and transformation service scaffold."""

    def __init__(self, pipe: connection.Connection):
        super().__init__(pipe)
        self._records_processed: int = 0
        self._records_processed_past_ten_seconds: deque = deque([])
        self._records_per_second: float = 0.0
        self._cycle_stop: bool = False

    def _run_cycle(self) -> None:
        """Run one cycle of the pipeline service."""
        self._cycle_stop = False
        telemetry_thread = threading.Thread(
            target=self._telemetry_snap,
            daemon=True,
        )
        telemetry_thread.start()
        self._records_processed += 1
        self._records_processed_past_ten_seconds.append(time.time())

        # Keep the scaffold alive while the service is running.
        self._throughput()
        time.sleep(0.1)
        self._cycle_stop = True
        telemetry_thread.join()

    def _throughput(self) -> None:
        """Update the current pipeline service throughput."""
        while (
            self._records_processed_past_ten_seconds
            and self._records_processed_past_ten_seconds[0]
            < time.time() - 10.0
        ):
            self._records_processed_past_ten_seconds.popleft()

        self._records_per_second = (
            len(self._records_processed_past_ten_seconds) / 10.0
        )

    def _telemetry_snap(self) -> None:
        """Update a snapshot of the pipeline service telemetry."""
        while not self._shutdown and not self._cycle_stop:
            self._telemetry_snapshot = {
                "records_processed": self._records_processed,
                "records_per_second": self._records_per_second,
            }
            time.sleep(0.25)
