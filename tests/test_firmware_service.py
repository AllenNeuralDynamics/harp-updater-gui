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

    assert firmware_service.validate_firmware_file(str(test_file)) is True
    assert (
        firmware_service.validate_firmware_file(str(tmp_path / "nonexistent.uf2"))
        is False
    )

    # Test invalid extension
    bad_file = tmp_path / "test.bin"
    bad_file.write_text("test")
    assert firmware_service.validate_firmware_file(str(bad_file)) is False


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
