from nicegui import ui
from typing import List, Dict, Literal
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration for activity log"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


class UpdateWorkflow:
    """Update workflow panel component"""
    
    # Color mapping for log levels (CSS class names)
    LOG_COLORS = {
        LogLevel.INFO: "log-info",
        LogLevel.SUCCESS: "log-success",
        LogLevel.WARNING: "log-warning",
        LogLevel.ERROR: "log-error",
        LogLevel.DEBUG: "log-debug",
    }
    
    # Prefix icons for log levels
    LOG_PREFIXES = {
        LogLevel.INFO: "ℹ",
        LogLevel.SUCCESS: "✓",
        LogLevel.WARNING: "⚠",
        LogLevel.ERROR: "✗",
        LogLevel.DEBUG: "🔍",
    }
    
    def __init__(self):
        """Initialize update workflow component"""
        self.has_error = False
        self.error_message = ""
        
        # UI elements
        self.log = None
        self.alert_container = None
    
    def render(self):
        """Render the update workflow panel"""
        with ui.column().classes('workflow-container w-full'):
            # Workflow title
            ui.label('Activity Log').classes('workflow-title')
            
            # Log section
            self.log = ui.log(max_lines=100).classes('activity-log w-full')
            self.push_log('Ready to start firmware updates.', LogLevel.INFO)
            
            # Alert container (initially hidden)
            self.alert_container = ui.column().classes('hidden')
    
    def start_update(self, device_name: str, firmware_version: str):
        """
        Start an update workflow for a single device
        
        Args:
            device_name: Name of device being updated
            firmware_version: Firmware version being installed
        """
        self.has_error = False
        
        self.push_log(f'Starting firmware update for {device_name}', LogLevel.INFO)
        self.push_log(f'Target firmware version: {firmware_version}', LogLevel.INFO)
    
    def start_batch_update(self, device_name: str, device_count: int, firmware_version: str):
        """
        Start a batch update workflow for multiple devices with the same name
        
        Args:
            device_name: Name of devices being updated
            device_count: Number of devices to update
            firmware_version: Firmware version being installed
        """
        self.has_error = False
        
        self.push_log(f'Starting BATCH firmware update for {device_count} "{device_name}" devices', LogLevel.INFO)
        self.push_log(f'Target firmware version: {firmware_version}', LogLevel.INFO)
    
    def push_log(self, message: str, level: LogLevel = LogLevel.INFO):
        """
        Push a log message with a specific level and color
        
        Args:
            message: Log message text
            level: Log level (INFO, SUCCESS, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefix = self.LOG_PREFIXES.get(level, "")
        color_class = self.LOG_COLORS.get(level, "log-info")
        log_entry = f'[{timestamp}] {prefix} {message}'
        
        # Update UI with colored log entry
        if self.log:
            self.log.push(log_entry, classes=color_class)
    
    def show_error(self, error_message: str):
        """
        Show an error dialog
        
        Args:
            error_message: Error message text
        """
        self.has_error = True
        self.error_message = error_message
        
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Firmware Update Error').classes('text-h6 text-negative')
            ui.label(error_message).classes('text-sm mt-2')
            with ui.row().classes('gap-2 mt-4 justify-end w-full'):
                ui.button('Close', on_click=dialog.close).props('flat')
        
        dialog.open()
    
    def show_error_with_force(self, error_message: str):
        """
        Show an error dialog suggesting to enable force upload checkbox
        
        Args:
            error_message: Error message text
            force_checkbox: Reference to the force upload checkbox to enable
        """
        self.has_error = True
        self.error_message = error_message
        
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Firmware Update Failed').classes('text-h6 text-negative')
            ui.label(error_message).classes('text-sm mt-2')
            ui.label('To bypass safety checks, enable the "Force upload" checkbox and try again.').classes('text-sm mt-3 font-semibold text-warning')
            
            
            with ui.row().classes('gap-2 mt-4 justify-end w-full'):
                ui.button('Close', on_click=dialog.close).classes('btn btn-secondary')
        
        dialog.open()
    
    def hide_error(self):
        """Hide error alert"""
        self.has_error = False
        if self.alert_container:
            self.alert_container.classes(add='hidden')
    
    def on_retry(self):
        """Handle retry button click"""
        self.hide_error()
        self.push_log('Retrying update...', LogLevel.WARNING)
        ui.notify('Retrying update', type='info')
    
    def on_rollback(self):
        """Handle rollback button click"""
        self.hide_error()
        self.push_log('Rolling back to previous firmware...', LogLevel.WARNING)
        ui.notify('Rolling back firmware', type='warning')
    
    def complete_update(self, success: bool):
        """
        Complete the update workflow
        
        Args:
            success: Whether update completed successfully
        """
        if success:
            self.push_log('Firmware update completed successfully!', LogLevel.SUCCESS)
            ui.notify('Firmware update completed!', type='positive')
        else:
            self.push_log('Firmware update failed. Please check the logs and try again.', LogLevel.ERROR)
            self.show_error('Firmware update failed. Please check the logs and try again.')