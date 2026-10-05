from typing import List, Optional
from harp_updater_gui.services.cli_wrapper import CLIWrapper
from harp_updater_gui.services.device_operations import (
    DEVICE_OPERATIONS,
    DeviceOperationBusy,
    DeviceOperationLease,
    DeviceOperations,
)
from harp_updater_gui.models.device import Device


class DeviceManager:
    """Manager for Harp device operations"""

    def __init__(
        self, cli_path: str = "HarpRegulator", operations: DeviceOperations | None = None
    ):
        """
        Initialize device manager

        Args:
            cli_path: Path to HarpRegulator executable
        """
        self.cli = CLIWrapper(cli_path)
        self.operations = operations or DEVICE_OPERATIONS
        self.devices: List[Device] = []
        self.selected_device: Optional[Device] = None

    def refresh_devices(
        self,
        all_devices: bool = True,
        allow_connect: bool = True,
        *,
        operation: DeviceOperationLease | None = None,
    ) -> List[Device]:
        """
        Refresh the list of connected devices

        Args:
            all_devices: Include all devices, even low-confidence ones
            allow_connect: Allow connecting to devices for more information

        Returns:
            List of Device objects
        """
        with self.operations.operation("Device discovery", operation):
            return self._refresh_devices(all_devices, allow_connect)

    def _refresh_devices(self, all_devices: bool, allow_connect: bool) -> List[Device]:
        device_data = self.cli.list_devices(
            all_devices=all_devices, allow_connect=allow_connect
        )

        devices = []
        for data in device_data:
            try:
                device = Device(**data)
                devices.append(device)
            except Exception as e:
                print(f"Error parsing device data: {e}")
                print(f"Raw data: {data}")
                continue

        self.devices = devices
        if self.selected_device:
            self.selected_device = self.get_device_by_identity(
                self.selected_device.identity, expected=self.selected_device
            )
        return self.devices

    def get_devices(self) -> List[Device]:
        """Get the current list of devices"""
        return self.devices

    def get_device_by_identity(
        self, identity: str, *, expected: Optional[Device] = None
    ) -> Optional[Device]:
        """Resolve an identity only when it has exactly one current match."""
        matches = [device for device in self.devices if device.identity == identity]
        if len(matches) != 1:
            return None
        current = matches[0]
        if (
            expected and expected.serial_number and current.serial_number
            and expected.serial_number.casefold() != current.serial_number.casefold()
        ):
            return None
        return current

    def select_device(self, device: Optional[Device]):
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
        self,
        device: Device,
        firmware_path: str,
        force: bool = False,
        *,
        operation: DeviceOperationLease | None = None,
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
        if device.kind == "ATxmega" and not device.port_name:
            return False, "ATxmega firmware uploads require a serial port."

        try:
            with self.operations.operation("Firmware upload", operation):
                devices = self._refresh_devices(all_devices=True, allow_connect=False)
                current = self.get_device_by_identity(device.identity, expected=device)
                if current is None:
                    return False, (
                        "The selected device is no longer uniquely identifiable. "
                        "Refresh and select the device again."
                    )
                if current.kind not in (device.kind, "FTDI", "Unknown"):
                    return False, "The selected device kind changed. Refresh and select it again."
                if any(item.state in ("DriverError", "DeviceError") for item in devices):
                    return False, "Deployment blocked: a discovered device is in an error state."
                if current.state not in ("Online", "Unknown", "Bootloader"):
                    return False, "The selected device is not available for deployment."

                target = current.port_name
                if current.state == "Bootloader" and current.kind == "Pico":
                    pico_bootloaders = [
                        item for item in devices
                        if item.kind == "Pico" and item.state == "Bootloader"
                    ]
                    if len(pico_bootloaders) != 1:
                        return False, "PICOBOOT requires exactly one connected Pico bootloader."
                    target = "PICOBOOT"
                bootloaders = [item for item in devices if item.state == "Bootloader"]
                if len(bootloaders) > 1:
                    return False, "Deployment blocked: multiple devices are in bootloader mode."
                if bootloaders and bootloaders[0].identity != current.identity:
                    return False, "Deployment allowed only to the single bootloader device."
                if not target:
                    return False, "The selected device has no usable upload target."

                return self.cli.upload_firmware(
                    firmware_path=firmware_path,
                    target=target,
                    force=force,
                    no_interactive=True,
                    progress=device.kind == "ATxmega",
                    verbose=force,
                )
        except DeviceOperationBusy as error:
            return False, str(error)

    def install_drivers(
        self, *, operation: DeviceOperationLease | None = None
    ) -> tuple[bool, str]:
        """Install drivers using HarpRegulator."""
        try:
            with self.operations.operation("Driver installation", operation):
                return self.cli.install_drivers()
        except DeviceOperationBusy as error:
            return False, str(error)
