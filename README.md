# macosprox

A VM Creator MVP that uses Apple's Virtualization Framework to create and manage Linux virtual machines on macOS with SSH access capabilities.

## Features

- **VM Creation & Management** - Create, start, stop, list, and delete Linux VMs
- **SSH Access** - Automated SSH key generation and remote access
- **Auto-Installation** - Cloud-init support for unattended Linux setup
- **ISO Mounting** - Support for Linux installation media
- **High Performance** - Uses Apple's native Virtualization Framework via PyObjC

## Requirements

- macOS 11 (Big Sur) or later
- Python 3.13+
- Apple Silicon or Intel Mac with virtualization support

## Installation

```bash
# Install dependencies using uv
uv sync

# Install in development mode
uv pip install -e .
```

## Quick Start

1. **Check virtualization support**:
   ```bash
   uv run macosprox check
   ```

2. **Create and start a VM with auto-installation**:
   ```bash
   # Download a Linux ISO first
   uv run macosprox create --name ubuntu-vm --cpu 4 --memory 4 --disk 20 \
     --iso ~/Downloads/ubuntu-22.04-server.iso --auto-install
   uv run macosprox start ubuntu-vm
   ```

3. **SSH into the VM**:
   ```bash
   uv run macosprox ssh ubuntu-vm
   ```

## Usage

### Basic Commands

```bash
# List all VMs
uv run macosprox list

# Check VM status
uv run macosprox status vm-name

# Start/stop VMs
uv run macosprox start vm-name
uv run macosprox stop vm-name

# Delete VM
uv run macosprox delete vm-name
```

### VM Creation Options

```bash
# Basic VM
uv run macosprox create --name test-vm --cpu 2 --memory 4 --disk 20

# VM with ISO mounting
uv run macosprox create --name ubuntu-vm --cpu 4 --memory 8 --disk 40 \
  --iso /path/to/ubuntu.iso

# VM with custom SSH key
uv run macosprox create --name auto-vm --cpu 2 --memory 4 --disk 20 \
  --auto-install --ssh-key ~/.ssh/id_rsa.pub
```

### SSH Access

```bash
# SSH with auto-generated keys
uv run macosprox ssh vm-name

# SSH with custom user and key
uv run macosprox ssh vm-name --user ubuntu --key ~/.ssh/my_key
```

## Architecture

VMs are stored in `~/VMs/{vm_name}/` with the following structure:

```
~/VMs/ubuntu-vm/
├── efi_vars.fd                    # EFI variable store
├── ubuntu-vm.img                  # Main disk image  
├── ubuntu-vm-cloud-init.iso       # Auto-configuration ISO
├── ssh/
│   ├── vm_key                     # Private SSH key
│   └── vm_key.pub                 # Public SSH key
└── cloud-init/
    ├── user-data                  # Cloud-init configuration
    └── meta-data                  # VM metadata
```

## Development

```bash
# Run linting and type checking
uv run ruff check
uv run mypy src/

# Auto-fix issues
uv run ruff --fix
```

## Dependencies

- **PyObjC** - Python bindings to Apple's frameworks
- **Click** - Command-line interface framework  
- **Rich** - Terminal formatting and display

## License

[Add your license here]