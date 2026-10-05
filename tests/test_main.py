import pytest

from harp_updater_gui import main
from harp_updater_gui.models.device import Device


@pytest.fixture
def updater(mocker):
    updater = main.HarpFirmwareUpdaterApp.__new__(main.HarpFirmwareUpdaterApp)
    updater.device_manager = mocker.Mock()
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