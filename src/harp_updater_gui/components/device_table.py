from nicegui import ui, app
from typing import Optional, Callable
from pathlib import Path
from harp_updater_gui.models.device import Device
from harp_updater_gui.services.device_manager import DeviceManager
from harp_updater_gui.services.firmware_service import FirmwareService


class DeviceTable:
    """Device table component with integrated firmware upload"""

    def __init__(
        self,
        device_manager: DeviceManager,
        firmware_service: FirmwareService,
        on_deploy: Optional[Callable] = None,
    ):
        """
        Initialize device table

        Args:
            device_manager: DeviceManager instance
            firmware_service: FirmwareService instance
            on_deploy: Callback when firmware deployment is initiated
        """
        self.device_manager = device_manager
        self.firmware_service = firmware_service
        self.on_deploy = on_deploy

        self.table = None
        self.selected_device: Optional[Device] = None
        self.firmware_file_path: Optional[str] = None
        self.force_upload_checkbox = None
        self.batch_update_checkbox = None
        self.file_path_label = None
        self.deploy_button = None
        self.connect_all_on_refresh_checkbox = None
        self.connect_all_on_refresh = False

        # Search and filter state
        self.filter_type = "All types"

    def _get_deploy_eligibility(self) -> tuple[bool, Optional[str]]:
        """Evaluate whether firmware deployment is currently allowed."""
        devices = self.device_manager.get_devices()

        if not devices:
            return False, "No devices available for firmware deployment"

        bootloader_devices = [d for d in devices if d.state == "Bootloader"]
        error_devices = [
            d for d in devices if d.state in ("DriverError", "DeviceError")
        ]

        # Never allow deployment when any device is in error state.
        if error_devices:
            return (
                False,
                "Deployment blocked: one or more devices are in DeviceError state",
            )

        # Allow exactly one Bootloader device, but only to that specific device.
        if len(bootloader_devices) == 1:
            if not self.selected_device:
                return False, "Select the Bootloader device to deploy firmware"

            bootloader_device = bootloader_devices[0]
            if self.selected_device.port_name != bootloader_device.port_name:
                return False, "Deployment allowed only to the single Bootloader device"

            if self.batch_update_checkbox and self.batch_update_checkbox.value:
                return (
                    False,
                    "Batch update is not allowed when exactly one device is in Bootloader state",
                )

            return True, None

        # If more than one device is in Bootloader, block all deployment.
        if len(bootloader_devices) > 1:
            return False, "Deployment blocked: multiple devices are in Bootloader state"

        return True, None

    def render(self):
        """Render the device table panel"""
        with ui.column().classes("device-table-container w-full mb-3"):
            # Header with controls
            with ui.row().classes("w-full items-center justify-between gap-4"):
                ui.label("Harp Devices").classes("text-2xl font-bold")

                with ui.row().classes("gap-4"):
                    # Search input with dynamic filtering
                    search_input = ui.input(placeholder="Search devices...").classes(
                        "w-48"
                    )

                    # Filter dropdown
                    ui.select(
                        options=["All types", "Pico", "ATxmega", "Healthy", "Error"],
                        value="All types",
                    ).classes("w-36").bind_value(self, "filter_type").on_value_change(
                        self.update_table
                    )

                    # Refresh button
                    ui.button("🔄 Refresh", on_click=self.refresh_devices).classes(
                        "btn btn-secondary"
                    )

            # Refresh behavior controls
            with ui.row().classes("w-full items-center justify-end mb-2"):
                self.connect_all_on_refresh_checkbox = ui.checkbox(
                    "Connect all"
                ).tooltip(
                    "When enabled, all detected devices will be connected during refresh, allowing for device metadata to be updated. Use with caution as this may disrupt devices that are currently in use."
                )
                self.connect_all_on_refresh_checkbox.bind_value(
                    self, "connect_all_on_refresh"
                )
                self.connect_all_on_refresh_checkbox.on_value_change(
                    self.on_connect_all_refresh_toggle
                )

            # Device table
            self.table = (
                ui.table(
                    columns=[
                        {
                            "name": "name",
                            "label": "Device Name",
                            "field": "name",
                            "align": "left",
                            "sortable": True,
                        },
                        {
                            "name": "port",
                            "label": "Port",
                            "field": "port",
                            "align": "left",
                            "sortable": True,
                        },
                        {
                            "name": "kind",
                            "label": "Kind",
                            "field": "kind",
                            "align": "left",
                            "sortable": True,
                        },
                        {
                            "name": "hardware",
                            "label": "Hardware",
                            "field": "hardware",
                            "align": "left",
                            "sortable": True,
                        },
                        {
                            "name": "firmware",
                            "label": "Firmware",
                            "field": "firmware",
                            "align": "left",
                            "sortable": True,
                        },
                        {
                            "name": "status",
                            "label": "Status",
                            "field": "status",
                            "align": "left",
                            "sortable": True,
                        },
                    ],
                    rows=[],
                    row_key="port",
                    selection="single",
                    pagination={
                        "rowsPerPage": 10,
                        "sortBy": "name",
                        "descending": False,
                    },
                )
                .classes("w-full")
                .props("flat bordered")
                .on("selection", self.on_row_select)
            )

            self.table.add_slot(
                "body-cell-status",
                """
                <q-td :props="props">
                    <q-badge :color="props.row.status_color">
                        {{ props.row.status }}
                    </q-badge>
                </q-td>
            """,
            )

            # Bind search input to table filter after table is created
            search_input.bind_value(self.table, "filter")

            # Firmware upload section
            with ui.card().classes("w-full p-4 firmware-upload-card"):
                ui.label("Firmware Upload").classes("text-lg font-semibold mb-3")

                with ui.row().classes("w-full items-start gap-8"):
                    # Column 1: File picker
                    with ui.column().classes("flex-1 gap-2"):
                        ui.label("Select Firmware File").classes("text-sm font-medium")
                        with ui.row().classes("gap-2 items-center"):
                            ui.button(
                                "📁 Browse", on_click=self.browse_firmware
                            ).classes("btn btn-secondary")
                            self.file_path_label = ui.label("No file selected").classes(
                                "text-sm text-secondary"
                            )

                    # Column 2: Checkboxes and Deploy button
                    with ui.column().classes("gap-2"):
                        # Checkboxes
                        self.batch_update_checkbox = ui.checkbox(
                            "Update all devices with same name"
                        )
                        self.batch_update_checkbox.tooltip(
                            "When enabled, all devices with the same name as the selected device will be updated"
                        )
                        self.force_upload_checkbox = ui.checkbox(
                            "Force upload (bypass safety checks)"
                        )

                        # Deploy button
                        self.deploy_button = ui.button(
                            "🚀 Deploy Firmware", on_click=self.deploy_firmware
                        ).classes("btn btn-primary")
                    self.deploy_button.set_enabled(False)

            # Initial load
            self.refresh_devices(show_notification=False)

    def refresh_devices(self, show_notification: bool = True):
        """Refresh device list from device manager"""
        if show_notification:
            ui.notify("Checking for devices...", type="info")
        try:
            devices = self.device_manager.refresh_devices(
                allow_connect=self.connect_all_on_refresh
            )
            self.update_table()
            if show_notification:
                ui.notify(f"Found {len(devices)} device(s)", type="positive")
        except Exception as e:
            ui.notify(f"Error: {str(e)}", type="negative")

    def on_connect_all_refresh_toggle(self, e):
        """Handle connect-on-refresh toggle changes."""

        print(f"Connect on refresh set to: {self.connect_all_on_refresh}")

        if self.connect_all_on_refresh:
            ui.notify("Connect on refresh enabled", type="info")
            self.refresh_devices(show_notification=False)
        else:
            ui.notify("Connect on refresh disabled", type="info")

    def update_table(self):
        """Update the device table with filtered data"""
        # Only filter by device type since search is handled by table's built-in filter
        devices = self.device_manager.filter_devices(
            search_query=None,  # Don't filter by search query - the table handles this
            device_type=self.filter_type if self.filter_type != "All types" else None,
        )

        rows = []
        for device in devices:
            # Map health color to Quasar color
            status_color = (
                "positive"
                if device.health_color == "green"
                else ("warning" if device.health_color == "yellow" else "negative")
            )

            rows.append(
                {
                    "name": device.display_name,
                    "port": device.port_name,
                    "kind": "PICO"
                    if device.kind == "Pico"
                    else (device.kind or "Unknown"),
                    "hardware": f"v{device.hardware_version or '?'}",
                    "firmware": f"v{device.firmware_version or '?'}",
                    "status": device.health_status,
                    "status_color": status_color,
                }
            )

        self.table.rows = rows
        self.table.update()

        # Enable deploy button if firmware is selected
        if self.firmware_file_path and self.selected_device:
            self.deploy_button.set_enabled(True)

    def on_row_select(self, e):
        """Handle row selection"""
        # Access the table's selected rows directly
        if self.table.selected and len(self.table.selected) > 0:
            selected_row = self.table.selected[0]
            port_name = selected_row["port"]

            # Find the device by port name
            devices = self.device_manager.get_devices()
            self.selected_device = next(
                (d for d in devices if d.port_name == port_name), None
            )

            if self.selected_device:
                # Count how many devices have the same name
                same_name_count = sum(
                    1
                    for d in devices
                    if d.display_name == self.selected_device.display_name
                )
                if same_name_count > 1:
                    ui.notify(
                        f"Selected: {self.selected_device.display_name} ({same_name_count} devices with this name)",
                        type="info",
                    )
                else:
                    ui.notify(
                        f"Selected: {self.selected_device.display_name}", type="info"
                    )

            # Enable deploy button if firmware is selected
            if self.firmware_file_path and self.selected_device:
                self.deploy_button.set_enabled(True)
        else:
            self.selected_device = None
            self.deploy_button.set_enabled(False)

    async def browse_firmware(self):
        """Open file picker to browse for firmware file"""
        # Prefer native dialog when available (native mode)
        if app.native.main_window:
            try:
                paths = await app.native.main_window.create_file_dialog(
                    allow_multiple=False,
                    file_types=["Firmware files (*.uf2;*.hex)"],
                )
            except Exception:
                ui.notify(
                    "Unable to open native file dialog. Falling back to browser picker.",
                    type="warning",
                )
            else:
                if paths:
                    selected_path = paths[0]
                    self.firmware_file_path = selected_path
                    self.file_path_label.set_text(Path(selected_path).name)
                    if self.selected_device:
                        self.deploy_button.set_enabled(True)
                    ui.notify(f"Selected: {Path(selected_path).name}", type="info")
                return

        # Browser-based picker fallback
        try:
            result = await ui.run_javascript(
                """
                new Promise((resolve) => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = '.uf2,.hex';
                    input.onchange = (e) => {
                        const file = e.target.files[0];
                        if (file) {
                            resolve(file.name);
                        } else {
                            resolve(null);
                        }
                    };
                    input.click();
                })
            """,
                timeout=60.0,
            )
        except TimeoutError:
            ui.notify(
                "File picker did not respond in time. Please try again.", type="warning"
            )
            return

        if result:
            self.firmware_file_path = result
            self.file_path_label.set_text(result)
            if self.selected_device:
                self.deploy_button.set_enabled(True)
            ui.notify(f"Selected: {result}", type="info")

    async def deploy_firmware(self):
        """Deploy firmware to selected device(s)"""
        if not self.selected_device:
            ui.notify("Please select a device first", type="warning")
            return

        if not self.firmware_file_path:
            ui.notify("Please select a firmware file", type="warning")
            return

        can_deploy, blocked_reason = self._get_deploy_eligibility()
        if not can_deploy:
            ui.notify(blocked_reason, type="warning")
            return

        # Disable button during deployment
        self.deploy_button.set_enabled(False)

        try:
            if self.on_deploy:
                if (
                    self.selected_device.kind == "Pico"
                    or self.selected_device.kind == "PICO"
                ):
                    self.force_upload_checkbox.set_value(
                        True
                    )  # Force upload for Pico devices

                force = self.force_upload_checkbox.value
                batch_update = self.batch_update_checkbox.value

                if batch_update:
                    # Find all devices with the same name
                    all_devices = self.device_manager.get_devices()
                    devices_to_update = [
                        d
                        for d in all_devices
                        if d.display_name == self.selected_device.display_name
                    ]
                    await self.on_deploy(
                        devices_to_update, self.firmware_file_path, force
                    )
                else:
                    # Single device update
                    await self.on_deploy(
                        [self.selected_device], self.firmware_file_path, force
                    )
        finally:
            # Re-enable button after deployment
            if self.selected_device and self.firmware_file_path:
                self.deploy_button.set_enabled(True)
                self.force_upload_checkbox.set_value(
                    False
                )  # Reset force upload checkbox after operation
