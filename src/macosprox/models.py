"""Pydantic models for VM data structures"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class VMType(str, Enum):
    """VM type enumeration"""
    LINUX = "linux"


class VMStatus(str, Enum):
    """VM status enumeration"""
    CREATED = "created"
    STOPPED = "stopped"
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    PAUSED = "paused"
    PAUSING = "pausing"
    RESUMING = "resuming"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"


class VMInfo(BaseModel):
    """Model for VM information returned by create_linux_vm"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., description="VM name")
    type: VMType = Field(..., description="VM type")
    cpu_count: int = Field(..., gt=0, description="Number of CPU cores")
    memory_gb: int = Field(..., gt=0, description="Memory size in GB")
    disk_gb: int = Field(..., gt=0, description="Disk size in GB")
    disk_path: str = Field(..., description="Path to disk image file")
    vm_dir: str = Field(..., description="VM directory path")
    status: VMStatus = Field(..., description="VM status")


class VMListItem(BaseModel):
    """Model for VM list items returned by list_vms"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., description="VM name")
    path: str = Field(..., description="VM directory path")
    exists: bool = Field(..., description="Whether VM directory exists")


class VirtualizationSupport(BaseModel):
    """Model for virtualization support information"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    supported: bool = Field(..., description="Whether virtualization is supported")
    framework_available: bool = Field(..., description="Whether Virtualization framework is available")
    message: str = Field(..., description="Support status message")
    pyobjc_version: Optional[str] = Field(None, description="PyObjC version if available")
    error: Optional[str] = Field(None, description="Error message if not supported")


class VMCreateRequest(BaseModel):
    """Model for VM creation request parameters"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, description="VM name")
    cpu_count: int = Field(2, gt=0, le=32, description="Number of CPU cores")
    memory_size_gb: int = Field(4, gt=0, le=128, description="Memory size in GB")
    disk_size_gb: int = Field(20, gt=0, le=1000, description="Disk size in GB")
    iso_path: Optional[str] = Field(None, description="Path to Linux ISO file")
    
    def validate_iso_path(self) -> None:
        """Validate that ISO path exists if provided"""
        if self.iso_path and not Path(self.iso_path).exists():
            raise ValueError(f"ISO file not found: {self.iso_path}")