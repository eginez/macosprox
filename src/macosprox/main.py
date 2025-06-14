"""Main entry point for macOS Proxmox VM Creator"""

from __future__ import annotations

from .cli import cli

def main() -> None:
    """Main entry point"""
    cli()

if __name__ == "__main__":
    main()
