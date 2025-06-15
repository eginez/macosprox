# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**macosprox** is a VM Creator MVP that uses Apple's Virtualization Framework to create and manage Linux virtual machines on macOS. The project leverages PyObjC bindings to interact with Apple's native Virtualization Framework for high-performance VM creation and management.

The project uses uv with ruff amd mypy
 Before every commit make sure ruff and mypy pass

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
5. **Networking**: Sets up VirtIO network devices with NAT attachment
6. **Devices**: Configures entropy, keyboard, pointing, graphics, and audio devices
7. **Validation**: Validates configuration before VM instantiation

### File Structure

- VMs are stored in `~/VMs/{vm_name}/` directory
- Each VM has an EFI variable store file (`efi_vars.fd`)
- Disk images are stored as `{vm_name}.img` files
- Uses `dd` command to create raw disk images

## Development Commands

### Installation and Setup
```bash
# Install dependencies using uv (modern Python package manager)
uv sync

# Install in development mode
pip install -e .
```

### Running the CLI
```bash
# Run the CLI directly
python -m macosprox.main

# Or if installed
macosprox
```

### Key CLI Commands
```bash
# Check virtualization support
macosprox check

# Create a new VM
macosprox create --name test-vm --cpu 2 --memory 4 --disk 20

# List VMs
macosprox list

# Start/stop VMs
macosprox start vm-name
macosprox stop vm-name

# Check VM status
macosprox status vm-name

# Delete VM
macosprox delete vm-name
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