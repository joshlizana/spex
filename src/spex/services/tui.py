import random
import threading

from multiprocessing import connection, get_context

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Label, Static

SpawnProcess = get_context("spawn").Process


class SpexProcess(SpawnProcess):
    """Provide shared process lifecycle and Hub control for the Spex TUI."""

    def __init__(self, pipe: connection.Connection):
        super().__init__()
        self._pipe: connection.Connection = pipe
        self._app: Spex | None = None
        self._shutdown = False

    def run(self) -> None:
        """Run the Spex TUI until it exits, releasing the Hub pipe afterward."""
        self._app = Spex()
        pipe_thread = threading.Thread(target=self.pipe, daemon=True)
        try:
            pipe_thread.start()
            try:
                self._app.run()
            finally:
                self._shutdown = True
                pipe_thread.join()
        finally:
            self._pipe.close()

    def pipe(self) -> None:
        """Monitor the Spex TUI control-plane pipe."""
        while not self._shutdown:
            try:
                if self._pipe.poll(timeout=0.1):
                    message = self._pipe.recv()
                    # message handling logic would go here
            except (EOFError, OSError):
                self._shutdown = True
                self._app.call_from_thread(self._app.exit)


class StatusCircle(Static):
    """Display the walking-skeleton health indicator."""

    def on_mount(self) -> None:
        self.set_interval(1, self.update_status)

    def update_status(self) -> None:
        """Select a placeholder health color."""

        # Simulate health until the control plane supplies service state.
        self.styles.color = random.choice(["green", "red", "yellow"])


class Spex(App):
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
