import time

from multiprocessing import connection

from spex.services.service import ServiceProcess


class PipelineService(ServiceProcess):
    """Represent the validation and transformation service scaffold."""

    def __init__(self, pipe: connection.Connection):
        super().__init__(pipe)

    def _run_cycle(self) -> None:
        """Run one cycle of the pipeline service."""

        # Keep the scaffold alive while the service is running.
        time.sleep(0.1)
