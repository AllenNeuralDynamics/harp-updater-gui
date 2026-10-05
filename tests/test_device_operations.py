import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from harp_updater_gui.services.device_operations import DeviceOperationBusy, DeviceOperations
from harp_updater_gui.services import device_operations as operations_module


def test_shared_coordinators_reject_overlapping_operations(tmp_path):
    first = DeviceOperations(tmp_path / "devices.lock")
    second = DeviceOperations(first.lock_path)
    lease = first.begin("Firmware deployment")
    try:
        assert first.is_busy
        assert second.is_busy
        with pytest.raises(DeviceOperationBusy):
            first.begin("Device discovery")
        with pytest.raises(DeviceOperationBusy):
            second.begin("Driver installation")
    finally:
        first.end(lease)
    assert not second.is_busy


def test_worker_keeps_lease_after_ui_owner_exits(tmp_path):
    operations = DeviceOperations(tmp_path / "devices.lock")
    lease = operations.begin("Firmware deployment")
    entered = Event()
    release = Event()

    def worker():
        with operations.operation("Firmware upload", lease):
            entered.set()
            assert release.wait(timeout=5)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker)
        try:
            assert entered.wait(timeout=5)
            operations.end(lease)
            assert operations.is_busy
            with pytest.raises(DeviceOperationBusy), operations.operation("Queued upload", lease):
                pass
            with pytest.raises(DeviceOperationBusy):
                operations.begin("Device discovery")
        finally:
            release.set()
            future.result(timeout=5)
    assert not operations.is_busy
    with DeviceOperations(operations.lock_path).operation("Device discovery"):
        pass


def test_operation_releases_after_failure(tmp_path):
    operations = DeviceOperations(tmp_path / "devices.lock")
    with pytest.raises(ValueError), operations.operation("Firmware deployment"):
        raise ValueError("upload failed")
    assert not operations.is_busy


def test_other_process_cannot_use_locked_devices(tmp_path):
    operations = DeviceOperations(tmp_path / "devices.lock")
    code = (
        "from pathlib import Path; import sys; "
        "from harp_updater_gui.services.device_operations import DeviceOperations; "
        "assert DeviceOperations(Path(sys.argv[1])).is_busy"
    )
    with operations.operation("Firmware deployment"):
        subprocess.run([sys.executable, "-c", code, str(operations.lock_path)], check=True)


def test_single_instance_lock_rejects_overlap_and_releases(tmp_path, mocker):
    mocker.patch.object(operations_module, "gettempdir", return_value=str(tmp_path))
    with operations_module.single_app_instance():
        with pytest.raises(RuntimeError, match="already running"):
            with operations_module.single_app_instance():
                pass
    with operations_module.single_app_instance():
        pass