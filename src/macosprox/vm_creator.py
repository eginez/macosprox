"""VM Creator using Apple's Virtualization Framework via PyObjC"""

from __future__ import annotations

import subprocess
from pathlib import Path
import logging

from .models import VMInfo, VMListItem, VirtualizationSupport, VMType, VMStatus

# PyObjC imports for Apple's Virtualization Framework
import objc
from Foundation import NSObject, NSURL, NSError, NSOperationQueue
from Virtualization import (
    VZVirtualMachineConfiguration,
    VZVirtualMachine,
    VZEFIBootLoader,
    VZEFIVariableStore,
    VZVirtioBlockDeviceConfiguration,
    VZDiskImageStorageDeviceAttachment,
    VZVirtioNetworkDeviceConfiguration,
    VZNATNetworkDeviceAttachment,
    VZVirtioEntropyDeviceConfiguration,
    VZUSBKeyboardConfiguration,
    VZUSBScreenCoordinatePointingDeviceConfiguration,
    VZVirtioGraphicsDeviceConfiguration,
    VZVirtioGraphicsScanoutConfiguration,
    VZVirtioSoundDeviceConfiguration,
    VZVirtualMachineStateStopped,
    VZVirtualMachineStateRunning,
    VZVirtualMachineStatePaused,
    VZVirtualMachineStateError,
    VZVirtualMachineStateStarting,
    VZVirtualMachineStatePausing,
    VZVirtualMachineStateResuming,
    VZVirtualMachineStateStopping,
    VZGenericPlatformConfiguration,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VMDelegate(NSObject):
    """Delegate class to handle VM events"""
    
    def virtualMachine_didStopWithError_(self, vm: VZVirtualMachine, error: NSError | None) -> None:
        """Called when VM stops with an error"""
        if error:
            logger.error(f"VM stopped with error: {error}")
        else:
            logger.info("VM stopped successfully")
    
    def virtualMachine_didFailToStart_(self, vm: VZVirtualMachine, error: NSError) -> None:
        """Called when VM fails to start"""
        logger.error(f"VM failed to start: {error}")
    
    def guestDidStop_(self, vm: VZVirtualMachine) -> None:
        """Called when guest OS stops"""
        logger.info("Guest OS stopped")


class VMCreator:
    """Main VM Creator class using Apple's Virtualization Framework"""
    
    def __init__(self) -> None:
        self.delegate: VMDelegate = VMDelegate.new()
        self.vm: VZVirtualMachine | None = None
        self.config: VZVirtualMachineConfiguration | None = None
        
    def create_linux_vm(self, 
                       name: str,
                       cpu_count: int = 2,
                       memory_size_gb: int = 4,
                       disk_size_gb: int = 20,
                       iso_path: str | None = None) -> VMInfo:
        """
        Create a Linux VM configuration
        
        Args:
            name: VM name
            cpu_count: Number of CPU cores
            memory_size_gb: Memory in GB
            disk_size_gb: Disk size in GB
            iso_path: Path to Linux ISO file
            
        Returns:
            VMInfo model with VM configuration details
        """
        try:
            logger.info(f"Creating Linux VM: {name}")
            
            # Create VM configuration
            config = VZVirtualMachineConfiguration.new()
            
            # Set CPU and memory
            config.setCPUCount_(cpu_count)
            config.setMemorySize_(memory_size_gb * 1024 * 1024 * 1024)  # Convert GB to bytes
            
            # Create platform configuration for Linux
            platform_config = VZGenericPlatformConfiguration.new()
            config.setPlatform_(platform_config)
            
            # Create storage device (disk)
            vm_dir = Path.home() / "VMs" / name
            vm_dir.mkdir(parents=True, exist_ok=True)
            
            # Set up EFI boot loader for Linux
            bootloader = VZEFIBootLoader.new()
            
            # Create EFI variable store
            efi_store_path = vm_dir / "efi_vars.fd"
            if not efi_store_path.exists():
                # Create new EFI variable store
                efi_url = NSURL.fileURLWithPath_(str(efi_store_path))
                result = VZEFIVariableStore.alloc().initCreatingVariableStoreAtURL_options_error_(
                    efi_url, 0, None
                )
                efi_store = result[0]
                error = result[1]
                if error:
                    raise Exception(f"Failed to create EFI variable store: {error}")
            else:
                # Load existing EFI variable store
                efi_url = NSURL.fileURLWithPath_(str(efi_store_path))
                efi_store = VZEFIVariableStore.alloc().initWithURL_(efi_url)
            
            bootloader.setVariableStore_(efi_store)
            config.setBootLoader_(bootloader)
            
            disk_path = vm_dir / f"{name}.img"
            
            # Create disk image if it doesn't exist
            if not disk_path.exists():
                self._create_disk_image(str(disk_path), disk_size_gb)
            
            # Configure storage
            disk_url = NSURL.fileURLWithPath_(str(disk_path))
            disk_attachment = VZDiskImageStorageDeviceAttachment.alloc().initWithURL_readOnly_error_(
                disk_url, False, None
            )[0]
            
            storage_config = VZVirtioBlockDeviceConfiguration.alloc().initWithAttachment_(disk_attachment)
            config.setStorageDevices_([storage_config])
            
            # Configure network
            network_config = VZVirtioNetworkDeviceConfiguration.new()
            nat_attachment = VZNATNetworkDeviceAttachment.new()
            network_config.setAttachment_(nat_attachment)
            config.setNetworkDevices_([network_config])
            
            # Configure entropy (random number generator)
            entropy_config = VZVirtioEntropyDeviceConfiguration.new()
            config.setEntropyDevices_([entropy_config])
            
            # Configure input devices
            keyboard_config = VZUSBKeyboardConfiguration.new()
            pointing_config = VZUSBScreenCoordinatePointingDeviceConfiguration.new()
            config.setKeyboards_([keyboard_config])
            config.setPointingDevices_([pointing_config])
            
            # Configure graphics
            graphics_config = VZVirtioGraphicsDeviceConfiguration.new()
            scanout_config = VZVirtioGraphicsScanoutConfiguration.alloc().initWithWidthInPixels_heightInPixels_(800, 600)
            graphics_config.setScanouts_([scanout_config])
            config.setGraphicsDevices_([graphics_config])
            
            # Configure audio
            audio_config = VZVirtioSoundDeviceConfiguration.new()
            config.setAudioDevices_([audio_config])
            
            # Validate configuration
            result = config.validateWithError_(None)
            if not result[0]:
                error = result[1]
                raise Exception(f"VM configuration validation failed: {error}")
            
            self.config = config
            
            # Create VM instance
            self.vm = VZVirtualMachine.alloc().initWithConfiguration_queue_(
                config, NSOperationQueue.mainQueue()
            )
            self.vm.setDelegate_(self.delegate)
            
            logger.info(f"Linux VM '{name}' created successfully")
            
            return VMInfo(
                name=name,
                type=VMType.LINUX,
                cpu_count=cpu_count,
                memory_gb=memory_size_gb,
                disk_gb=disk_size_gb,
                disk_path=str(disk_path),
                vm_dir=str(vm_dir),
                status=VMStatus.CREATED
            )
            
        except Exception as e:
            logger.error(f"Failed to create Linux VM: {e}")
            raise
    
    def start_vm(self) -> bool:
        """Start the configured VM"""
        if not self.vm:
            logger.error("No VM configured")
            return False
            
        try:
            logger.info("Starting VM...")
            
            def completion_handler(error: NSError | None) -> None:
                if error:
                    logger.error(f"VM start failed: {error}")
                else:
                    logger.info("VM started successfully")
            
            self.vm.startWithCompletionHandler_(completion_handler)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start VM: {e}")
            return False
    
    def stop_vm(self) -> bool:
        """Stop the running VM"""
        if not self.vm:
            logger.error("No VM configured")
            return False
            
        try:
            logger.info("Stopping VM...")
            
            def completion_handler(error: NSError | None) -> None:
                if error:
                    logger.error(f"VM stop failed: {error}")
                else:
                    logger.info("VM stopped successfully")
            
            self.vm.stopWithCompletionHandler_(completion_handler)
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop VM: {e}")
            return False
    
    def get_vm_state(self) -> VMStatus:
        """Get current VM state"""
        if not self.vm:
            return VMStatus.NOT_CONFIGURED
            
        state = self.vm.state()
        state_map: dict[int, VMStatus] = {
            VZVirtualMachineStateStopped: VMStatus.STOPPED,
            VZVirtualMachineStateRunning: VMStatus.RUNNING,
            VZVirtualMachineStatePaused: VMStatus.PAUSED,
            VZVirtualMachineStateError: VMStatus.ERROR,
            VZVirtualMachineStateStarting: VMStatus.STARTING,
            VZVirtualMachineStatePausing: VMStatus.PAUSING,
            VZVirtualMachineStateResuming: VMStatus.RESUMING,
            VZVirtualMachineStateStopping: VMStatus.STOPPING,
        }
        
        return state_map.get(state, VMStatus.UNKNOWN)
    
    def _create_disk_image(self, path: str, size_gb: int) -> None:
        """Create a disk image file"""
        logger.info(f"Creating disk image: {path} ({size_gb}GB)")
        
        # Create empty disk image using dd
        
        try:
            subprocess.run([
                "dd", "if=/dev/zero", f"of={path}", 
                "bs=1m", f"count={size_gb * 1024}"
            ], check=True, capture_output=True)
            logger.info(f"Disk image created: {path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create disk image: {e}")
            raise


def list_vms() -> list[VMListItem]:
    """List all VMs in the default VM directory"""
    vm_dir: Path = Path.home() / "VMs"
    if not vm_dir.exists():
        return []
    
    vms: list[VMListItem] = []
    for vm_path in vm_dir.iterdir():
        if vm_path.is_dir():
            vms.append(VMListItem(
                name=vm_path.name,
                path=str(vm_path),
                exists=True
            ))
    
    return vms


def delete_vm(vm_name: str) -> bool:
    """Delete a VM and all its files"""
    try:
        vm_dir: Path = Path.home() / "VMs" / vm_name
        
        if not vm_dir.exists():
            logger.warning(f"VM directory does not exist: {vm_dir}")
            return False
        
        logger.info(f"Deleting VM: {vm_name}")
        logger.info(f"VM directory: {vm_dir}")
        
        # Delete all files in the VM directory
        import shutil
        shutil.rmtree(vm_dir)
        
        logger.info(f"VM '{vm_name}' deleted successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete VM '{vm_name}': {e}")
        return False


def check_virtualization_support() -> VirtualizationSupport:
    """Check if the system supports virtualization"""
    try:
        # Try to import Virtualization framework
        import Virtualization  # noqa: F401
        
        # Check if we can create a basic configuration
        VZVirtualMachineConfiguration.alloc().init()
        
        return VirtualizationSupport(
            supported=True,
            framework_available=True,
            pyobjc_version=objc.__version__,
            message="Virtualization framework is available"
        )
    except ImportError as e:
        return VirtualizationSupport(
            supported=False,
            framework_available=False,
            error=str(e),
            message="Virtualization framework not available"
        )
    except Exception as e:
        return VirtualizationSupport(
            supported=False,
            framework_available=True,
            error=str(e),
            message="Error checking virtualization support"
        )
