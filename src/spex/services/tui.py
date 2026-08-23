import random

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
        self._shutdown: bool = False

    def run(self):
        """Run the Spex TUI until it exits, releasing the Hub pipe afterward."""
        try:
            app = Spex()
            app.run()
        finally:
            self._pipe.close()


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
