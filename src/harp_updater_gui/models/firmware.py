from pydantic import BaseModel
from typing import List, Optional


class Firmware(BaseModel):
    version: str
    compatible_hardware: List[str]
    release_notes: Optional[str] = None

    def is_compatible(self, hardware_version: str) -> bool:
        return hardware_version in self.compatible_hardware
