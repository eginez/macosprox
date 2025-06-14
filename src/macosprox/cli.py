"""Command Line Interface for macOS Proxmox VM Creator"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import sys
from pathlib import Path
from typing import Any

from .vm_creator import VMCreator, list_vms, check_virtualization_support

console: Console = Console()


@click.group()
@click.version_option()
def cli() -> None:
    """macOS Proxmox - VM Creator MVP using Apple's Virtualization Framework"""
    pass


@cli.command()
def check() -> None:
    """Check if virtualization is supported on this system"""
    console.print("\n[bold blue]Checking Virtualization Support...[/bold blue]")
    
    support_info: dict[str, Any] = check_virtualization_support()
    
    if support_info["supported"]:
        console.print(Panel(
            f"✅ {support_info['message']}\nPyObjC Version: {support_info.get('pyobjc_version', 'Unknown')}",
            title="[green]Virtualization Supported[/green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"❌ {support_info['message']}\nError: {support_info.get('error', 'Unknown error')}",
            title="[red]Virtualization Not Supported[/red]",
            border_style="red"
        ))
        sys.exit(1)


@cli.command()
@click.option("--name", "-n", required=True, help="VM name")
@click.option("--cpu", "-c", default=2, help="Number of CPU cores (default: 2)")
@click.option("--memory", "-m", default=4, help="Memory in GB (default: 4)")
@click.option("--disk", "-d", default=20, help="Disk size in GB (default: 20)")
@click.option("--iso", "-i", help="Path to Linux ISO file (optional)")
def create(name: str, cpu: int, memory: int, disk: int, iso: str | None) -> None:
    """Create a new Linux VM"""
    
    console.print(f"\n[bold blue]Creating VM: {name}[/bold blue]")
    
    # Check virtualization support first
    support_info: dict[str, Any] = check_virtualization_support()
    if not support_info["supported"]:
        console.print(f"[red]Error:[/red] {support_info['message']}")
        sys.exit(1)
    
    try:
        creator: VMCreator = VMCreator()
        
        with console.status("[bold green]Creating VM configuration..."):
            vm_info: dict[str, Any] = creator.create_linux_vm(
                name=name,
                cpu_count=cpu,
                memory_size_gb=memory,
                disk_size_gb=disk,
                iso_path=iso
            )
        
        # Display VM information
        table: Table = Table(title=f"VM Created: {name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Name", vm_info["name"])
        table.add_row("Type", vm_info["type"].title())
        table.add_row("CPU Cores", str(vm_info["cpu_count"]))
        table.add_row("Memory", f"{vm_info['memory_gb']} GB")
        table.add_row("Disk Size", f"{vm_info['disk_gb']} GB")
        table.add_row("Disk Path", vm_info["disk_path"])
        table.add_row("VM Directory", vm_info["vm_dir"])
        table.add_row("Status", vm_info["status"].title())
        
        console.print(table)
        
        console.print(f"\n[green]✅ VM '{name}' created successfully![/green]")
        console.print(f"[yellow]💡 Tip:[/yellow] Use 'macosprox start {name}' to start the VM")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to create VM:[/red] {str(e)}")
        sys.exit(1)


@cli.command()
def list() -> None:
    """List all VMs"""
    
    console.print("\n[bold blue]Listing VMs...[/bold blue]")
    
    vms: list[dict[str, Any]] = list_vms()
    
    if not vms:
        console.print("[yellow]No VMs found.[/yellow]")
        console.print("[dim]Create your first VM with: macosprox create --name my-vm[/dim]")
        return
    
    table: Table = Table(title="Virtual Machines")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Status", style="green")
    
    for vm in vms:
        table.add_row(
            vm["name"],
            vm["path"],
            "Available" if vm["exists"] else "Missing"
        )
    
    console.print(table)


@cli.command()
@click.argument("vm_name")
def start(vm_name):
    """Start a VM"""
    
    console.print(f"\n[bold blue]Starting VM: {vm_name}[/bold blue]")
    
    # Check if VM exists
    vms = list_vms()
    vm_exists = any(vm["name"] == vm_name for vm in vms)
    
    if not vm_exists:
        console.print(f"[red]❌ VM '{vm_name}' not found.[/red]")
        console.print("[dim]Use 'macosprox list' to see available VMs[/dim]")
        sys.exit(1)
    
    try:
        creator = VMCreator()
        
        # First create/load the VM configuration
        with console.status("[bold green]Loading VM configuration..."):
            vm_info = creator.create_linux_vm(name=vm_name)
        
        # Start the VM
        with console.status("[bold green]Starting VM..."):
            success = creator.start_vm()
        
        if success:
            console.print(f"[green]✅ VM '{vm_name}' is starting...[/green]")
            console.print("[yellow]💡 Note:[/yellow] VM will continue running in the background")
            
            # Show current state
            state = creator.get_vm_state()
            console.print(f"[dim]Current state: {state}[/dim]")
        else:
            console.print(f"[red]❌ Failed to start VM '{vm_name}'[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error starting VM:[/red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("vm_name")
def stop(vm_name: str) -> None:
    """Stop a running VM"""
    
    console.print(f"\n[bold blue]Stopping VM: {vm_name}[/bold blue]")
    
    try:
        creator: VMCreator = VMCreator()
        
        # Load VM configuration
        with console.status("[bold green]Loading VM configuration..."):
            vm_info: dict[str, Any] = creator.create_linux_vm(name=vm_name)
        
        # Check current state
        state: str = creator.get_vm_state()
        if state not in ["running", "starting"]:
            console.print(f"[yellow]⚠️  VM '{vm_name}' is not running (state: {state})[/yellow]")
            return
        
        # Stop the VM
        with console.status("[bold green]Stopping VM..."):
            success: bool = creator.stop_vm()
        
        if success:
            console.print(f"[green]✅ VM '{vm_name}' is stopping...[/green]")
        else:
            console.print(f"[red]❌ Failed to stop VM '{vm_name}'[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error stopping VM:[/red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("vm_name")
def status(vm_name: str) -> None:
    """Show VM status"""
    
    console.print(f"\n[bold blue]VM Status: {vm_name}[/bold blue]")
    
    # Check if VM exists
    vms: list[dict[str, Any]] = list_vms()
    vm_exists: bool = any(vm["name"] == vm_name for vm in vms)
    
    if not vm_exists:
        console.print(f"[red]❌ VM '{vm_name}' not found.[/red]")
        sys.exit(1)
    
    try:
        creator: VMCreator = VMCreator()
        
        # Load VM configuration
        vm_info: dict[str, Any] = creator.create_linux_vm(name=vm_name)
        
        # Get current state
        state: str = creator.get_vm_state()
        
        # Create status display
        status_colors: dict[str, str] = {
            "running": "green",
            "stopped": "red", 
            "starting": "yellow",
            "stopping": "yellow",
            "paused": "blue",
            "error": "red",
            "not_configured": "dim"
        }
        
        color: str = status_colors.get(state, "white")
        
        console.print(Panel(
            f"VM: [bold]{vm_name}[/bold]\n"
            f"State: [{color}]{state.title()}[/{color}]\n"
            f"Path: [dim]{vm_info['vm_dir']}[/dim]",
            title="VM Status",
            border_style=color
        ))
        
    except Exception as e:
        console.print(f"[red]❌ Error getting VM status:[/red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("vm_name")
@click.option("--force", "-f", is_flag=True, help="Force deletion without confirmation")
def delete(vm_name: str, force: bool) -> None:
    """Delete a VM and all its files"""
    
    console.print(f"\n[bold red]Deleting VM: {vm_name}[/bold red]")
    
    # Check if VM exists
    vms: list[dict[str, Any]] = list_vms()
    vm_exists: bool = any(vm["name"] == vm_name for vm in vms)
    
    if not vm_exists:
        console.print(f"[red]❌ VM '{vm_name}' not found.[/red]")
        console.print("[dim]Use 'macosprox list' to see available VMs[/dim]")
        sys.exit(1)
    
    # Get VM directory path
    vm_dir_path: str = str(Path.home() / "VMs" / vm_name)
    
    try:
        creator: VMCreator = VMCreator()
        
        # Load VM configuration to check current state
        with console.status("[bold yellow]Checking VM state..."):
            vm_info: dict[str, Any] = creator.create_linux_vm(name=vm_name)
            state: str = creator.get_vm_state()
        
        # Don't delete running VMs
        if state in ["running", "starting"]:
            console.print(f"[red]❌ Cannot delete VM '{vm_name}' while it's {state}.[/red]")
            console.print(f"[yellow]💡 Tip:[/yellow] Stop the VM first with 'macosprox stop {vm_name}'")
            sys.exit(1)
        
        # Show what will be deleted
        vm_dir = Path(vm_dir_path)
        if vm_dir.exists():
            try:
                files_to_delete = list(vm_dir.iterdir())
                
                console.print("\n[yellow]The following files will be deleted:[/yellow]")
                for file_path in files_to_delete:
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        size_mb = file_size / (1024 * 1024)
                        console.print(f"  • {file_path.name} ({size_mb:.1f} MB)")
                    elif file_path.is_dir():
                        console.print(f"  • {file_path.name}/ (directory)")
                
                console.print(f"\n[yellow]Directory:[/yellow] {vm_dir_path}")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not list files: {e}[/yellow]")
                console.print(f"[yellow]Directory:[/yellow] {vm_dir_path}")
        else:
            console.print(f"[yellow]VM directory not found:[/yellow] {vm_dir_path}")
        
        # Confirmation (unless --force)
        if not force:
            confirm = console.input(f"\n[bold red]Are you sure you want to delete VM '{vm_name}' and all its files? [y/N]: [/bold red]")
            if confirm.lower() not in ['y', 'yes']:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return
        
        # Delete the VM
        from .vm_creator import delete_vm
        with console.status(f"[bold red]Deleting VM '{vm_name}'..."):
            success: bool = delete_vm(vm_name)
        
        if success:
            console.print(f"\n[green]✅ VM '{vm_name}' deleted successfully![/green]")
        else:
            console.print(f"\n[red]❌ Failed to delete VM '{vm_name}'[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error deleting VM:[/red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
