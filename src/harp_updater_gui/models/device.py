from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class Device(BaseModel):
    """
    Model representing a Harp device based on HarpRegulator list output

    Example JSON:
    {
      "Confidence": "Low",
      "Kind": "Pico",
      "State": "Online",
      "PortName": "COM5",
      "WhoAmI": 1405,
      "DeviceDescription": "EnvironmentSensor",
      "SerialNumber": null,
      "FirmwareVersion": "0.2.0",
      "Source": "Pico USB Serial Port - USB\\VID_2E8A&PID_000A&MI_00\\6&369292A4&2&0000"
    }
    """

    confidence: str = Field(
        alias="Confidence", description="Device confidence level: High, Medium, Low"
    )
    kind: str = Field(
        alias="Kind", description="Device kind: Pico, ATxmega, or Unknown"
    )
    state: str = Field(
        alias="State", description="Device state: Online, Bootloader, DriverError, etc."
    )
    port_name: Optional[str] = Field(
        None, alias="PortName", description="COM port or device path"
    )
    who_am_i: Optional[int] = Field(
        None, alias="WhoAmI", description="Device WhoAmI register value"
    )
    device_description: Optional[str] = Field(
        None, alias="DeviceDescription", description="Human-readable device name"
    )
    serial_number: Optional[str] = Field(
        None, alias="SerialNumber", description="Device serial number"
    )
    firmware_version: Optional[str] = Field(
        None, alias="FirmwareVersion", description="Current firmware version"
    )
    hardware_version: Optional[str] = Field(
        None, alias="HardwareVersion", description="Hardware version"
    )
    source: Optional[str] = Field(
        None, alias="Source", description="Device source identifier"
    )

    class Config:
        populate_by_name = True

    @field_validator("serial_number", mode="before")
    def serialize_serial_number(cls, value):
        """Convert serial numbers coming in as ints to strings."""
        if value is None:
            return value
        return str(value)

    @model_validator(mode="after")
    def validate_port_name(self):
        """Validate that port_name is provided unless device is in Bootloader or DriverError state."""
        if self.state not in ["Bootloader", "DriverError"] and self.port_name is None:
            raise ValueError(
                f"port_name is required when device state is '{self.state}'"
            )
        return self

    @property
    def display_name(self) -> str:
        """Get a human-readable display name for the device"""
        if self.device_description:
            return self.device_description
        if self.who_am_i:
            return f"Device {self.who_am_i}"
        if self.port_name:
            return f"Device on {self.port_name}"
        return "Unknown Device"

    @property
    def health_status(self) -> str:
        """Get health status based on device state and confidence"""
        if self.state == "Online":
            return "Healthy"
        elif self.state == "Bootloader":
            return "Bootloader"
        elif self.state == "DriverError":
            return "Error"
        else:
            return "Unknown"

    @property
    def health_color(self) -> str:
        """Get color indicator for health status"""
        status = self.health_status
        if status == "Healthy":
            return "green"
        elif status == "Bootloader":
            return "yellow"
        elif status == "Error":
            return "red"
        else:
            return "gray"

    @property
    def metadata_line(self) -> str:
        """Get a formatted metadata line for display"""
        parts = []
        if self.port_name:
            parts.append(self.port_name)

        if self.hardware_version:
            parts.append(f"HW v{self.hardware_version}")

        if self.kind and self.kind != "Unknown":
            parts.append(self.kind)

        return " • ".join(parts)

    def __repr__(self):
        return f"<Device(name={self.display_name}, port={self.port_name}, kind={self.kind}, state={self.state})>"
