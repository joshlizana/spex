from spex.config import SpexConfig


def bootstrap_spex() -> None:
    """Create the accepted Spex directory layout from validated paths."""
    config = SpexConfig().config

    # Create every platformdirs root used by Spex.
    for directory in [
        config.data_dir,
        config.log_dir,
        config.config_dir,
        config.cache_dir,
        config.runtime_dir,
        config.state_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    # Create durable application-data boundaries.
    for subdirectory in [
        "raw",
        "ducklake",
        "rejected",
        "credentials",
    ]:
        (config.data_dir / subdirectory).mkdir(parents=True, exist_ok=True)

    # Create the service-state boundary.
    for subdirectory in ["services"]:
        (config.state_dir / subdirectory).mkdir(parents=True, exist_ok=True)
