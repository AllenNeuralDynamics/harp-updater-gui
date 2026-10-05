import pytest
from harp_updater_gui.services.firmware_service import FirmwareService


@pytest.fixture
def firmware_service():
    """Create a firmware service instance for testing"""
    return FirmwareService()


def test_get_firmware_type(firmware_service):
    """Test firmware type detection"""
    assert firmware_service.get_firmware_type("firmware.uf2") == ".uf2"
    assert firmware_service.get_firmware_type("firmware.hex") == ".hex"
    assert firmware_service.get_firmware_type("firmware.bin") is None
    assert firmware_service.get_firmware_type("FIRMWARE.UF2") == ".uf2"


def test_validate_firmware_file(firmware_service, tmp_path):
    """Test firmware file validation"""
    # Create a test file
    test_file = tmp_path / "test.uf2"
    test_file.write_text("test content")

    device_kind = "Pico"

    assert (
        firmware_service.validate_firmware_file(device_kind, str(test_file))[0] is True
    )
    assert (
        firmware_service.validate_firmware_file(
            device_kind, str(tmp_path / "nonexistent.uf2")
        )[0]
        is False
    )

    # Test wrong device kind
    assert (
        firmware_service.validate_firmware_file("UnknownDevice", str(test_file))[0]
        is False
    )
    assert (
        firmware_service.validate_firmware_file("ATxmega", str(test_file))[0] is False
    )

    # Test invalid extension
    bad_file = tmp_path / "test.bin"
    bad_file.write_text("test")
    assert (
        firmware_service.validate_firmware_file(device_kind, str(bad_file))[0] is False
    )


def test_get_available_firmware_versions(firmware_service):
    """Test fetching available firmware versions"""
    versions = firmware_service.get_available_firmware_versions("EnvironmentSensor")

    assert isinstance(versions, list)
    assert len(versions) > 0


def test_is_compatible(firmware_service):
    """Test firmware compatibility checking"""
    firmware_info = {"version": "1.0.0"}
    hardware_version = "1.0"

    # Placeholder test - in real implementation would check actual compatibility
    assert firmware_service.is_compatible(firmware_info, hardware_version) is True


def test_inspect_firmware_cache(firmware_service, mocker):
    """Test firmware inspection with caching"""
    mock_info = {"WhoAmI": 1405, "Version": "1.0.0"}
    mocker.patch.object(
        firmware_service.cli, "inspect_firmware", return_value=mock_info
    )

    firmware_path = "test_firmware.uf2"

    # First call should hit the CLI
    info1 = firmware_service.inspect_firmware(firmware_path)
    assert info1 == mock_info

    # Second call should use cache
    info2 = firmware_service.inspect_firmware(firmware_path)
    assert info2 == mock_info

    # CLI should only be called once
    firmware_service.cli.inspect_firmware.assert_called_once()


def test_validate_atxmega_without_device_connection(firmware_service, tmp_path, mocker):
    firmware = tmp_path / "Behavior-fw3.3-harp1.15-hw2.0-ass0.hex"
    firmware.write_text(":0400000001020304F2\n:00000001FF\n")
    upload = mocker.patch.object(
        firmware_service.cli, "upload_firmware", return_value=(True, "Firmware upload skipped")
    )

    assert firmware_service.validate_firmware_file("ATxmega", str(firmware)) == (True, "")
    upload.assert_called_once_with(
        firmware_path=str(firmware),
        target="validation-only",
        no_interactive=True,
        progress=False,
        no_upload=True,
    )


@pytest.mark.parametrize(
    "error",
    ["Invalid Harp firmware metadata specification string", "Invalid HEX checksum"],
)
def test_validate_atxmega_rejects_regulator_errors(
    firmware_service, tmp_path, mocker, error
):
    firmware = tmp_path / "firmware.hex"
    firmware.write_text(":00000001FF\n")
    mocker.patch.object(
        firmware_service.cli, "upload_firmware", return_value=(False, error)
    )

    valid, message = firmware_service.validate_firmware_file("ATxmega", str(firmware))

    assert not valid
    assert error in message
    assert "<device>-fw<firmware>" in message
    assert "Force upload cannot bypass" in message


def test_validate_atxmega_does_not_use_inspection_cache(firmware_service, tmp_path, mocker):
    firmware = tmp_path / "Behavior-fw3.3-harp1.15-hw2.0-ass0.hex"
    firmware.write_text(":00000001FF\n")
    firmware_service.firmware_cache[str(firmware)] = {"Metadata": firmware.stem}
    upload = mocker.patch.object(
        firmware_service.cli, "upload_firmware", return_value=(True, "")
    )

    assert firmware_service.validate_firmware_file("ATxmega", str(firmware))[0]
    firmware.write_text("invalid image")
    upload.return_value = (False, "Invalid HEX checksum")
    assert not firmware_service.validate_firmware_file("ATxmega", str(firmware))[0]
    assert upload.call_count == 2


def test_fetch_available_firmware(firmware_service):
    """Test fetching available firmware for a device"""
    device_id = "EnvironmentSensor"
    firmware_list = firmware_service.fetch_available_firmware(device_id)

    assert isinstance(firmware_list, list)


def test_check_firmware_compatibility(firmware_service):
    """Test checking firmware compatibility with device"""
    device_id = "EnvironmentSensor"
    firmware_version = "v0.9.1"

    is_compatible = firmware_service.check_firmware_compatibility(
        device_id, firmware_version
    )

    # Placeholder implementation returns True
    assert is_compatible is True
