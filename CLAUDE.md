# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**macosprox** is a VM Creator MVP that uses Apple's Virtualization Framework to create and manage Linux virtual machines on macOS. The project leverages PyObjC bindings to interact with Apple's native Virtualization Framework for high-performance VM creation and management with SSH access capabilities.

The project uses uv with ruff and mypy
Before every commit make sure ruff and mypy pass

## Current Status

### ✅ **Completed Features:**
- **CLI Interface** - Complete command-line interface with Rich formatting
- **VM Creation** - Can create Linux VMs with configurable CPU, memory, and disk
- **VM Management** - Start, stop, list, status, and delete operations  
- **ISO Mounting** - Support for mounting Linux installation ISOs
- **SSH Access** - Automated SSH key generation and cloud-init configuration
- **Auto-Installation** - Cloud-init ISO creation for unattended Linux setup
- **Storage** - Creates raw disk images and EFI variable stores
- **Networking** - VirtIO network with NAT attachment and predictable MAC addresses
- **Graphics & Audio** - VirtIO graphics and sound devices
- **Input Devices** - USB keyboard and pointing device support
- **Validation** - Virtualization support checking

### 🎯 **Ready for Linux Installation:**
The infrastructure is complete and ready to boot Linux VMs with SSH access. To test:

1. **Download a Linux ISO** (Ubuntu Server recommended)
2. **Create VM with ISO and auto-install**:
   ```bash
   uv run macosprox create --name ubuntu-vm --cpu 4 --memory 4 --disk 20 \
     --iso ~/Downloads/ubuntu-22.04-server.iso --auto-install
   ```
3. **Start the VM**: `uv run macosprox start ubuntu-vm`
4. **SSH into the VM**: `uv run macosprox ssh ubuntu-vm`

## Key Architecture

### Core Components

- **cli.py**: Click-based command-line interface with Rich formatting for user interaction
- **vm_creator.py**: Core VM creation and management logic using Apple's Virtualization Framework
- **main.py**: Entry point that launches the CLI

### VM Architecture

The VM creation process follows this pattern:
1. **Configuration**: Creates `VZVirtualMachineConfiguration` with CPU, memory, storage, and device settings
2. **Platform**: Uses `VZGenericPlatformConfiguration` for Linux VMs
3. **Boot**: Configures EFI boot loader with variable store for UEFI support
4. **Storage**: Creates VirtIO block devices with disk image attachments
   - Main disk: Raw disk image for VM storage
   - ISO mounting: For Linux installation media
   - Cloud-init ISO: For automated setup with SSH access
5. **Networking**: Sets up VirtIO network devices with NAT attachment and predictable MAC addresses
6. **Console**: VirtIO console device with file logging for debugging
7. **Devices**: Configures entropy, keyboard, pointing, graphics, and audio devices
8. **Validation**: Validates configuration before VM instantiation

### SSH and Remote Access

- **Automatic SSH Setup**: Use `--auto-install` flag to create cloud-init configuration
- **SSH Key Management**: Generates SSH key pairs automatically or uses provided keys
- **IP Discovery**: Uses ARP table scanning to find VM IP addresses
- **Predictable MACs**: Generates consistent MAC addresses based on VM name for easier networking

### File Structure

- VMs are stored in `~/VMs/{vm_name}/` directory
- Each VM has an EFI variable store file (`efi_vars.fd`)
- Disk images are stored as `{vm_name}.img` files
- Console logs are saved as `{vm_name}_console.log` (when implemented)
- SSH keys are generated in `ssh/` subdirectory (`vm_key`, `vm_key.pub`)
- Cloud-init configuration stored in `cloud-init/` subdirectory (`user-data`, `meta-data`)
- Auto-generated cloud-init ISO as `{vm_name}-cloud-init.iso`
- Uses `dd` command to create raw disk images
- Uses `hdiutil` to create cloud-init ISO images

### Example VM Directory Structure:
```
~/VMs/ubuntu-vm/
├── efi_vars.fd                    # EFI variable store
├── ubuntu-vm.img                  # Main disk image  
├── ubuntu-vm-cloud-init.iso       # Auto-configuration ISO
├── ssh/
│   ├── vm_key                     # Private SSH key (auto-generated)
│   └── vm_key.pub                 # Public SSH key (auto-generated)
└── cloud-init/
    ├── user-data                  # Cloud-init user configuration
    └── meta-data                  # VM metadata
```

## Development Commands

### Installation and Setup
```bash
# Install dependencies using uv (modern Python package manager)
uv sync

# Install in development mode
uv pip install -e .

# To run checks
uv run ruff check  
uv run mypy src/

# To fix automatically 
uv run ruff --fix
```

### Running the CLI
```bash
# Run the CLI directly
uv run macosprox --help
```

### Key CLI Commands
```bash
# Check virtualization support
uv run macosprox check

# Create a new VM (basic)
uv run macosprox create --name test-vm --cpu 2 --memory 4 --disk 20

# Create a VM with ISO mounting
uv run macosprox create --name ubuntu-vm --cpu 4 --memory 8 --disk 40 --iso /path/to/ubuntu.iso

# Create a VM with auto-installation and SSH setup
uv run macosprox create --name auto-vm --cpu 2 --memory 4 --disk 20 --auto-install --ssh-key ~/.ssh/id_rsa.pub

# List VMs
uv run macosprox list

# Start/stop VMs
uv run macosprox start vm-name
uv run macosprox stop vm-name

# Check VM status
uv run macosprox status vm-name

# SSH into a running VM
uv run macosprox ssh vm-name
uv run macosprox ssh vm-name --user ubuntu --key ~/.ssh/my_key

# Delete VM
uv run macosprox delete vm-name
```

## Dependencies

- **PyObjC**: Provides Python bindings to Apple's Objective-C frameworks
- **Click**: Command-line interface framework
- **Rich**: Terminal formatting and display library
- **Apple Virtualization Framework**: Native macOS virtualization (requires macOS 11+ and Apple Silicon or Intel with virtualization support)

## Platform Requirements

- macOS 11 (Big Sur) or later
- Python 3.13+
- Apple Silicon or Intel Mac with virtualization support
- Appropriate entitlements for Virtualization Framework access

## Important Notes

- The VMDelegate class handles VM lifecycle events and logging
- VM state management uses Apple's native state constants
- Disk images are created as raw files using `dd` command
- EFI variable stores are required for UEFI boot support
- All VM operations are asynchronous with completion handlers
- Cloud-init provides automated Linux setup with SSH access
- SSH keys are automatically generated per VM for security
- Predictable MAC addresses enable consistent IP assignment
- NAT networking provides internet access while maintaining isolation

## Troubleshooting

### Common Issues:
1. **"Virtualization not supported"** - Requires macOS 11+ and Apple Silicon/Intel with virtualization
2. **VM won't start** - Check that an ISO is mounted or disk has a bootable OS
3. **Can't SSH to VM** - VM needs to be running and have completed Linux installation
4. **IP address not found** - Wait for VM to fully boot and get DHCP lease

### Debug Commands:
```bash
# Check VM state
uv run macosprox status vm-name

# View VM MAC address (check logs)
uv run macosprox start vm-name

# Check if VM has IP address
arp -a | grep "52:54:00"
```