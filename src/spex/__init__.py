import asyncio

from spex.tui import SpexTUI

async def _async_bridge(app: SpexTUI) -> None:
    await app.run_async()

async def orchestrator() -> None:
    """Runs an asynchronous orchestration loop. This is a placeholder for the actual orchestration logic."""
    while True:
        await asyncio.sleep(1)  # Placeholder for actual orchestration tasks
        
def main() -> None:
    app = SpexTUI()
    asyncio.run(_async_bridge(app))