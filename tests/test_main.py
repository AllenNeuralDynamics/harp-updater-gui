import asyncio
from threading import Event, get_ident

import pytest

from harp_updater_gui import main
from harp_updater_gui.models.device import Device
from harp_updater_gui.services.device_operations import DeviceOperationBusy, DeviceOperations


@pytest.fixture
def updater(mocker, tmp_path):
    updater = main.HarpFirmwareUpdaterApp.__new__(main.HarpFirmwareUpdaterApp)
    updater.device_manager = mocker.Mock()
    updater.device_manager.operations = DeviceOperations(tmp_path / "devices.lock")
    updater.firmware_service = mocker.Mock()
    updater.update_workflow = mocker.Mock()
    updater.device_table = mocker.Mock()
    updater.device_table.refresh_devices = mocker.AsyncMock()
    updater.audit_logger = mocker.Mock()
    updater.firmware_service.validate_firmware_file.return_value = (True, "")
    updater.device_manager.get_devices.return_value = []
    mocker.patch.object(main, "ui")
    mocker.patch.object(main, "log_successful_firmware_update")

    async def run_callback(callback, *args, **kwargs):
        if getattr(callback, "__name__", "") != "<lambda>":
            return callback(*args, **kwargs)

    mocker.patch.object(main.run, "io_bound", side_effect=run_callback)
    mocker.patch.object(main.run, "cpu_bound", side_effect=run_callback)
    return updater


def atxmega_device(port="COM4"):
    return Device(
        Confidence="High",
        Kind="ATxmega",
        State="Online",
        PortName=port,
        DeviceDescription="Behavior",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output, offer_force",
    [
        (
            "Firmware upload failed: Device name mismatch.\n"
            "Upload aborted. Use --force to override compatibility checks or recover a device in bootloader mode.",
            True,
        ),
        ("Firmware was written, but the device did not respond within 20 seconds.", False),
        ("Firmware upload failed: Write failed", False),
        ("Failed to load firmware file: Invalid HEX checksum", False),
    ],
)
async def test_atxmega_failure_only_offers_force_when_regulator_allows(
    updater, output, offer_force
):
    updater.device_manager.upload_firmware_to_device.return_value = (False, output)

    await updater.on_firmware_deploy([atxmega_device()], "firmware.hex")

    assert updater.update_workflow.show_error_with_force.called is offer_force
    assert updater.update_workflow.show_error.called is not offer_force
    updater.update_workflow.complete_update.assert_not_called()
    main.log_successful_firmware_update.assert_not_called()


@pytest.mark.asyncio
async def test_atxmega_success_reports_regulator_readiness(updater):
    updater.device_manager.upload_firmware_to_device.return_value = (
        True,
        "Firmware written. Waiting for the device to restart...\n"
        "Successfully uploaded firmware to COM4\n",
    )

    await updater.on_firmware_deploy([atxmega_device()], "firmware.hex")

    updater.update_workflow.complete_update.assert_called_once_with(True)
    messages = [call.args[0] for call in updater.update_workflow.push_log.call_args_list]
    assert "Firmware written. Waiting for the device to restart..." in messages
    assert "Device responded after restart (confirmed by HarpRegulator)." in messages
    assert "Firmware verified" not in messages
    main.log_successful_firmware_update.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_atxmega_image_is_not_uploaded_even_with_force(updater):
    updater.firmware_service.validate_firmware_file.return_value = (
        False, "Invalid HEX checksum"
    )

    await updater.on_firmware_deploy([atxmega_device()], "firmware.hex", force=True)

    updater.device_manager.upload_firmware_to_device.assert_not_called()
    updater.update_workflow.show_error.assert_called_once()
    updater.update_workflow.show_error_with_force.assert_not_called()


@pytest.mark.asyncio
async def test_mixed_device_kinds_are_rejected_before_batch_upload(updater):
    pico = atxmega_device("COM5").model_copy(update={"kind": "Pico"})

    await updater.on_firmware_deploy([atxmega_device(), pico], "firmware.hex")

    updater.firmware_service.validate_firmware_file.assert_not_called()
    updater.device_manager.upload_firmware_to_device.assert_not_called()
    updater.update_workflow.show_error.assert_called_once()


@pytest.mark.asyncio
async def test_deployment_lease_covers_batch_and_final_refresh(updater):
    leases = []

    def upload(*args, operation, on_output=None):
        assert updater.device_manager.operations.is_busy
        leases.append(operation)
        return True, "Uploaded"

    async def refresh(*args, operation):
        assert updater.device_manager.operations.is_busy
        leases.append(operation)

    updater.device_manager.upload_firmware_to_device.side_effect = upload
    updater.device_table.refresh_devices.side_effect = refresh

    await updater.on_firmware_deploy(
        [atxmega_device(), atxmega_device("COM5")], "firmware.hex"
    )

    assert len(leases) == 3
    assert all(lease is leases[0] for lease in leases)
    assert updater.device_manager.refresh_devices.call_args.kwargs["operation"] is leases[0]
    assert not updater.device_manager.operations.is_busy


@pytest.mark.asyncio
async def test_second_client_cannot_start_deployment(updater, mocker):
    entered, finish = asyncio.Event(), asyncio.Event()

    async def validate(*args, **kwargs):
        entered.set()
        await finish.wait()
        return False, "Test validation rejection"

    mocker.patch.object(main.run, "io_bound", side_effect=validate)
    other = main.HarpFirmwareUpdaterApp.__new__(main.HarpFirmwareUpdaterApp)
    other.device_manager = mocker.Mock()
    other.device_manager.operations = DeviceOperations(updater.device_manager.operations.lock_path)
    other.firmware_service = mocker.Mock()
    task = asyncio.create_task(updater.on_firmware_deploy([atxmega_device()], "firmware.hex"))
    await entered.wait()
    try:
        await other.on_firmware_deploy([atxmega_device()], "firmware.hex")
        other.firmware_service.validate_firmware_file.assert_not_called()
        other.device_manager.upload_firmware_to_device.assert_not_called()
    finally:
        finish.set()
        await task

    assert not updater.device_manager.operations.is_busy


@pytest.mark.asyncio
async def test_cancelled_deployment_releases_idle_lease(updater, mocker):
    entered = asyncio.Event()

    async def validate(*args, **kwargs):
        entered.set()
        await asyncio.Event().wait()

    mocker.patch.object(main.run, "io_bound", side_effect=validate)
    task = asyncio.create_task(updater.on_firmware_deploy([atxmega_device()], "firmware.hex"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert not updater.device_manager.operations.is_busy


@pytest.mark.asyncio
async def test_invalid_firmware_releases_deployment_lease(updater):
    updater.firmware_service.validate_firmware_file.return_value = (False, "Invalid HEX")

    await updater.on_firmware_deploy([atxmega_device()], "firmware.hex")

    assert not updater.device_manager.operations.is_busy


@pytest.mark.asyncio
async def test_cancelled_upload_keeps_guard_until_worker_exits(updater, mocker):
    loop = asyncio.get_running_loop()
    entered, finished = asyncio.Event(), asyncio.Event()
    release = Event()
    operations = updater.device_manager.operations

    def upload(*args, operation, on_output=None):
        try:
            with operations.operation("Firmware upload", operation):
                loop.call_soon_threadsafe(entered.set)
                assert release.wait(timeout=5)
                return True, "Uploaded"
        finally:
            loop.call_soon_threadsafe(finished.set)

    async def run_callback(callback, *args, **kwargs):
        if callback is updater.device_manager.upload_firmware_to_device:
            return await asyncio.to_thread(callback, *args, **kwargs)
        if getattr(callback, "__name__", "") != "<lambda>":
            return callback(*args, **kwargs)

    updater.device_manager.upload_firmware_to_device.side_effect = upload
    mocker.patch.object(main.run, "io_bound", side_effect=run_callback)
    task = asyncio.create_task(updater.on_firmware_deploy([atxmega_device()], "firmware.hex"))
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert operations.is_busy
        with pytest.raises(DeviceOperationBusy):
            operations.begin("Competing deployment")
    finally:
        release.set()
        await asyncio.wait_for(finished.wait(), timeout=5)
        if not task.done():
            await task

    assert not operations.is_busy
    main.ui.timer.return_value.deactivate.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("success", [True, False])
async def test_atxmega_logs_progress_before_upload_finishes(updater, mocker, success):
    loop = asyncio.get_running_loop()
    entered = asyncio.Event()
    release = Event()
    ui_threads = []
    updater.update_workflow.push_log.side_effect = lambda *args: ui_threads.append(get_ident())

    def upload(*args, operation, on_output):
        with updater.device_manager.operations.operation("Firmware upload", operation):
            on_output("10% Write")
            loop.call_soon_threadsafe(entered.set)
            assert release.wait(timeout=5)
            on_output("Firmware written")
            return success, "10% Write\rFirmware written\n"

    async def run_callback(callback, *args, **kwargs):
        if callback is updater.device_manager.upload_firmware_to_device:
            return await asyncio.to_thread(callback, *args, **kwargs)
        if getattr(callback, "__name__", "") != "<lambda>":
            return callback(*args, **kwargs)

    updater.device_manager.upload_firmware_to_device.side_effect = upload
    mocker.patch.object(main.run, "io_bound", side_effect=run_callback)
    task = asyncio.create_task(updater.on_firmware_deploy([atxmega_device()], "firmware.hex"))
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        messages = [call.args[0] for call in updater.update_workflow.push_log.call_args_list]
        assert "10% Write" not in messages
        main.ui.timer.assert_called_once()
        main.ui.timer.call_args.args[1]()
        messages = [call.args[0] for call in updater.update_workflow.push_log.call_args_list]
        assert "10% Write" in messages
        assert not task.done()
    finally:
        release.set()
        await asyncio.wait_for(task, timeout=5)

    messages = [call.args[0] for call in updater.update_workflow.push_log.call_args_list]
    assert messages.count("10% Write") == 1
    assert messages.count("Firmware written") == 1
    assert all(thread == get_ident() for thread in ui_threads)
    main.ui.timer.return_value.deactivate.assert_called_once()
    if not success:
        assert "10% Write\rFirmware written" in updater.update_workflow.show_error.call_args.args[0]