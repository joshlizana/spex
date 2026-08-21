from platformdirs import PlatformDirs


class PipelineService:
    """Represent the validation and transformation service scaffold."""

    def __init__(self):
        self.running = True
        self.paused = False
        self.paths = PlatformDirs("spex", ensure_exists=True)
