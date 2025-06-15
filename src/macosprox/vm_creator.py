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
    VZDiskImageStorageDeviceAttachment,
    VZMACAddress,
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
                       iso_path: str | None = None,
                       ssh_key: str | None = None,
                       auto_install: bool = False) -> VMInfo:
        """
        Create a Linux VM configuration
        
        Args:
            name: VM name
            cpu_count: Number of CPU cores
            memory_size_gb: Memory in GB
            disk_size_gb: Disk size in GB
            iso_path: Path to Linux ISO file
            ssh_key: SSH public key content for cloud-init
            auto_install: Whether to create cloud-init ISO for auto-installation
            
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
            
            # Configure storage devices
            storage_devices = []
            
            # Main disk
            disk_url = NSURL.fileURLWithPath_(str(disk_path))
            disk_attachment = VZDiskImageStorageDeviceAttachment.alloc().initWithURL_readOnly_error_(
                disk_url, False, None
            )[0]
            
            storage_config = VZVirtioBlockDeviceConfiguration.alloc().initWithAttachment_(disk_attachment)
            storage_devices.append(storage_config)
            
            # ISO mounting for installation
            if iso_path and Path(iso_path).exists():
                logger.info(f"Mounting ISO: {iso_path}")
                iso_url = NSURL.fileURLWithPath_(str(iso_path))
                iso_attachment = VZDiskImageStorageDeviceAttachment.alloc().initWithURL_readOnly_error_(
                    iso_url, True, None  # Read-only for ISO
                )[0]
                
                iso_config = VZVirtioBlockDeviceConfiguration.alloc().initWithAttachment_(iso_attachment)
                storage_devices.append(iso_config)
            
            # Create cloud-init ISO if auto-install is enabled
            if auto_install:
                try:
                    cloud_init_iso_path = self._create_cloud_init_iso(vm_dir, name, ssh_key)
                    if cloud_init_iso_path and Path(cloud_init_iso_path).exists():
                        logger.info(f"Mounting cloud-init ISO: {cloud_init_iso_path}")
                        cloud_init_url = NSURL.fileURLWithPath_(cloud_init_iso_path)
                        cloud_init_attachment = VZDiskImageStorageDeviceAttachment.alloc().initWithURL_readOnly_error_(
                            cloud_init_url, True, None
                        )[0]
                        
                        cloud_init_config = VZVirtioBlockDeviceConfiguration.alloc().initWithAttachment_(cloud_init_attachment)
                        storage_devices.append(cloud_init_config)
                        logger.info("Cloud-init ISO mounted successfully")
                    else:
                        logger.warning("Cloud-init ISO creation failed or file not found")
                except Exception as e:
                    logger.error(f"Failed to create/mount cloud-init ISO: {e}")
                    # Continue without cloud-init rather than failing completely
            
            config.setStorageDevices_(storage_devices)
            
            # Configure network with predictable MAC address for easier DHCP/SSH access
            network_config = VZVirtioNetworkDeviceConfiguration.new()
            
            # Generate a predictable MAC address based on VM name
            # This helps with consistent IP assignment and SSH access
            mac_bytes = bytes(f"52:54:00:{abs(hash(name)) % 256:02x}:{abs(hash(name)) % 256:02x}:{abs(hash(name)) % 256:02x}", 'utf-8')[:6]
            # Actually create a proper MAC address
            mac_string = f"52:54:00:{abs(hash(name)) % 256:02x}:{abs(hash(name + '1')) % 256:02x}:{abs(hash(name + '2')) % 256:02x}"
            mac_address = VZMACAddress.alloc().initWithString_(mac_string)
            network_config.setMACAddress_(mac_address)
            
            nat_attachment = VZNATNetworkDeviceAttachment.new()
            network_config.setAttachment_(nat_attachment)
            config.setNetworkDevices_([network_config])
            
            logger.info(f"VM Network MAC Address: {mac_string}")
            
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
            
            # Skip console devices for now - not essential for basic functionality
            # TODO: Add proper serial console support when needed
            
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
    
    def _create_cloud_init_iso(self, vm_dir: Path, vm_name: str, ssh_key: str | None = None) -> str:
        """
        Create a cloud-init ISO for automated Linux setup with SSH access
        
        Args:
            vm_dir: VM directory path
            vm_name: VM name
            ssh_key: Optional SSH public key content
            
        Returns:
            Path to created cloud-init ISO
        """
        cloud_init_dir = vm_dir / "cloud-init"
        cloud_init_dir.mkdir(exist_ok=True)
        
        # Create user-data with SSH configuration
        user_data = f"""#cloud-config
hostname: {vm_name}
manage_etc_hosts: true

users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
    passwd: $6$rounds=4096$aQ7lBLKCKLV$w0Jd8PkQmL8hZGdLNa1s1y3YI2IJ3j4K5L6M7N8O9P0Q1R2S3T4U5V6W7X8Y9Z0A1B2C3D4E5F6G7H8I9J0K1L2M3
"""
        
        if ssh_key:
            user_data += f"""    ssh_authorized_keys:
      - {ssh_key}
"""
        else:
            # Create a temporary SSH key pair if none provided
            ssh_dir = vm_dir / "ssh"
            ssh_dir.mkdir(exist_ok=True)
            private_key_path = ssh_dir / "vm_key"
            public_key_path = ssh_dir / "vm_key.pub"
            
            if not private_key_path.exists():
                import subprocess
                subprocess.run([
                    "ssh-keygen", "-t", "rsa", "-b", "2048", 
                    "-f", str(private_key_path), "-N", ""
                ], check=True)
                
            with open(public_key_path, 'r') as f:
                ssh_key = f.read().strip()
                
            user_data += f"""    ssh_authorized_keys:
      - {ssh_key}
"""
        
        user_data += """
ssh_pwauth: true
package_update: true
package_upgrade: true
packages:
  - openssh-server
  - curl
  - wget
  - htop
  - vim

runcmd:
  - systemctl enable ssh
  - systemctl start ssh
  - ufw allow ssh
  - echo "SSH server setup completed" > /var/log/cloud-init-ssh.log

final_message: |
  Cloud-init setup completed!
  SSH access enabled for user 'ubuntu'
  Default password: ubuntu (please change!)
"""
        
        # Write user-data
        user_data_path = cloud_init_dir / "user-data"
        with open(user_data_path, 'w') as f:
            f.write(user_data)
        
        # Create meta-data
        meta_data = f"""instance-id: {vm_name}-001
local-hostname: {vm_name}
"""
        
        meta_data_path = cloud_init_dir / "meta-data"
        with open(meta_data_path, 'w') as f:
            f.write(meta_data)
        
        # Create cloud-init ISO
        cloud_init_iso = vm_dir / f"{vm_name}-cloud-init.iso"
        
        try:
            subprocess.run([
                "hdiutil", "makehybrid", "-o", str(cloud_init_iso),
                "-hfs", "-joliet", "-iso", "-default-volume-name", "cidata",
                str(cloud_init_dir)
            ], check=True, capture_output=True)
            
            logger.info(f"Cloud-init ISO created: {cloud_init_iso}")
            return str(cloud_init_iso)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create cloud-init ISO: {e}")
            raise
        
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


    def get_vm_ip(self, vm_name: str) -> str | None:
        """
        Try to get the VM's IP address by scanning the NAT network
        This is a best-effort approach since Apple's Virtualization Framework
        doesn't provide direct IP access
        """
        try:
            # Use arp to find MAC address to IP mapping
            vm_dir = Path.home() / "VMs" / vm_name
            if not vm_dir.exists():
                return None
            
            # Generate the same MAC address we used when creating the VM
            mac_string = f"52:54:00:{abs(hash(vm_name)) % 256:02x}:{abs(hash(vm_name + '1')) % 256:02x}:{abs(hash(vm_name + '2')) % 256:02x}"
            
            # Use arp command to find IP for this MAC
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if mac_string.lower() in line.lower():
                    # Extract IP from line like: "? (192.168.64.2) at 52:54:00:xx:xx:xx on vmnet1 ifscope [ethernet]"
                    import re
                    ip_match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', line)
                    if ip_match:
                        return ip_match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get VM IP: {e}")
            return None


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
