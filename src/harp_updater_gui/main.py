#!/usr/bin/env python3
"""
Harp Firmware Updater GUI

A graphical user interface for managing Harp devices and updating firmware.
Built with NiceGUI and integrating with the HarpRegulator CLI tool.
"""

from multiprocessing import freeze_support
import sys
import logging
import shutil
from pathlib import Path
from nicegui import ui, app, run
from nicegui import core as nicegui_core
from harp_updater_gui.components.header import Header
from harp_updater_gui.components.device_table import DeviceTable
from harp_updater_gui.components.update_workflow import UpdateWorkflow, LogLevel
from harp_updater_gui.services.device_manager import DeviceManager
from harp_updater_gui.services.firmware_service import FirmwareService
from harp_updater_gui.utils.update_audit_logger import (
    log_successful_firmware_update,
    setup_update_audit_logger,
)
from harp_updater_gui.models.device import Device
from typing import List, Optional


def _resolve_static_dir() -> Optional[Path]:
    """Resolve static directory for both source and frozen (PyInstaller) runs."""
    candidates = [Path(__file__).resolve().parent / "static"]

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            meipass_path = Path(meipass)
            candidates.extend(
                [
                    meipass_path / "static",
                    meipass_path / "harp_updater_gui" / "static",
                ]
            )

        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                exe_dir / "static",
                exe_dir / "_internal" / "static",
                exe_dir / "_internal" / "harp_updater_gui" / "static",
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    return None


STATIC_DIR = _resolve_static_dir()
_SHARED_CSS_INJECTED = False


class HarpFirmwareUpdaterApp:
    """Main application class"""

    def __init__(self):
        """Initialize the application"""

        # Resolve paths to external tools per os depending on source vs frozen execution
        self.regulator_path = shutil.which("HarpRegulator.exe")
        if self.regulator_path is None:
            if getattr(sys, "frozen", False):
                exe_dir = Path(sys.executable).resolve().parent
                self.regulator_path = str(exe_dir / "_internal" / "harp_regulator" / "win-x64" /"HarpRegulator.exe")
            else:
                self.regulator_path = str(Path(__file__).resolve().parent.parent.parent / "deps" / "harp_regulator" / "win-x64" / "HarpRegulator.exe")
        
        print(f"Resolved HarpRegulator path: {self.regulator_path}")


        # Initialize services
        self.device_manager = DeviceManager(self.regulator_path)
        self.firmware_service = FirmwareService(self.regulator_path)
        self.audit_logger = setup_update_audit_logger()

        # Initialize components (will be set in render)
        self.header = None
        self.device_table = None
        self.update_workflow = None


    async def on_firmware_deploy(
        self, devices: List[Device], firmware_path: str, force: bool = False
    ):
        """
        Handle firmware deployment for one or more devices (batch update support)

        Args:
            devices: List of target devices (supports batch updates for devices with same name)
            firmware_path: Path to firmware file or version string
            force: Force upload even if checks fail
        """
        # Handle single device passed as non-list for backwards compatibility
        if isinstance(devices, Device):
            devices = [devices]

        total_devices = len(devices)
        is_batch = total_devices > 1

        # Show loading spinner
        with ui.dialog() as loading_dialog, ui.card().classes("items-center p-6"):
            ui.spinner(size="xl", color="primary")
            if is_batch:
                upload_label = ui.label(
                    f"Uploading firmware to {total_devices} devices..."
                ).classes("text-lg mt-4")
            else:
                upload_label = ui.label("Uploading firmware...").classes("text-lg mt-4")
            ui.label("Please wait, do not disconnect the device(s)").classes(
                "text-sm text-secondary mt-2"
            )

        loading_dialog.open()

        try:
            # Start update workflow
            if is_batch:
                device_names = set(d.display_name for d in devices)
                if len(device_names) == 1:
                    self.update_workflow.start_batch_update(
                        list(device_names)[0], total_devices, firmware_path
                    )
                else:
                    self.update_workflow.push_log(
                        f"Starting batch firmware update for {total_devices} devices",
                        LogLevel.INFO,
                    )
                    self.update_workflow.push_log(
                        f"Target firmware: {firmware_path}", LogLevel.INFO
                    )
            else:
                self.update_workflow.start_update(
                    devices[0].display_name, firmware_path
                )

            # Step 1: Validate firmware file
            self.update_workflow.push_log(
                f"Validating firmware file: {firmware_path}", LogLevel.INFO
            )

            # Validate using firmware service
            valid, error_msg = self.firmware_service.validate_firmware_file(
                devices[0].kind, firmware_path
            )
            if not valid:
                self.update_workflow.push_log(
                    f"Invalid firmware file: {error_msg}", LogLevel.ERROR
                )
                self.update_workflow.show_error(f"Invalid firmware file: {error_msg}")
                ui.notify("Invalid firmware file", type="negative")
                return

            self.update_workflow.push_log("Firmware file validated", LogLevel.SUCCESS)

            # Step 1.5: Close any device connections by refreshing without connecting
            self.update_workflow.push_log(
                "Closing device connections...", LogLevel.INFO
            )
            await run.cpu_bound(
                self.device_manager.refresh_devices, allow_connect=False
            )

            # Wait for OS to release port handles
            await run.io_bound(lambda: __import__("time").sleep(3))

            # Track results for batch updates
            success_count = 0
            fail_count = 0
            successful_updates: list[dict[str, str]] = []

            # Step 2: Flash firmware to each device
            for idx, device in enumerate(devices, 1):
                previous_firmware_version = device.firmware_version or "unknown"
                if is_batch:
                    upload_label.set_text(
                        f"Uploading firmware ({idx}/{total_devices})..."
                    )
                    self.update_workflow.push_log(
                        f"--- Device {idx}/{total_devices}: {device.display_name} ({device.port_name}) ---",
                        LogLevel.INFO,
                    )

                if force:
                    self.update_workflow.push_log(
                        f"Starting FORCED firmware upload to {device.display_name}...",
                        LogLevel.WARNING,
                    )
                else:
                    self.update_workflow.push_log(
                        f"Starting firmware upload to {device.display_name} ({device.port_name})...",
                        LogLevel.INFO,
                    )

                # Upload firmware using device manager (run in thread to avoid blocking UI)
                success, output = await run.cpu_bound(
                    self.device_manager.upload_firmware_to_device,
                    device,
                    firmware_path,
                    force,
                )

                if success:
                    success_count += 1
                    successful_updates.append(
                        {
                            "device_name": device.display_name,
                            "port_name": device.port_name,
                            "previous_firmware_version": previous_firmware_version,
                        }
                    )
                    self.update_workflow.push_log(
                        f"Firmware uploaded successfully to {device.display_name}",
                        LogLevel.SUCCESS,
                    )

                    # Wait between devices for batch updates
                    if is_batch and idx < total_devices:
                        self.update_workflow.push_log(
                            "Waiting before next device...", LogLevel.INFO
                        )
                        await run.io_bound(lambda: __import__("time").sleep(2))
                else:
                    fail_count += 1
                    self.update_workflow.push_log(
                        f"Upload failed for {device.display_name}: {output}",
                        LogLevel.ERROR,
                    )

                    # For single device, show error dialog
                    if not is_batch:
                        if not force:
                            error_msg = f"Firmware upload failed: {output}"
                            self.update_workflow.show_error_with_force(error_msg)
                        else:
                            self.update_workflow.show_error(
                                f"Forced firmware upload failed: {output}"
                            )
                        ui.notify("Firmware upload failed", type="negative")
                        return

            # Step 3: Verify and complete
            if is_batch:
                self.update_workflow.push_log(
                    f"Batch update complete: {success_count}/{total_devices} successful",
                    LogLevel.SUCCESS if fail_count == 0 else LogLevel.WARNING,
                )

                if fail_count > 0:
                    self.update_workflow.push_log(
                        f"{fail_count} device(s) failed to update", LogLevel.ERROR
                    )
                    ui.notify(
                        f"Batch update: {success_count} succeeded, {fail_count} failed",
                        type="warning",
                    )
                else:
                    self.update_workflow.push_log(
                        "All devices updated successfully!", LogLevel.SUCCESS
                    )
                    ui.notify(
                        f"Successfully updated {success_count} device(s)!",
                        type="positive",
                    )
            else:
                self.update_workflow.push_log(
                    "Verifying firmware installation...", LogLevel.INFO
                )

                # Give device time to reboot and reconnect (3 seconds)
                self.update_workflow.push_log(
                    "Waiting for device to reboot...", LogLevel.INFO
                )
                await run.io_bound(lambda: __import__("time").sleep(3))

                self.update_workflow.push_log("Firmware verified", LogLevel.SUCCESS)
                self.update_workflow.complete_update(True)

            # Close loading dialog
            loading_dialog.close()

            # Refresh device table to get updated info
            await self.device_table.refresh_devices(False)

            refreshed_devices = {
                d.port_name: (d.firmware_version or "unknown")
                for d in self.device_manager.get_devices()
            }
            for update in successful_updates:
                new_firmware_version = refreshed_devices.get(
                    update["port_name"], "unknown"
                )
                try:
                    log_successful_firmware_update(
                        logger=self.audit_logger,
                        device_name=update["device_name"],
                        port_name=update["port_name"],
                        previous_firmware_version=update[
                            "previous_firmware_version"
                        ],
                        new_firmware_version=new_firmware_version,
                    )
                except Exception as logging_error:
                    self.update_workflow.push_log(
                        f"Audit logging failed for {update['device_name']}: {logging_error}",
                        LogLevel.WARNING,
                    )

        except Exception as e:
            self.update_workflow.push_log(
                f"Error during upload: {str(e)}", LogLevel.ERROR
            )
            self.update_workflow.show_error(f"Error during firmware upload: {str(e)}")
            ui.notify(f"Upload error: {str(e)}", type="negative")
        finally:
            # Close loading dialog
            loading_dialog.close()

    def render(self):
        """Render the main application UI"""
        # Configure NiceGUI color theme
        ui.colors(
            primary="#2563eb",  # Blue for primary actions
            secondary="#6b7280",  # Gray for secondary elements
            accent="#7c3aed",  # Purple accent
            positive="#10b981",  # Green for success states
            negative="#ef4444",  # Red for errors
            info="#06b6d4",  # Cyan for info
            warning="#f59e0b",  # Orange for warnings
        )

        # Create dark mode toggle
        dark_mode = ui.dark_mode()

        # Create header with dark mode toggle
        self.header = Header(dark_mode_toggle=dark_mode)

        # Main content area with device table and activity log
        with ui.element("div").classes("app-container"):
            # Use splitter for resizable device table and activity log
            with ui.splitter(limits=(30, 80), value=70).classes("flex-1") as splitter:
                with splitter.before:
                    # Device table with integrated firmware upload
                    self.device_table = DeviceTable(
                        device_manager=self.device_manager,
                        firmware_service=self.firmware_service,
                        on_deploy=self.on_firmware_deploy,
                    )
                    self.device_table.render()

                with splitter.after:
                    # Activity log
                    self.update_workflow = UpdateWorkflow()
                    self.update_workflow.render()

                with splitter.separator:
                    ui.icon(name="drag_indicator", size="sm", color="accent")

        # Footer
        with ui.footer().classes("footer-container"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("© 2026 Allen Institute").classes("text-sm")
                ui.link(
                    "Help and Documentation",
                    "https://harp-updater-gui.readthedocs.io/en/latest/",
                    new_tab=True,
                ).classes("footer-link")


def start_app():
    """Initialize and start the application."""
    css_content = None
    if STATIC_DIR:
        css_path = STATIC_DIR / "styles.css"
        if css_path.exists():
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

    def root() -> None:
        global _SHARED_CSS_INJECTED
        if css_content and not _SHARED_CSS_INJECTED:
            ui.add_head_html(f"<style>{css_content}</style>", shared=True)
            _SHARED_CSS_INJECTED = True

        app_instance = HarpFirmwareUpdaterApp()
        app_instance.render()

    if nicegui_core.script_mode:
        if nicegui_core.script_client is not None:
            nicegui_core.script_client.delete()
            nicegui_core.script_client = None
        nicegui_core.script_mode = False

    # Run the application
    try:
        ui.run(
            root=root,
            title="Harp Updater GUI",
            favicon="🔧",
            host="0.0.0.0",
            port=4277,
            dark=None,  # Start in auto mode (respects system preference)
            reload=False,
            show=True,
            native=True,
            window_size=(1350, 1000),
        )
    except KeyboardInterrupt:
        # Clean shutdown on Ctrl+C
        pass

# Add static files directory if present
if STATIC_DIR:
    app.add_static_files("/static", str(STATIC_DIR))
else:
    logging.warning("Static assets directory not found; continuing without /static.")

# Start the app when executed directly.
# Do not start on "__mp_main__" because Windows multiprocessing workers
# (used by run.cpu_bound) import this module under that name.
if __name__ == "__main__":
    freeze_support()  # For PyInstaller compatibility
    start_app()
