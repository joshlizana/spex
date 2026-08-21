import asyncio

from spex.app import Spex
from spex.bootstrap import bootstrap_spex


def main() -> None:
    """Bootstrap Spex and run its Textual control plane."""

    bootstrap_spex()
    app = Spex()
    asyncio.run(app.run_async())
