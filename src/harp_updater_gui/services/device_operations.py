from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from threading import Lock
from typing import Iterator

from filelock import FileLock, Timeout


class DeviceOperationBusy(RuntimeError):
    """Another client or application process is using the devices."""


@dataclass(eq=False)
class DeviceOperationLease:
    name: str
    lock: FileLock
    owner_active: bool = True
    workers: int = 0


class DeviceOperations:
    """Coordinate device operations across clients, threads, and app processes."""

    def __init__(self, lock_path: Path | None = None):
        self.lock_path = lock_path or Path(gettempdir()) / "harp-updater-gui-devices.lock"
        self._mutex = Lock()
        self._active: DeviceOperationLease | None = None

    @property
    def is_busy(self) -> bool:
        with self._mutex:
            if self._active:
                return True
            lock = FileLock(self.lock_path, timeout=0, thread_local=False)
            try:
                lock.acquire()
            except Timeout:
                return True
            lock.release()
            return False

    def begin(self, name: str) -> DeviceOperationLease:
        with self._mutex:
            if self._active:
                raise DeviceOperationBusy(f"{self._active.name} is already in progress.")
            lock = FileLock(self.lock_path, timeout=0, thread_local=False)
            try:
                lock.acquire()
            except Timeout as error:
                raise DeviceOperationBusy(
                    "Another Harp Updater GUI instance is using the devices."
                ) from error
            lease = DeviceOperationLease(name, lock)
            self._active = lease
            return lease

    def end(self, lease: DeviceOperationLease) -> None:
        with self._mutex:
            if self._active is lease:
                lease.owner_active = False
                self._release_if_finished(lease)

    def _release_if_finished(self, lease: DeviceOperationLease) -> None:
        if not lease.owner_active and lease.workers == 0:
            lease.lock.release()
            self._active = None

    @contextmanager
    def operation(
        self, name: str, lease: DeviceOperationLease | None = None
    ) -> Iterator[DeviceOperationLease]:
        owns_lease = lease is None
        current = self.begin(name) if owns_lease else lease
        with self._mutex:
            if current is not self._active or not current.owner_active:
                raise DeviceOperationBusy("The device operation is no longer active.")
            current.workers += 1
        try:
            yield current
        finally:
            with self._mutex:
                current.workers -= 1
                if owns_lease:
                    current.owner_active = False
                self._release_if_finished(current)


DEVICE_OPERATIONS = DeviceOperations()


@contextmanager
def single_app_instance() -> Iterator[None]:
    lock = FileLock(Path(gettempdir()) / "harp-updater-gui-instance.lock", timeout=0)
    try:
        lock.acquire()
    except Timeout as error:
        raise RuntimeError("Harp Updater GUI is already running.") from error
    try:
        yield
    finally:
        lock.release()