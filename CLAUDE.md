# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**macosprox** is a VM Creator MVP that uses Apple's Virtualization Framework to create and manage Linux virtual machines on macOS. The project provides both Python and Swift implementations for VM creation and management with SSH access capabilities.

## Implementation Status

### ✅ **Swift Implementation (Primary)**
- **Location**: `src/swift/`
- **Status**: Complete and production-ready
- **Performance**: Native Swift with Apple Virtualization Framework
- **Usage**: Primary implementation for web application backend

### 🔄 **Python Implementation (Legacy)**
- **Location**: `src/python/` 
- **Status**: Legacy implementation (PyObjC-based)
- **Usage**: Reference implementation, uses uv with ruff and mypy

**Build Requirements:**
- Swift implementation: `make` or `swift build` with code signing
- Python implementation: Before commits ensure `ruff check` and `mypy src/` pass

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
The infrastructure is complete and ready to boot Linux VMs with SSH access.

#### **Swift Implementation (Recommended):**
```bash
# Build and sign
make

# Check virtualization support
src/swift/.build/debug/macosprox check

# Create VM with ISO and auto-install
src/swift/.build/debug/macosprox create --name ubuntu-vm --cpu 4 --memory 4 --disk 20 \
  --iso ~/Downloads/ubuntu-22.04-server.iso --auto-install

# Start the VM
src/swift/.build/debug/macosprox start ubuntu-vm

# SSH into the VM
src/swift/.build/debug/macosprox ssh ubuntu-vm
```

#### **Python Implementation (Legacy):**
```bash
# Test with Python implementation
uv run macosprox create --name ubuntu-vm --cpu 4 --memory 4 --disk 20 \
  --iso ~/Downloads/ubuntu-22.04-server.iso --auto-install
uv run macosprox start ubuntu-vm
uv run macosprox ssh ubuntu-vm
```

## Key Architecture

### Core Components

#### **Swift Implementation:**
- **main.swift**: Complete CLI interface with argument parsing and command execution
- **VMCreator.swift**: Core VM creation and management using Apple's Virtualization Framework
- **Package.swift**: Swift package configuration with entitlements
- **Resources/entitlements.plist**: Required entitlements for virtualization framework access

#### **Python Implementation (Legacy):**
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

### Swift Implementation (Primary)

#### **Build and Setup:**
```bash
# Build and sign with entitlements (recommended)
make

# Development build (faster, no signing)
make dev

# Release build
make release

# Clean build artifacts
make clean

# Run tests
make test

# Show help
make help
```

#### **Manual Build Process:**
```bash
# Build only (from project root)
cd src/swift && swift build

# Build and sign manually (from project root)
cd src/swift && swift build
cd src/swift && codesign --force --sign - --entitlements Resources/entitlements.plist .build/debug/macosprox
```

#### **Key CLI Commands:**
```bash
# All commands use the built executable (paths from project root)

# Check virtualization support
src/swift/.build/debug/macosprox check

# Create a new VM (basic)
src/swift/.build/debug/macosprox create --name test-vm --cpu 2 --memory 4 --disk 20

# Create a VM with ISO mounting
src/swift/.build/debug/macosprox create --name ubuntu-vm --cpu 4 --memory 8 --disk 40 --iso /path/to/ubuntu.iso

# Create a VM with auto-installation and SSH setup
src/swift/.build/debug/macosprox create --name auto-vm --cpu 2 --memory 4 --disk 20 --auto-install --ssh-key ~/.ssh/id_rsa.pub

# List VMs
src/swift/.build/debug/macosprox list

# Start/stop VMs
src/swift/.build/debug/macosprox start vm-name
src/swift/.build/debug/macosprox stop vm-name

# Check VM status
src/swift/.build/debug/macosprox status vm-name

# SSH into a running VM
src/swift/.build/debug/macosprox ssh vm-name
src/swift/.build/debug/macosprox ssh vm-name --user ubuntu --key ~/.ssh/my_key

# Delete VM
src/swift/.build/debug/macosprox delete vm-name
```

### Python Implementation (Legacy)

#### **Installation and Setup:**
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

#### **Running the CLI:**
```bash
# Run the CLI directly
uv run macosprox --help

# Example commands (same as Swift but with uv run prefix)
uv run macosprox check
uv run macosprox create --name test-vm --cpu 2 --memory 4 --disk 20
uv run macosprox list
```

## Dependencies

### Swift Implementation:
- **Apple Virtualization Framework**: Native macOS virtualization framework
- **Foundation**: Core macOS system framework
- **CryptoKit**: For cryptographic operations
- **Swift 5.9+**: Modern Swift language and runtime

### Python Implementation (Legacy):
- **PyObjC**: Provides Python bindings to Apple's Objective-C frameworks
- **Click**: Command-line interface framework
- **Rich**: Terminal formatting and display library
- **Python 3.13+** with uv package manager

## Platform Requirements

- **macOS 14+ (Sonoma)** - Required for Swift implementation
- **macOS 11+ (Big Sur)** - Minimum for Python implementation
- **Apple Silicon or Intel Mac** with virtualization support
- **Appropriate entitlements** for Virtualization Framework access (automatically configured in Swift build)
- **Xcode Command Line Tools** for Swift compilation and code signing

## Important Notes

### Swift Implementation:
- **Native Performance**: Direct Swift bindings to Apple's Virtualization Framework
- **Code Signing**: Automatically signs executable with required entitlements
- **Async/Await**: Modern Swift concurrency for VM operations
- **Memory Management**: Automatic memory management with ARC
- **Type Safety**: Compile-time type checking for reliability

### General VM Behavior:
- VM state management uses Apple's native state constants
- Disk images are created as raw files using `dd` command
- EFI variable stores are required for UEFI boot support
- All VM operations are asynchronous with completion handlers
- Cloud-init provides automated Linux setup with SSH access
- SSH keys are automatically generated per VM for security
- Predictable MAC addresses enable consistent IP assignment
- NAT networking provides internet access while maintaining isolation

## Troubleshooting

### Swift Implementation Issues:
1. **"Build failed"** - Ensure Xcode Command Line Tools are installed: `xcode-select --install`
2. **"Code signing failed"** - Run `make` instead of `swift build` for automatic signing
3. **"Virtualization entitlement error"** - Ensure executable is properly signed with entitlements

### Common VM Issues:
1. **"Virtualization not supported"** - Run `./.build/debug/macosprox check` to verify
2. **VM won't start** - Check that an ISO is mounted or disk has a bootable OS
3. **Can't SSH to VM** - VM needs to be running and have completed Linux installation
4. **IP address not found** - Wait for VM to fully boot and get DHCP lease

### Debug Commands:

#### Swift Implementation:
```bash
# Check VM state
src/swift/.build/debug/macosprox status vm-name

# Check virtualization support
src/swift/.build/debug/macosprox check

# View VM MAC address and attempt IP discovery
src/swift/.build/debug/macosprox start vm-name

# Check if VM has IP address
arp -a | grep "52:54:00"
```

#### Python Implementation (Legacy):
```bash
# Check VM state
uv run macosprox status vm-name

# View VM MAC address (check logs)
uv run macosprox start vm-name

# Check if VM has IP address
arp -a | grep "52:54:00"
```