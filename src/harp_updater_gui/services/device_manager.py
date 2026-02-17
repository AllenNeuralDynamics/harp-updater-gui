from typing import List, Optional
from harp_updater_gui.services.cli_wrapper import CLIWrapper
from harp_updater_gui.models.device import Device


class DeviceManager:
    """Manager for Harp device operations"""

    def __init__(self, cli_path: str = "HarpRegulator"):
        """
        Initialize device manager

        Args:
            cli_path: Path to HarpRegulator executable
        """
        self.cli = CLIWrapper(cli_path)
        self.devices: List[Device] = []
        self.selected_device: Optional[Device] = None

    def refresh_devices(
        self, all_devices: bool = True, allow_connect: bool = True
    ) -> List[Device]:
        """
        Refresh the list of connected devices

        Args:
            all_devices: Include all devices, even low-confidence ones
            allow_connect: Allow connecting to devices for more information

        Returns:
            List of Device objects
        """
        device_data = self.cli.list_devices(
            all_devices=all_devices, allow_connect=allow_connect
        )

        self.devices = []
        for data in device_data:
            try:
                device = Device(**data)
                self.devices.append(device)
            except Exception as e:
                print(f"Error parsing device data: {e}")
                print(f"Raw data: {data}")
                continue

        return self.devices

    def get_devices(self) -> List[Device]:
        """Get the current list of devices"""
        return self.devices

    def select_device(self, device: Device):
        """Select a device for operations"""
        self.selected_device = device

    def get_selected_device(self) -> Optional[Device]:
        """Get the currently selected device"""
        return self.selected_device

    def filter_devices(
        self,
        search_query: str = "",
        device_type: Optional[str] = None,
        health_status: Optional[str] = None,
    ) -> List[Device]:
        """
        Filter devices based on criteria

        Args:
            search_query: Text to search in device name or port
            device_type: Filter by device kind (Pico, ATxmega, etc.) or status
            health_status: Filter by health status

        Returns:
            Filtered list of devices
        """
        filtered = self.devices

        # Apply search query
        if search_query:
            query_lower = search_query.lower()
            filtered = [
                d
                for d in filtered
                if query_lower in d.display_name.lower()
                or query_lower in d.port_name.lower()
                or (
                    d.device_description and query_lower in d.device_description.lower()
                )
            ]

        # Apply device type filter
        if device_type and device_type != "All types":
            # Hardware types
            if device_type in ["Pico", "ATxmega"]:
                filtered = [d for d in filtered if d.kind == device_type]
            # Health status filters
            elif device_type == "Healthy":
                filtered = [d for d in filtered if d.state == "Online"]
            elif device_type == "Error":
                filtered = [
                    d for d in filtered if d.state in ["DriverError", "Unknown"]
                ]
            elif device_type == "Needs update":
                # This would require firmware version checking
                # For now, just show devices that are online but might need updates
                filtered = [d for d in filtered if d.state == "Online"]

        # Apply health status filter (if explicitly provided)
        if health_status:
            filtered = [d for d in filtered if d.health_status == health_status]

        return filtered

    def upload_firmware_to_device(
        self, device: Device, firmware_path: str, force: bool = False
    ) -> tuple[bool, str]:
        """
        Upload firmware to a specific device

        Args:
            device: Target device
            firmware_path: Path to firmware file
            force: Force upload even if checks fail

        Returns:
            Tuple of (success, message)
        """
        target = device.port_name

        # Use PICOBOOT if device is in bootloader state and is Pico
        if device.state == "Bootloader" and device.kind == "Pico":
            target = "PICOBOOT"

        success, output = self.cli.upload_firmware(
            firmware_path=firmware_path,
            target=target,
            force=force,
            no_interactive=True,
            progress=False,
            verbose=force,
        )

        return success, output
