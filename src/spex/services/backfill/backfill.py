import asyncio
from multiprocessing import Process

from platformdirs import PlatformDirs


class BackfillService(Process):
    """Represent the historical backfill service scaffold."""

    def __init__(self):
        super().__init__()
        self.running = True
        self.paused = True
        self.paths = PlatformDirs("spex", ensure_exists=True)

    def run(self):
        """Run the backfill service."""

        while self.running:
            if self.running and not self.paused:
                # Reserve this branch for backfill work.
                asyncio.run(asyncio.sleep(1))

            asyncio.run(asyncio.sleep(0.1))


    def _pause(self):
        """Pause the backfill service."""
        if not self.paused:
            self.paused = True


    def _resume(self):
        """Resume the backfill service."""
        if self.paused:
            self.paused = False


    def _stop(self):
        """Stop the backfill service."""
        if self.running:
            self.running = False


    def _state(self):
        """Return the current operational state of the backfill service."""
        if self.running and not self.paused:
            return {"running": True, "paused": False}
        elif self.running and self.paused:
            return {"running": True, "paused": True}
        elif not self.running:
            return {"running": False, "paused": False}
