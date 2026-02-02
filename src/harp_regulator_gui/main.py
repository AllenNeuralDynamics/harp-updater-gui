#!/usr/bin/env python3
"""
HARP Firmware Updater GUI

A graphical user interface for managing Harp devices and updating firmware.
Built with NiceGUI and integrating with the HarpRegulator CLI tool.
"""

import os
import sys
from pathlib import Path
from nicegui import ui, app, run
from harp_regulator_gui.components.header import Header
from harp_regulator_gui.components.device_table import DeviceTable
from harp_regulator_gui.components.update_workflow import UpdateWorkflow
from harp_regulator_gui.services.device_manager import DeviceManager
from harp_regulator_gui.services.firmware_service import FirmwareService
from harp_regulator_gui.models.device import Device

# Get the path to the static directory
STATIC_DIR = Path(__file__).parent / 'static'


class HarpFirmwareUpdaterApp:
    """Main application class"""
    
    def __init__(self):
        """Initialize the application"""
        # Initialize services
        self.device_manager = DeviceManager("C:\\Users\\anjal\\Projects\\aind\\harp-regulator\\artifacts\\bin\\HarpRegulator\\debug\\HarpRegulator.exe")
        self.firmware_service = FirmwareService("C:\\Users\\anjal\\Projects\\aind\\harp-regulator\\artifacts\\bin\\HarpRegulator\\debug\\HarpRegulator.exe")
        
        # Initialize components (will be set in render)
        self.header = None
        self.device_table = None
        self.update_workflow = None
    
    def on_device_select(self, device: Device):
        """
        Handle device selection
        
        Args:
            device: Selected device
        """
        # No longer needed with integrated table
        pass
    
    async def on_firmware_deploy(self, device: Device, firmware_path: str, force: bool = False):
        """
        Handle firmware deployment
        
        Args:
            device: Target device
            firmware_path: Path to firmware file or version string
            force: Force upload even if checks fail
        """
        # Show loading spinner
        with ui.dialog() as loading_dialog, ui.card().classes('items-center p-6'):
            ui.spinner(size='xl', color='primary')
            ui.label('Uploading firmware...').classes('text-lg mt-4')
            ui.label('Please wait, do not disconnect the device').classes('text-sm text-secondary mt-2')
        
        loading_dialog.open()
        
        try:
            # Start update workflow
            self.update_workflow.start_update(device.display_name, firmware_path)
            
            # Close any device connections by refreshing without connecting
            self.update_workflow.add_log('Closing device connections...')
            await run.cpu_bound(self.device_manager.refresh_devices, allow_connect=False)
            
            # Wait for OS to release port handles
            await run.io_bound(lambda: __import__('time').sleep(3))
            
            # Step 1: Validate firmware file
            self.update_workflow.add_log(f'Validating firmware file: {firmware_path}')
            
            # Validate using firmware service
            if not self.firmware_service.validate_firmware_file(firmware_path):
                self.update_workflow.add_log(f'✗ Error: Invalid firmware file')
                self.update_workflow.show_error(f'Invalid firmware file. Must be .uf2 or .hex format: {firmware_path}')
                ui.notify('Invalid firmware file', type='negative')
                return
            
            self.update_workflow.add_log(f'✓ Firmware file validated')
            
            # Step 2: Flash firmware
            if force:
                self.update_workflow.add_log(f'Starting FORCED firmware upload to {device.display_name}...')
            else:
                self.update_workflow.add_log(f'Starting firmware upload to {device.display_name}...')
            
            # Upload firmware using device manager (run in thread to avoid blocking UI)
            success, output = await run.cpu_bound(
                self.device_manager.upload_firmware_to_device,
                device,
                firmware_path,
                force
            )
            
            if success:
                self.update_workflow.add_log('✓ Firmware uploaded successfully')
                
                # Step 3: Verify
                self.update_workflow.add_log('Verifying firmware installation...')
                
                # Give device time to reboot and reconnect (5 seconds)
                self.update_workflow.add_log('Waiting for device to reboot...')
                await run.io_bound(lambda: __import__('time').sleep(5))
                
                self.update_workflow.add_log('✓ Firmware verified')
                self.update_workflow.complete_update(True)
                
                # Refresh device table to get updated info
                self.device_table.refresh_devices()
                
            else:
                self.update_workflow.add_log(f'✗ Upload failed: {output}')
                
                # If not already forced, suggest enabling force upload checkbox
                if not force:
                    error_msg = f'Firmware upload failed: {output}'
                    self.update_workflow.show_error_with_force(error_msg)
                else:
                    self.update_workflow.show_error(f'Forced firmware upload failed: {output}')
                
                ui.notify('Firmware upload failed', type='negative')
                
        except Exception as e:
            self.update_workflow.add_log(f'✗ Error during upload: {str(e)}')
            self.update_workflow.show_error(f'Error during firmware upload: {str(e)}')
            ui.notify(f'Upload error: {str(e)}', type='negative')
        finally:
            # Close loading dialog
            loading_dialog.close()
    
    def render(self):
        """Render the main application UI"""
        # Configure NiceGUI color theme
        ui.colors(
            primary='#2563eb',      # Blue for primary actions
            secondary='#6b7280',    # Gray for secondary elements
            accent='#7c3aed',       # Purple accent
            positive='#10b981',     # Green for success states
            negative='#ef4444',     # Red for errors
            info='#06b6d4',         # Cyan for info
            warning='#f59e0b',      # Orange for warnings
        )
        
        # Create dark mode toggle
        dark_mode = ui.dark_mode()
        
        # Create header with dark mode toggle
        self.header = Header(dark_mode_toggle=dark_mode)
        
        # Main content area with device table and activity log
        with ui.element('div').classes('app-container'):
            # Use splitter for resizable device table and activity log
            with ui.splitter(limits=(30, 80), value=75).classes('flex-1') as splitter:
                with splitter.before:
                    # Device table with integrated firmware upload
                    self.device_table = DeviceTable(
                        device_manager=self.device_manager,
                        firmware_service=self.firmware_service,
                        on_deploy=self.on_firmware_deploy
                    )
                    self.device_table.render()
                
                with splitter.after:
                    # Activity log
                    self.update_workflow = UpdateWorkflow()
                    self.update_workflow.render()
        
        # Footer
        with ui.footer().classes('footer-container'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('© 2026 Allen Institute').classes('text-sm')
                ui.link('Help and Documentation', 'https://github.com/harp-tech/protocol', new_tab=True).classes('footer-link')


def start_app():
    """Initialize and start the application."""
    # Ensure NiceGUI error pages can locate the running script when launched via entrypoints
    sys.argv[0] = str(Path(__file__).resolve())

    # Add static files directory
    app.add_static_files('/static', str(STATIC_DIR))
    
    # Load custom CSS
    css_path = STATIC_DIR / 'styles.css'
    if css_path.exists():
        with open(css_path, 'r', encoding='utf-8') as f:
            ui.add_head_html(f'<style>{f.read()}</style>')

    # Create app instance and render UI
    app_instance = HarpFirmwareUpdaterApp()
    app_instance.render()

    # Run the application
    ui.run(
        title='HARP Regulator GUI',
        favicon='🔧',
        host="0.0.0.0",
        port=4277,
        dark=None,  # Start in auto mode (respects system preference)
        reload=False,
        show=True,
        native=True,
        window_size=(1200, 1000),
    )


# Start the app if running as a module
if __name__ in {"__main__", "__mp_main__"}:
    start_app()
