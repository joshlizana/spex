import fcntl
import os
from pathlib import Path

import orjson
import psutil

from spex.config import SpexConfig


class Lock:
    """Own a role-specific process lock and its identity metadata."""

    def __init__(self, service: str, session_id: str, instance_id: str):
        self._lock_file: Path = (
            SpexConfig().config.runtime_dir / "locks" / f"{service}.lock"
        )
        self._lock_fd: int | None = None
        self._pid: int = os.getpid()
        self._create_time: int = int(
            psutil.Process(self._pid).create_time() * 1_000_000
        )
        self._role: str = service
        self._session_id: str = session_id
        self._instance_id: str = instance_id

    @property
    def lock_fd(self) -> int | None:
        """Return the file descriptor for the lock file."""
        return self._lock_fd

    def acquire(self) -> None:
        """Acquire the lock for the service."""

        if self._lock_fd is not None:
            raise RuntimeError("Lock is already acquired.")
        try:
            self._lock_fd = os.open(
                self._lock_file,
                os.O_CREAT | os.O_NONBLOCK | os.O_RDWR,
                0o600,
            )
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._close_lock()
            raise RuntimeError(
                f"Another {self._role} process is already running. Cannot acquire lock."
            )
        except OSError as e:
            self._close_lock()
            raise RuntimeError(f"Failed to acquire lock for {self._role}: {e}")

        self.write_metadata()

    def release(self) -> None:
        """Release the lock for the service."""

        if self._lock_fd is None:
            raise RuntimeError("Lock is not acquired or already released.")
        try:
            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
        finally:
            self._close_lock()

    def write_metadata(self) -> None:
        """Write metadata to the lock file."""

        try:
            if self._lock_fd is not None:
                metadata = orjson.dumps(
                    {
                        "PID": self._pid,
                        "Create Time": self._create_time,
                        "Role": self._role,
                        "Session ID": self._session_id,
                        "Instance ID": self._instance_id,
                    }
                )
                remaining_bytes = memoryview(metadata)
                os.lseek(self._lock_fd, 0, os.SEEK_SET)
                while remaining_bytes:
                    written = os.write(self._lock_fd, remaining_bytes)
                    if written == 0:
                        raise OSError("Failed to write metadata to lock file.")
                    remaining_bytes = remaining_bytes[written:]
                os.ftruncate(self._lock_fd, len(metadata))
                os.fsync(self._lock_fd)
            else:
                raise RuntimeError("Lock is not acquired. Cannot write metadata.")
        except Exception as e:
            self._close_lock()
            raise RuntimeError(f"Failed to write metadata: {e}")

    def _close_lock(self) -> None:
        """Close the lock descriptor and clear its ownership state."""

        fd = self._lock_fd
        self._lock_fd = None
        if fd is not None:
            os.close(fd)
