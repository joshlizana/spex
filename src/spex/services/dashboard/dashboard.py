from platformdirs import PlatformDirs


class DashboardService:
    """Represent the Streamlit dashboard service scaffold."""

    def __init__(self):
        self.running = True
        self.paused = False
        self.paths = PlatformDirs("spex", ensure_exists=True)
