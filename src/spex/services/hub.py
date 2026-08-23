import signal

from dataclasses import dataclass
from multiprocessing import connection, context, get_context

from spex.services.backfill import BackfillService
from spex.services.lock import HubLock
from spex.services.live import LiveService
from spex.services.pipeline import PipelineService
from spex.services.service import ServiceProcess
from spex.services.tui import SpexProcess
from spex.services.dashboard import DashboardService


SERVICE_TYPES = {
    "live": LiveService,
    "backfill": BackfillService,
    "pipeline": PipelineService,
    "tui": SpexProcess,
    "dashboard": DashboardService,
}


@dataclass(slots=True)
class ManagedService:
    """Represent a managed Spex service."""

    process: ServiceProcess | SpexProcess | DashboardService
    pipe: connection.Connection
    is_running: bool = True
    is_paused: bool = False


class Hub:
    """Represent the main-process Spex Hub scaffold."""

    def __init__(self):
        self._lock: HubLock | None = None
        self._spawn_context: context.SpawnContext = get_context("spawn")
        self._services: dict[str, ManagedService] = {}

    def __enter__(self):
        self._lock = HubLock()
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self._join()
        finally:
            if self._lock is not None:
                self._lock.release()

    def run(self):
        """Run the Spex Hub supervision loop."""

        self._spawn_service("tui")
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        while True:
            try:
                # Wait for messages from tui
                pass
            except KeyboardInterrupt:
                break
            except Exception as e:
                raise

        self._join()


    def _signal_handler(self, signum, frame):
        """Handle signals sent to the Hub process."""
        if signum in (signal.SIGTERM, signal.SIGINT):
            self._join()

    def _handle_message(self, message: dict):
        """Handle a message received from a specific service."""

        match message.get("type"):
            case "start":
                service = message.get("role")
                self._spawn_service(service)
            case "stop":
                service = message.get("role")
                self._join_service(service)
            case _:
                raise ValueError(
                    f"{message.get('type')}"
                )

    def _spawn_service(self, role: str):
        """Spawn a new instance of a Spex service."""

        service_type = SERVICE_TYPES.get(role)
        if service_type is None:
            raise ValueError(f"Unknown service type: {role}")

        existing = self._services.get(role)
        if existing is not None and existing.process.is_alive():
            return
        elif existing is not None:
            self._join_service(role)

        parent_pipe, child_pipe = self._spawn_context.Pipe(duplex=True)
        process = service_type(pipe=child_pipe)

        try:
            process.start()
        except BaseException:
            parent_pipe.close()
            raise
        finally:
            child_pipe.close()

        self._services[role] = ManagedService(process=process, pipe=parent_pipe)

    def _join_service(self, role: str):
        """Join a specific service process."""

        service = self._services.get(role)

        if service is not None:
            service.pipe.close()

            if service.process.is_alive():
                service.process.terminate()
                service.process.join(timeout=15)

            if service.process.is_alive():
                service.process.kill()
                service.process.join()

            del self._services[role]

    def _join(self):
        """Join all child processes."""
        for role in list(self._services.keys()):
            self._join_service(role)
