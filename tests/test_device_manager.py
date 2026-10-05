import pytest
from harp_updater_gui.services.device_manager import DeviceManager
from harp_updater_gui.services.device_operations import DeviceOperationBusy, DeviceOperations
from harp_updater_gui.models.device import Device


@pytest.fixture
def device_manager(tmp_path):
    """Create a device manager instance for testing"""
    return DeviceManager(operations=DeviceOperations(tmp_path / "devices.lock"))


@pytest.fixture
def sample_device_data():
    """Sample device data matching HarpRegulator JSON output"""
    return {
        "Confidence": "Low",
        "Kind": "Pico",
        "State": "Online",
        "PortName": "COM5",
        "WhoAmI": 1405,
        "DeviceDescription": "EnvironmentSensor",
        "SerialNumber": None,
        "FirmwareVersion": "0.2.0",
        "HardwareVersion": "1.0",
        "Source": "Pico USB Serial Port",
    }


def test_device_model_creation(sample_device_data):
    """Test creating a Device from HarpRegulator data"""
    device = Device(**sample_device_data)

    assert device.port_name == "COM5"
    assert device.who_am_i == 1405
    assert device.device_description == "EnvironmentSensor"
    assert device.firmware_version == "0.2.0"
    assert device.kind == "Pico"
    assert device.state == "Online"


def test_device_display_name(sample_device_data):
    """Test device display name property"""
    device = Device(**sample_device_data)
    assert device.display_name == "EnvironmentSensor"

    # Test without device description
    data = sample_device_data.copy()
    data["DeviceDescription"] = None
    device = Device(**data)
    assert device.display_name == "Device 1405"


def test_device_health_status(sample_device_data):
    """Test device health status mapping"""
    device = Device(**sample_device_data)
    assert device.health_status == "Healthy"
    assert device.health_color == "green"

    # Test bootloader state
    data = sample_device_data.copy()
    data["State"] = "Bootloader"
    device = Device(**data)
    assert device.health_status == "Bootloader"
    assert device.health_color == "yellow"

    # Test error state
    data = sample_device_data.copy()
    data["State"] = "DriverError"
    device = Device(**data)
    assert device.health_status == "Error"
    assert device.health_color == "red"


def test_filter_devices(device_manager, mocker, sample_device_data):
    """Test device filtering functionality"""
    # Mock the CLI to return sample devices
    mock_list = [
        sample_device_data,
        {
            **sample_device_data,
            "PortName": "COM6",
            "DeviceDescription": "TreadmillDriver",
            "Kind": "ATxmega",
        },
    ]
    mocker.patch.object(device_manager.cli, "list_devices", return_value=mock_list)

    # Refresh devices
    device_manager.refresh_devices()

    # Test search filter
    filtered = device_manager.filter_devices(search_query="Environment")
    assert len(filtered) == 1
    assert filtered[0].device_description == "EnvironmentSensor"

    # Test device type filter
    filtered = device_manager.filter_devices(device_type="Pico")
    assert len(filtered) == 1
    assert filtered[0].kind == "Pico"

    filtered = device_manager.filter_devices(device_type="ATxmega")
    assert len(filtered) == 1
    assert filtered[0].kind == "ATxmega"


def test_select_device(device_manager, mocker, sample_device_data):
    """Test device selection"""
    mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[sample_device_data]
    )

    device_manager.refresh_devices()
    devices = device_manager.get_devices()

    assert len(devices) == 1

    device_manager.select_device(devices[0])
    selected = device_manager.get_selected_device()

    assert selected is not None
    assert selected.port_name == "COM5"
    assert selected.display_name == "EnvironmentSensor"


def test_install_drivers_delegates_to_cli(device_manager, mocker):
    """Test that driver installation delegates to CLI wrapper."""
    mock_install = mocker.patch.object(
        device_manager.cli,
        "install_drivers",
        return_value=(True, "Drivers installed"),
    )

    success, output = device_manager.install_drivers()

    assert success is True
    assert output == "Drivers installed"
    mock_install.assert_called_once_with()


def test_refresh_selection_follows_serial_not_port(device_manager, mocker, sample_device_data):
    selected = Device(**{**sample_device_data, "SerialNumber": "ABC123"})
    device_manager.select_device(selected)
    mocker.patch.object(
        device_manager.cli,
        "list_devices",
        return_value=[{**sample_device_data, "SerialNumber": "ABC123", "PortName": "COM9"}],
    )

    device_manager.refresh_devices(allow_connect=False)

    assert device_manager.get_selected_device().port_name == "COM9"
    assert device_manager.get_selected_device() is not selected


def test_refresh_clears_selection_when_port_is_reused(device_manager, mocker, sample_device_data):
    device_manager.select_device(Device(**{**sample_device_data, "SerialNumber": "ABC123"}))
    mocker.patch.object(
        device_manager.cli,
        "list_devices",
        return_value=[{**sample_device_data, "SerialNumber": "OTHER"}],
    )

    device_manager.refresh_devices(allow_connect=False)

    assert device_manager.get_selected_device() is None


def test_ambiguous_identity_is_not_resolved(device_manager):
    device = Device(Confidence="Low", Kind="Pico", State="Bootloader")
    device_manager.devices = [device, device.model_copy()]

    assert device_manager.get_device_by_identity(device.identity) is None


def test_usb_identity_survives_port_change(sample_device_data):
    source = "Pico USB Serial Port - USB\\VID_2E8A\\UNIQUE_DEVICE"
    first = Device(**{**sample_device_data, "Source": source})
    second = Device(**{**sample_device_data, "Source": source, "PortName": "COM9"})

    assert first.identity == second.identity


@pytest.mark.parametrize("force", [False, True])
def test_atxmega_upload_uses_serial_port_and_progress(device_manager, mocker, force):
    device = Device(
        Confidence="High", Kind="ATxmega", State="Bootloader", PortName="COM4"
    )
    mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[device.model_dump(by_alias=True)]
    )
    upload = mocker.patch.object(
        device_manager.cli, "upload_firmware", return_value=(True, "Successfully uploaded")
    )

    assert device_manager.upload_firmware_to_device(device, "firmware.hex", force)[0]
    upload.assert_called_once_with(
        firmware_path="firmware.hex",
        target="COM4",
        force=force,
        no_interactive=True,
        progress=True,
        verbose=force,
        on_output=None,
    )


def test_upload_forwards_live_output_callback(device_manager, mocker):
    device = Device(Confidence="High", Kind="ATxmega", State="Online", PortName="COM4")
    callback = mocker.Mock()
    mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[device.model_dump(by_alias=True)]
    )
    upload = mocker.patch.object(
        device_manager.cli, "upload_firmware", return_value=(True, "Uploaded")
    )

    assert device_manager.upload_firmware_to_device(
        device, "firmware.hex", on_output=callback
    )[0]
    assert upload.call_args.kwargs["on_output"] is callback


def test_atxmega_upload_requires_serial_port(device_manager, mocker):
    device = Device(Confidence="Low", Kind="ATxmega", State="Bootloader")
    upload = mocker.patch.object(device_manager.cli, "upload_firmware")

    success, output = device_manager.upload_firmware_to_device(device, "firmware.hex")

    assert not success
    assert "serial port" in output
    upload.assert_not_called()


def test_pico_bootloader_upload_is_unchanged(device_manager, mocker):
    device = Device(Confidence="High", Kind="Pico", State="Bootloader")
    mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[device.model_dump(by_alias=True)]
    )
    upload = mocker.patch.object(
        device_manager.cli, "upload_firmware", return_value=(True, "Finished uploading")
    )

    assert device_manager.upload_firmware_to_device(device, "firmware.uf2")[0]
    assert upload.call_args.kwargs["target"] == "PICOBOOT"
    assert upload.call_args.kwargs["progress"] is False


def test_upload_uses_fresh_port_for_same_serial(device_manager, mocker):
    selected = Device(
        Confidence="High", Kind="ATxmega", State="Online",
        PortName="COM4", SerialNumber="ABC123",
    )
    current = selected.model_copy(update={"port_name": "COM9"})
    discovery = mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[current.model_dump(by_alias=True)]
    )
    upload = mocker.patch.object(
        device_manager.cli, "upload_firmware", return_value=(True, "Uploaded")
    )

    assert device_manager.upload_firmware_to_device(selected, "firmware.hex")[0]
    discovery.assert_called_once_with(all_devices=True, allow_connect=False)
    assert upload.call_args.kwargs["target"] == "COM9"


def test_upload_rejects_reused_port_with_new_identity(device_manager, mocker):
    selected = Device(
        Confidence="High", Kind="ATxmega", State="Online",
        PortName="COM4", SerialNumber="ABC123",
    )
    replacement = selected.model_copy(update={"serial_number": "OTHER"})
    mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[replacement.model_dump(by_alias=True)]
    )
    upload = mocker.patch.object(device_manager.cli, "upload_firmware")

    assert not device_manager.upload_firmware_to_device(selected, "firmware.hex", force=True)[0]
    upload.assert_not_called()


def test_nonconnecting_ftdi_scan_preserves_atxmega_target(device_manager, mocker):
    selected = Device(
        Confidence="High", Kind="ATxmega", State="Online", PortName="COM4",
        SerialNumber="ABC123",
        Source="FTDI USB Device - USB\\VID_0403\\UNIQUE_DEVICE",
    )
    current = selected.model_copy(update={
        "kind": "FTDI", "confidence": "Low", "serial_number": None,
    })
    mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[current.model_dump(by_alias=True)]
    )
    upload = mocker.patch.object(
        device_manager.cli, "upload_firmware", return_value=(True, "Uploaded")
    )

    assert device_manager.upload_firmware_to_device(selected, "firmware.hex")[0]
    assert upload.call_args.kwargs["target"] == "COM4"
    assert upload.call_args.kwargs["progress"] is True


def test_multiple_pico_bootloaders_never_use_generic_target(device_manager, mocker):
    selected = Device(
        Confidence="High", Kind="Pico", State="Bootloader", SerialNumber="FIRST"
    )
    other = selected.model_copy(update={"serial_number": "SECOND"})
    mocker.patch.object(
        device_manager.cli, "list_devices",
        return_value=[selected.model_dump(by_alias=True), other.model_dump(by_alias=True)],
    )
    upload = mocker.patch.object(device_manager.cli, "upload_firmware")

    success, message = device_manager.upload_firmware_to_device(selected, "firmware.uf2")

    assert not success
    assert "exactly one" in message
    upload.assert_not_called()


def test_conflicting_serial_invalidates_same_usb_identity(device_manager, mocker):
    selected = Device(
        Confidence="High", Kind="ATxmega", State="Online", PortName="COM4",
        SerialNumber="FIRST", Source="FTDI USB Device - USB\\VID_0403\\INSTANCE",
    )
    replacement = selected.model_copy(update={"serial_number": "SECOND"})
    device_manager.select_device(selected)
    mocker.patch.object(
        device_manager.cli, "list_devices", return_value=[replacement.model_dump(by_alias=True)]
    )
    upload = mocker.patch.object(device_manager.cli, "upload_firmware")

    assert not device_manager.upload_firmware_to_device(selected, "firmware.hex")[0]
    assert device_manager.selected_device is None
    upload.assert_not_called()


def test_active_deployment_blocks_refresh_install_and_upload(device_manager, mocker):
    discovery = mocker.patch.object(device_manager.cli, "list_devices")
    install = mocker.patch.object(device_manager.cli, "install_drivers")
    upload = mocker.patch.object(device_manager.cli, "upload_firmware")
    device = Device(Confidence="High", Kind="Pico", State="Bootloader")
    lease = device_manager.operations.begin("Firmware deployment")
    try:
        with pytest.raises(DeviceOperationBusy):
            device_manager.refresh_devices()
        assert not device_manager.install_drivers()[0]
        assert not device_manager.upload_firmware_to_device(device, "firmware.uf2")[0]
        discovery.assert_not_called()
        install.assert_not_called()
        upload.assert_not_called()
    finally:
        device_manager.operations.end(lease)


def test_missing_pico_bootloader_never_uploads(device_manager, mocker):
    device = Device(Confidence="High", Kind="Pico", State="Bootloader")
    mocker.patch.object(device_manager.cli, "list_devices", return_value=[])
    upload = mocker.patch.object(device_manager.cli, "upload_firmware")

    assert not device_manager.upload_firmware_to_device(device, "firmware.uf2")[0]
    upload.assert_not_called()


def test_new_bootloader_blocks_upload_to_other_device(device_manager, mocker):
    selected = Device(Confidence="High", Kind="ATxmega", State="Online", PortName="COM4")
    bootloader = Device(Confidence="High", Kind="Pico", State="Bootloader")
    mocker.patch.object(
        device_manager.cli, "list_devices",
        return_value=[selected.model_dump(by_alias=True), bootloader.model_dump(by_alias=True)],
    )
    upload = mocker.patch.object(device_manager.cli, "upload_firmware")

    assert not device_manager.upload_firmware_to_device(selected, "firmware.hex")[0]
    upload.assert_not_called()
