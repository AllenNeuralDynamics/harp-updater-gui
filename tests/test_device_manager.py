import pytest
from harp_updater_gui.services.device_manager import DeviceManager
from harp_updater_gui.models.device import Device


@pytest.fixture
def device_manager():
    """Create a device manager instance for testing"""
    return DeviceManager()


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
