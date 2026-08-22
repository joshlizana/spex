import time


class DashboardService:
    """Represent the Streamlit dashboard service scaffold."""

    def run(self):
        """Run the dashboard service."""
        # Keep the scaffold alive while the service is running.
        while True:
            time.sleep(0.1)
