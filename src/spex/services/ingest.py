import time

from multiprocessing import connection

from spex.services.service import ServiceProcess


class IngestionService(ServiceProcess):
    """Represent the Jetstream replay and live ingestion scaffold."""

    def __init__(self, pipe: connection.Connection):
        super().__init__(pipe)

    def _run_cycle(self) -> None:
        """Run one cycle of the ingestion service."""

        # Keep the scaffold alive while the service is running.
        time.sleep(0.1)
