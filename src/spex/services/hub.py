import asyncio
import signal

from dataclasses import dataclass
from multiprocessing import connection, context, get_context

from spex.services.backfill import BackfillService
from spex.services.dashboard import DashboardService
from spex.services.live import LiveService
from spex.services.lock import HubLock
from spex.services.pipeline import PipelineService
from spex.services.service import ServiceProcess
from spex.services.tui import SpexProcess


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


class Hub:
    """Represent the main-process Spex Hub scaffold."""

    def __init__(self):
        self._running: bool = True
        self._lock: HubLock | None = None
        self._spawn_context: context.SpawnContext = get_context("spawn")
        self._services: dict[str, ManagedService] = {}

    async def __aenter__(self):
        self._lock = HubLock()
        self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self._services:
            await self._join()
        if self._lock is not None:
            self._lock.release()

    async def run(self):
        """Run the Spex Hub supervision loop."""
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            signal.SIGTERM,
            self._signal_handler,
            signal.SIGTERM,
        )
        loop.add_signal_handler(
            signal.SIGINT,
            self._signal_handler,
            signal.SIGINT,
        )

        # Start the TUI first; it is the primary operator interface, and its exit
        # is the Hub's shutdown trigger.
        self._spawn_service("tui")

        # Supervise the running services, handling messages received from the TUI.
        while self._running:
            for role, service in list(self._services.items()):
                if role == "tui":
                    try:
                        if service.pipe.poll() and service.process.is_alive():
                            message = service.pipe.recv()
                            await self._handle_message(message)
                        if not service.process.is_alive():
                            self._running = False
                            continue
                    except (EOFError, OSError):
                        self._running = False
                        continue
                else:
                    if not service.process.is_alive():
                        await asyncio.to_thread(self._join_service, role)
                        continue

            await asyncio.sleep(0.1)

        await self._join()

    def _signal_handler(self, signum):
        """Handle signals sent to the Hub process."""
        if signum in (signal.SIGTERM, signal.SIGINT):
            # Record the request; run() tears the services down after the loop.
            self._running = False

    async def _handle_message(self, message: dict):
        """Handle a message received from a specific service."""

        match message.get("type"):
            case "start":
                service = message.get("role")
                self._spawn_service(service)
            case "stop":
                service = message.get("role")
                await asyncio.to_thread(self._join_service, service)
            case _:
                raise ValueError(f"{message.get('type')}")

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

    async def _join(self):
        """Join all child processes."""
        roles = list(self._services)
        await asyncio.gather(
            *(asyncio.to_thread(self._join_service, role) for role in roles)
        )
