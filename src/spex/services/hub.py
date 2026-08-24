import asyncio
import signal
import time

from copy import deepcopy
from dataclasses import dataclass
from multiprocessing import connection, context, get_context

from spex.services.dashboard import DashboardService
from spex.services.ingest import IngestionService
from spex.services.lock import HubLock
from spex.services.pipeline import PipelineService
from spex.services.service import ServiceProcess


SERVICE_TYPES = {
    "ingest": IngestionService,
    "pipeline": PipelineService,
    "dashboard": DashboardService,
}


@dataclass(slots=True)
class ManagedService:
    """Represent a managed Spex service."""

    process: ServiceProcess | DashboardService
    pipe: connection.Connection


SpawnProcess = get_context("spawn").Process


class HubProcess(SpawnProcess):
    """Run the Hub as a TUI-owned spawned process."""

    def __init__(self, pipe: connection.Connection):
        super().__init__()
        self._pipe: connection.Connection = pipe
        self._hub: Hub | None = None

    def run(self) -> None:
        """Run the Spex Hub supervision loop."""
        asyncio.run(self._run_hub())

    async def _run_hub(self) -> None:
        """Run the Spex Hub supervision loop."""
        self._hub = Hub(pipe=self._pipe)
        ready = False

        try:
            async with self._hub as hub:
                self._pipe.send(
                    {
                        "type": "ready",
                        "payload": {
                            "services": {
                                "ingest": {
                                    "running": True,
                                    "phase": "live",
                                },
                                "pipeline": {"running": True},
                                "dashboard": {"running": True},
                            }
                        },
                    }
                )
                ready = True
                await hub.run()
        except Exception as exc:
            if not ready:
                try:
                    self._pipe.send(
                        {"type": "error", "payload": {"message": str(exc)}}
                    )
                except (BrokenPipeError, EOFError, OSError):
                    # The TUI endpoint is unavailable; preserve the startup error.
                    pass
            raise


class Hub:
    """Represent the Spex service orchestrator scaffold."""

    def __init__(self, pipe: connection.Connection):
        self._running: bool = True
        self._lock: HubLock | None = None
        self._spawn_context: context.SpawnContext = get_context("spawn")
        self._services: dict[str, ManagedService] = {}
        self._pipe: connection.Connection = pipe
        self._current_telemetry: dict = {
            "type": "telemetry",
            "payload": {
                "services": {
                    "ingest": {
                        "events_received": 0,
                        "events_per_second": 0.0,
                    },
                    "pipeline": {
                        "events_processed": 0,
                        "events_per_second": 0.0,
                    },
                }
            },
        }
        self._current_state: dict = {
            "type": "state",
            "payload": {
                "services": {
                    "ingest": {"running": True, "phase": "live"},
                    "pipeline": {"running": True},
                    "dashboard": {"running": True},
                }
            },
        }

    async def __aenter__(self):
        self._lock = HubLock()
        self._lock.acquire()
        try:
            for role in SERVICE_TYPES:
                self._spawn_service(role)
        except BaseException:
            try:
                if self._services:
                    await self._join()
            finally:
                self._lock.release()
            raise
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._running = False
        if self._pipe is not None:
            self._pipe.close()
        if self._services:
            await self._join()
        if self._lock is not None:
            self._lock.release()

    async def run(self) -> None:
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
        reporter = asyncio.create_task(asyncio.to_thread(self._reporter))
        # Supervise the running services.
        while self._running:
            try:
                if self._pipe.poll():
                    message = self._pipe.recv()
                    # The Hub receives no application messages in M0.
            except (EOFError, OSError):
                self._running = False
                continue

            for role, service in list(self._services.items()):
                try:
                    if service.pipe.poll():
                        message = service.pipe.recv()
                        await self._handle_message(role, message)
                    if not service.process.is_alive():
                        self._current_state["payload"]["services"][role]["running"] = False
                        await asyncio.to_thread(self._join_service, role)
                        await asyncio.to_thread(self._spawn_service, role)
                        self._current_state["payload"]["services"][role]["running"] = True
                        continue
                except (EOFError, OSError):
                    self._current_state["payload"]["services"][role]["running"] = False
                    await asyncio.to_thread(self._join_service, role)
                    await asyncio.to_thread(self._spawn_service, role)
                    self._current_state["payload"]["services"][role]["running"] = True
                    continue

            await asyncio.sleep(0.1)
        reporter.cancel()
        await self._join()

    def _reporter(self) -> None:
        """Send a telemetry report to the TUI."""
        reported_state = deepcopy(self._current_state)
        while self._running:
            self._pipe.send(deepcopy(self._current_telemetry))
            time.sleep(0.25)
            current_state = deepcopy(self._current_state)
            if reported_state != current_state:
                self._pipe.send(deepcopy(self._current_state))
                reported_state = current_state

    def _signal_handler(self, signum):
        """Handle signals sent to the Hub process."""
        if signum in (signal.SIGTERM, signal.SIGINT):
            # Record the request; run() tears the services down after the loop.
            self._running = False

    async def _handle_message(self, role: str, message: dict) -> None:
        """Handle a message received from a specific service."""

        match message.get("type"):
            case "telemetry":
                self._current_telemetry["payload"]["services"][role] = message.get("payload")
            case "state":
                self._current_state["payload"]["services"][role] = message.get("payload")
            case _:
                raise ValueError(f"{message.get('type')}")

    def _spawn_service(self, role: str) -> None:
        """Spawn a new instance of a Spex service."""
        service_spawned = False
        retry = 0
        exceptions = []
        while not service_spawned and retry < 5:
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
                service_spawned = True
            except BaseException:
                parent_pipe.close()
                exceptions.append(Exception(f"Failed to spawn {role} service."))
            finally:
                child_pipe.close()

            if not service_spawned and retry < 4:
                time.sleep(2**retry)
            retry += 1
        if not service_spawned:
            raise Exception(
                f"Failed to spawn {role} service after "
                f"{retry} attempts: {exceptions}"
            )
        self._services[role] = ManagedService(process=process, pipe=parent_pipe)

    def _join_service(self, role: str) -> None:
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

    async def _join(self) -> None:
        """Join all child processes."""
        roles = list(self._services)
        await asyncio.gather(
            *(asyncio.to_thread(self._join_service, role) for role in roles)
        )
