import random

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static


class StatusCircle(Static):
    """A simple widget to display the status of the orchestration tool."""

    def on_mount(self) -> None:
        self.set_interval(1, self.update_status)

    def update_status(self) -> None:
        """Placeholder for actual health check logic. In a real application, this would check the system's health."""

        # Simulate a health check (replace with actual logic)
        color = random.choice(["green", "red", "yellow"])

        self.styles.color = color

        if color == "green":
            self.update(f"● Alive")
        elif color == "red":
            self.update(f"● Offline")
        elif color == "yellow":
            self.update(f"● Degraded")


class SpexTUI(App):
    """Textual TUI for the Spex orchestration tool."""

    TITLE = "Spex"

    DEFAULT_CSS = """
    StatusCircle {
        content-align: left top;
        text-style: bold;
        height: 1fr;
        color: green;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]


    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusCircle("●")
        yield Footer()