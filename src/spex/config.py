import json
import os
import threading
from pathlib import Path

import platformdirs
from pydantic import BaseModel, Field, ValidationError, computed_field


class ConfigSchema(BaseModel):
    """Validate persisted settings and expose platform-specific paths."""

    model_config = {"validate_assignment": True}
    retention: int = Field(default=24, ge=1, description="Retention period in hours for data storage.")

    @computed_field
    @property
    def data_dir(self) -> Path:
        """Compute the data directory path based on the platform."""
        dirs = platformdirs.PlatformDirs("spex", ensure_exists=True)
        return dirs.user_data_path

    @computed_field
    @property
    def log_dir(self) -> Path:
        """Compute the log directory path based on the platform."""
        dirs = platformdirs.PlatformDirs("spex", ensure_exists=True)
        return dirs.user_log_path

    @computed_field
    @property
    def config_dir(self) -> Path:
        """Compute the configuration directory path based on the platform."""
        dirs = platformdirs.PlatformDirs("spex", ensure_exists=True)
        return dirs.user_config_path

    @computed_field
    @property
    def cache_dir(self) -> Path:
        """Compute the cache directory path based on the platform."""
        dirs = platformdirs.PlatformDirs("spex", ensure_exists=True)
        return dirs.user_cache_path

    @computed_field
    @property
    def runtime_dir(self) -> Path:
        """Compute the runtime directory path based on the platform."""
        dirs = platformdirs.PlatformDirs("spex", ensure_exists=True)
        return dirs.user_runtime_path

    @computed_field
    @property
    def state_dir(self) -> Path:
        """Compute the state directory path based on the platform."""
        dirs = platformdirs.PlatformDirs("spex", ensure_exists=True)
        return dirs.user_state_path

class SpexConfig:
    """Load, validate, and atomically persist Spex configuration."""

    def __init__(self):
        self._lock = threading.Lock()
        self._config_file: Path = Path(platformdirs.PlatformDirs("spex", ensure_exists=True).user_config_path) / "config.json"
        self._config: ConfigSchema = self._load_config()


    @property
    def config(self) -> ConfigSchema:
        """Return an isolated snapshot of the current configuration."""
        with self._lock:
            return self._config.model_copy(deep=True)

    def _load_config(self) -> ConfigSchema:
        """Load validated JSON or create the default configuration."""
        if self._config_file.exists():
            try:
                loaded_config = self._config_file.read_text(encoding="utf-8")
                config = ConfigSchema.model_validate_json(loaded_config)
            except (ValidationError, json.JSONDecodeError):
                os.remove(self._config_file)
                config = ConfigSchema()
        else:
            config = ConfigSchema()
            fd = os.open(self._config_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(config.model_dump_json(exclude_computed_fields=True, indent=4))
                f.flush()
                os.fsync(f.fileno())

        return config


    def _save_config(self, config_copy: ConfigSchema) -> None:
        """Atomically replace the persisted configuration with a candidate."""
        if not self._config_file.parent.exists():
            self._config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            tmp_file = self._config_file.parent / "config.json.tmp"
            fd = os.open(tmp_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(config_copy.model_dump_json(exclude_computed_fields=True, indent=4))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, self._config_file)
        finally:
            try:
                tmp_file.unlink(missing_ok=True)
            except OSError:
                pass


    def update(self, **kwargs) -> None:
        """Validate, persist, and publish a complete configuration update."""
        with self._lock:
            config_data = self._config.model_dump(exclude_computed_fields=True)
            config_data.update(kwargs)
            config_copy = ConfigSchema.model_validate(config_data, extra="forbid")
            self._save_config(config_copy)
            self._config = config_copy.model_copy()
