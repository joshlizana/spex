import asyncio

from spex.bootstrap import bootstrap_spex
from spex.services.hub import Hub


async def run_hub() -> None:
    """Run the Spex Hub in an asynchronous context."""
    async with Hub() as hub:
        await hub.run()


def main() -> None:
    """Bootstrap Spex and run the Hub in the main process."""

    bootstrap_spex()
    asyncio.run(run_hub())
