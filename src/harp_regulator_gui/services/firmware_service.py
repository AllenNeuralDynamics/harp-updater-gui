from typing import List, Optional, Dict, Any
from pathlib import Path
from harp_regulator_gui.services.cli_wrapper import CLIWrapper
from harp_regulator_gui.models.firmware import Firmware
from harp_regulator_gui.models.device import Device


class FirmwareService:
    """Service for firmware operations"""
    
    def __init__(self, cli_path: str = "HarpRegulator"):
        """
        Initialize firmware service
        
        Args:
            cli_path: Path to HarpRegulator executable
        """
        self.cli = CLIWrapper(cli_path)
        self.firmware_cache: Dict[str, Dict[str, Any]] = {}
    
    def inspect_firmware(self, firmware_path: str) -> Optional[Dict[str, Any]]:
        """
        Inspect a firmware file and get its metadata
        
        Args:
            firmware_path: Path to firmware file (.uf2 or .hex)
            
        Returns:
            Dictionary with firmware information or None on error
        """
        # Check cache first
        if firmware_path in self.firmware_cache:
            return self.firmware_cache[firmware_path]
        
        firmware_info = self.cli.inspect_firmware(firmware_path)
        
        if firmware_info:
            self.firmware_cache[firmware_path] = firmware_info
        
        return firmware_info
    
    def get_firmware_type(self, firmware_path: str) -> Optional[str]:
        """
        Get the firmware file type (UF2 for Pico, HEX for ATxmega)
        
        Args:
            firmware_path: Path to firmware file
            
        Returns:
            File extension (.uf2 or .hex) or None
        """
        path = Path(firmware_path)
        ext = path.suffix.lower()
        
        if ext in ['.uf2', '.hex']:
            return ext
        
        return None
    
    def is_compatible(self, firmware_info: Dict[str, Any], hardware_version: str) -> bool:
        """
        Check if firmware is compatible with hardware version
        
        Args:
            firmware_info: Firmware metadata from inspect
            hardware_version: Hardware version string
            
        Returns:
            True if compatible
        """
        # This would need to parse the firmware info structure
        # For now, return True as a placeholder
        return True
    
    def get_available_firmware_versions(self, device_type: str) -> List[str]:
        """
        Get available firmware versions for a device type
        
        This is a placeholder - in a real implementation, this would
        query a firmware repository or local directory
        
        Args:
            device_type: Device type (e.g., "EnvironmentSensor")
            
        Returns:
            List of available firmware version strings
        """
        # Placeholder implementation
        return ["v0.9.1", "v0.9.0", "v0.5.0"]
    
    def download_firmware(self, version: str, device_type: str, output_path: str) -> bool:
        """
        Download firmware from a repository
        
        This is a placeholder - in a real implementation, this would
        download from a web service or package manager
        
        Args:
            version: Firmware version to download
            device_type: Device type
            output_path: Where to save the firmware file
            
        Returns:
            True if successful
        """
        # Placeholder implementation
        print(f"Would download {device_type} firmware {version} to {output_path}")
        return False
    
    def validate_firmware_file(self, device_kind: str, firmware_path: str) -> tuple[bool, str]:
        """
        Validate that a firmware file exists and is the correct format
        
        Args:
            device_kind: Kind of device (e.g., "Pico" or "ATxmega")
            firmware_path: Path to firmware file
            
        Returns:
            True if file is valid
        """
        path = Path(firmware_path)
        
        if not path.exists():
            return False, "Firmware file does not exist"
        
        ext = self.get_firmware_type(firmware_path)
        if ext not in ['.uf2', '.hex']:
            return False, "Unsupported firmware file type"
        
        # Check compatibility based on device kind
        if device_kind == "Pico" and ext != '.uf2':
            return False, "Pico devices require .uf2 firmware files"

        if device_kind == "ATxmega" and ext != '.hex':
            return False, "ATxmega devices require .hex firmware files"

        # Could add more validation here (e.g., file size, magic bytes)
        return True, ""
    
    def fetch_available_firmware(self, device_id: str) -> List[str]:
        """
        Fetch available firmware versions for a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            List of available firmware versions
        """
        return self.get_available_firmware_versions(device_id)
    
    def check_firmware_compatibility(self, device_id: str, firmware_version: str) -> bool:
        """
        Check if a firmware version is compatible with a device
        
        Args:
            device_id: Device identifier
            firmware_version: Firmware version string
            
        Returns:
            True if compatible
        """
        # Placeholder implementation
        return True