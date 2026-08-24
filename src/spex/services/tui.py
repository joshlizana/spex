import random
import threading

from multiprocessing import connection, context, get_context

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Label, Static

from spex.services.hub import HubProcess

SpawnProcess = get_context("spawn").Process


class Spex:
    """Own the main-process TUI and its Hub child lifecycle."""

    def __init__(self):
        self._app: Tui = Tui()
        self._spawn_context: context.SpawnContext = get_context("spawn")
        self._shutdown = False
        self._hub_process: SpawnProcess | None = None
        self._pipe: connection.Connection | None = None
        self._pipe_thread: threading.Thread = threading.Thread(
            target=self._pipe_monitor,
            daemon=True,
        )

    def __enter__(self):
        self._start_hub()
        try:
            self._handshake()
            self._pipe_thread.start()
        except BaseException:
            if self._hub_process is not None:
                self._hub_process.terminate()
                self._hub_process.join()
            if self._pipe is not None:
                self._pipe.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._shutdown = True
        if self._pipe_thread is not None:
            self._pipe_thread.join()
        if self._pipe is not None:
            self._pipe.close()
        if self._hub_process is not None:
            self._hub_process.join()

    def run(self) -> None:
        """Run the Spex TUI until it exits, releasing the Hub pipe afterward."""

        try:
            self._app.run()
        finally:
            self._shutdown = True

    def _start_hub(self) -> None:
        """Create the TUI control pipe and spawn the Hub process."""
        parent_pipe, child_pipe = self._spawn_context.Pipe(duplex=True)

        try:
            hub_process = HubProcess(child_pipe)
            hub_process.start()
        except BaseException:
            parent_pipe.close()
            raise
        finally:
            child_pipe.close()

        self._hub_process = hub_process
        self._pipe = parent_pipe

    def _pipe_monitor(self) -> None:
        """Monitor the Spex TUI control-plane pipe."""
        while not self._shutdown:
            try:
                if self._pipe.poll(timeout=0.1):
                    message = self._pipe.recv()
                    # TUI receives no application messages in M0.
            except (EOFError, OSError):
                self._shutdown = True
                self._app.call_from_thread(self._app.exit)

    def _handshake(self) -> None:
        """Perform a handshake with the Hub process."""
        if self._pipe is None:
            raise RuntimeError("Hub pipe is not initialized.")

        try:
            message = self._pipe.recv()
            if message.get("type") == "ready":
                return
            elif message.get("type") == "error":
                error_message = message.get("payload", {}).get("message")
                raise RuntimeError(f"Hub error: {error_message}")
            else:
                raise RuntimeError(f"Unexpected Hub message: {message}")
        except (EOFError, OSError):
            raise RuntimeError("Hub process terminated unexpectedly.")


class StatusCircle(Static):
    """Display the walking-skeleton health indicator."""

    def on_mount(self) -> None:
        self.set_interval(1, self.update_status)

    def update_status(self) -> None:
        """Select a placeholder health color."""

        # Simulate health until the control plane supplies service state.
        self.styles.color = random.choice(["green", "red", "yellow"])


class Tui(App):
    """Provide the Spex Textual control plane and operational interface."""

    DEFAULT_CSS = """
    Horizontal {
        height: 1;
        width: 100%;
        content-align: left top;
        padding: 0 1;
    }
    #live_status_circle {
        content-align: left top;
        text-style: bold;
        height: 1;
        width: 1;
        color: green;
    }
    #live_service_label {
        content-align: left top;
        text-style: bold;
        height: 1;
        width: auto;
        margin-left: 1;
    }

    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the walking-skeleton application shell."""
        yield Header()
        with Horizontal():
            yield StatusCircle("●", id="live_status_circle")
            yield Label("Live Service", id="live_service_label")
        yield Footer()
