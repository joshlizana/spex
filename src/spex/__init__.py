from spex.bootstrap import bootstrap_spex
from spex.services.tui import Spex


def start_spex() -> None:
    """Bootstrap Spex and run its Textual control plane."""

    with Spex() as app:
        app.run()


def main() -> None:
    """Bootstrap Spex and run its Textual control plane."""

    bootstrap_spex()
    start_spex()
