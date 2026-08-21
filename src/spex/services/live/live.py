import asyncio
from multiprocessing import Process

from platformdirs import PlatformDirs


class LiveService(Process):
    """Represent the live Jetstream ingestion service scaffold."""

    def __init__(self):
        super().__init__()
        self.running = True
        self.paused = True
        self.paths = PlatformDirs("spex", ensure_exists=True)

    def run(self):
        """Run the live service."""

        # Keep the scaffold alive while the service is running.
        while self.running:
            if self.running and not self.paused:
                # Reserve this branch for live ingestion work.
                asyncio.run(asyncio.sleep(1))

            asyncio.run(asyncio.sleep(0.1))  # Yield while paused or between iterations.


    def _pause(self):
        """Pause the live service."""
        if not self.paused:
            self.paused = True


    def _resume(self):
        """Resume the live service."""
        if self.paused:
            self.paused = False


    def _stop(self):
        """Stop the live service."""
        if self.running:
            self.running = False


    def _state(self):
        """Return the current operational state of the live service."""
        if self.running and not self.paused:
            return {"running": True, "paused": False}
        elif self.running and self.paused:
            return {"running": True, "paused": True}
        elif not self.running:
            return {"running": False, "paused": False}
