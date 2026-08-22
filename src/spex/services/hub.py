from dataclasses import dataclass
from multiprocessing import connection, context, get_context

from spex.services.backfill import BackfillService
from spex.services.lock import HubLock
from spex.services.live import LiveService
from spex.services.pipeline import PipelineService
from spex.services.service import ServiceProcess


SERVICE_TYPES = {
    "live": LiveService,
    "backfill": BackfillService,
    "pipeline": PipelineService,
}


@dataclass(slots=True)
class ManagedService:
    """Represent a managed Spex service."""

    process: ServiceProcess
    pipe: connection.Connection
    is_running: bool = True
    is_paused: bool = False


class Hub:
    """Represent the main-process Spex Hub scaffold."""

    def __init__(self):
        self._running: bool = True
        self._lock: HubLock | None = None
        self._spawn_context: context.SpawnContext = get_context("spawn")
        self._services: dict[str, ManagedService] = {}

    def __enter__(self):
        self._lock = HubLock()
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._running = False
        try:
            self._join()
        finally:
            if self._lock is not None:
                self._lock.release()

    def run(self):
        """Run the Spex Hub supervision loop."""

        while self._running:
            waitables = {}
            for role, service in self._services.items():
                waitables[service.pipe] = (role, "message")
                waitables[service.process.sentinel] = (role, "exit")

            for ready in connection.wait(waitables, timeout=0.1):
                role, event_type = waitables[ready]
                service = self._services.get(role)
                if service is None:
                    continue

                if event_type == "message":
                    try:
                        message = service.pipe.recv()
                        self._handle_message(role, message)
                    except (EOFError, OSError):
                        self._join_service(role)
                elif event_type == "exit":
                    self._join_service(role)

    def _handle_message(self, role: str, message: dict):
        """Handle a message received from a specific service."""

        match message.get("type"):
            case "state":
                payload = message.get("payload")
                self._services[role].is_running = payload.get("running")
                self._services[role].is_paused = payload.get("paused")
            case _:
                raise ValueError(
                    f"Unknown message type from service {role}: "
                    f"{message.get('type')}"
                )

    def _spawn(self, role: str):
        """Spawn a new instance of a Spex spoke service."""

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
            retry = 0
            while service.process.is_alive() and retry < 4:
                service.process.join(timeout=2**retry)
                retry += 1

            if service.process.is_alive():
                service.process.terminate()
                service.process.join(timeout=5)

            if service.process.is_alive():
                service.process.kill()
                service.process.join()

            del self._services[role]

    def _join(self):
        """Join all child processes."""
        for role in list(self._services.keys()):
            self._join_service(role)
