"""Command Line Interface for macOS Proxmox VM Creator"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import sys
from pathlib import Path

from macosprox.vm_creator import VMCreator, list_vms, check_virtualization_support
from macosprox.models import VMInfo, VMListItem, VirtualizationSupport, VMStatus

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
    
    support_info: VirtualizationSupport = check_virtualization_support()
    
    if support_info.supported:
        console.print(Panel(
            f"✅ {support_info.message}\nPyObjC Version: {support_info.pyobjc_version or 'Unknown'}",
            title="[green]Virtualization Supported[/green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"❌ {support_info.message}\nError: {support_info.error or 'Unknown error'}",
            title="[red]Virtualization Not Supported[/red]",
            border_style="red"
        ))
        sys.exit(1)




@cli.command("list")
def list_vms_command() -> None:
    """List all VMs"""
    
    console.print("\n[bold blue]Listing VMs...[/bold blue]")
    
    vm_list: list[VMListItem] = list_vms()
    
    if not vm_list:
        console.print("[yellow]No VMs found.[/yellow]")
        console.print("[dim]Create your first VM with: macosprox create --name my-vm[/dim]")
        return
    
    table: Table = Table(title="Virtual Machines")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Status", style="green")
    
    for vm in vm_list:
        table.add_row(
            vm.name,
            vm.path,
            "Available" if vm.exists else "Missing"
        )
    
    console.print(table)


@cli.command()
@click.argument("vm_name")
@click.option("--foreground", "-f", is_flag=True, help="Keep VM running in foreground (required for VM to stay alive)")
@click.option("--cpu", "-c", default=2, help="Number of CPU cores for new VM (default: 2)")
@click.option("--memory", "-m", default=4, help="Memory in GB for new VM (default: 4)")
@click.option("--disk", "-d", default=20, help="Disk size in GB for new VM (default: 20)")
@click.option("--iso", "-i", help="Path to Linux ISO file for installation")
@click.option("--ssh-key", help="Path to SSH public key file (will generate one if not provided)")
@click.option("--auto-install", is_flag=True, help="Create cloud-init ISO for automatic Linux installation")
@click.option("--kernel", help="Path to kernel file (required for new VMs)")
@click.option("--initramfs", help="Path to initramfs file (required for new VMs)")
def start(vm_name: str, foreground: bool, cpu: int, memory: int, disk: int, iso: str | None, ssh_key: str | None, auto_install: bool, kernel: str | None, initramfs: str | None) -> None:
    from pathlib import Path
    """Start a VM (create if it doesn't exist)"""
    
    # Check if VM exists
    vm_list = list_vms()
    vm_exists = any(vm.name == vm_name for vm in vm_list)
    
    try:
        creator = VMCreator()
        
        # Validate kernel and initramfs (required for new VMs only)
        if not vm_exists:
            if not kernel:
                console.print(f"[red]Error:[/red] --kernel is required when creating a new VM")
                sys.exit(1)
            if not initramfs:
                console.print(f"[red]Error:[/red] --initramfs is required when creating a new VM")
                sys.exit(1)
            
            if not Path(kernel).exists():
                console.print(f"[red]Error:[/red] Kernel file not found: {kernel}")
                sys.exit(1)
            if not Path(initramfs).exists():
                console.print(f"[red]Error:[/red] Initramfs file not found: {initramfs}")
                sys.exit(1)
        
        # Validate SSH key if provided
        ssh_key_content = None
        if ssh_key and Path(ssh_key).exists():
            with open(ssh_key, 'r') as f:
                ssh_key_content = f.read().strip()
            console.print(f"[green]Using SSH key:[/green] {ssh_key}")
        elif ssh_key:
            console.print(f"[red]Error:[/red] SSH key file not found: {ssh_key}")
            sys.exit(1)
        
        # Validate ISO if provided
        if iso and not Path(iso).exists():
            console.print(f"[red]Error:[/red] ISO file not found: {iso}")
            sys.exit(1)
        
        # Check virtualization support first
        support_info: VirtualizationSupport = check_virtualization_support()
        if not support_info.supported:
            console.print(f"[red]Error:[/red] {support_info.message}")
            sys.exit(1)
        
        # Get or create VM configuration
        action = "Starting existing" if vm_exists else "Creating and starting new"
        console.print(f"\n[bold blue]{action} VM: {vm_name}[/bold blue]")
        
        with console.status("[bold green]Loading/Creating VM configuration..."):
            vm_info: VMInfo = creator.get_or_create_vm(
                name=vm_name,
                cpu_count=cpu,
                memory_size_gb=memory,
                disk_size_gb=disk,
                iso_path=iso,
                ssh_key=ssh_key_content,
                auto_install=auto_install,
                kernel_path=kernel,
                initramfs_path=initramfs
            )
        
        if not vm_exists:
            console.print(f"[green]✅ VM '{vm_name}' created successfully![/green]")

        # Start the VM
        with console.status("[bold green]Starting VM..."):
            success = creator.start_vm()
        if success:
            console.print(f"[green]✅ VM '{vm_name}' is starting...[/green]")
            
            if foreground:
                console.print("[yellow]💡 Running in foreground - press Ctrl+C to stop VM[/yellow]")
                
                # Show console log path
                from pathlib import Path
                console_log_path = Path.home() / "VMs" / vm_name / f"{vm_name}_console.log"
                console.print(f"[dim]Console output: {console_log_path}[/dim]")
                console.print(f"[dim]Tip: Run 'tail -f {console_log_path}' in another terminal to see boot output[/dim]")
                
                try:
                    console.print(f"[green]VM '{vm_name}' is now running in foreground...[/green]")
                    console.print("[yellow]Press Ctrl+C to stop VM and exit[/yellow]")
                    
                    # Run the NSRunLoop indefinitely to keep VM alive
                    creator.run_vm_forever()
                except KeyboardInterrupt:
                    console.print(f"\n[yellow]Stopping VM '{vm_name}'...[/yellow]")
                    creator.stop_vm()
                    console.print(f"[green]VM '{vm_name}' stopped[/green]")
            else:
                console.print("[yellow]💡 Note:[/yellow] VM will only stay running if you use --foreground flag")
                console.print("[yellow]💡 Tip:[/yellow] Use 'macosprox start {vm_name} --foreground' to keep VM alive")
                
                # Show current state
                current_state: VMStatus = creator.get_vm_state()
                console.print(f"[dim]Current state: {current_state.value}[/dim]")
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
            try:
                creator.get_or_create_vm(name=vm_name)
            except Exception as e:
                console.print(f"[red]❌ Failed to load VM configuration for '{vm_name}': {e}[/red]")
                sys.exit(1)
        
        # Check current state
        state: VMStatus = creator.get_vm_state()
        if state not in [VMStatus.RUNNING, VMStatus.STARTING]:
            console.print(f"[yellow]⚠️  VM '{vm_name}' is not running (state: {state.value})[/yellow]")
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
    vm_list: list[VMListItem] = list_vms()
    vm_exists: bool = any(vm.name == vm_name for vm in vm_list)
    
    if not vm_exists:
        console.print(f"[red]❌ VM '{vm_name}' not found.[/red]")
        sys.exit(1)
    
    try:
        creator: VMCreator = VMCreator()
        
        # Load VM configuration
        with console.status("[bold green]Loading VM configuration..."):
            if not creator.get_or_create_vm(name=vm_name):
                console.print(f"[red]❌ Failed to load VM configuration for '{vm_name}'[/red]")
                sys.exit(1)
        
        # Get current state
        state: VMStatus = creator.get_vm_state()
        
        # Create status display
        status_colors: dict[VMStatus, str] = {
            VMStatus.RUNNING: "green",
            VMStatus.STOPPED: "red", 
            VMStatus.STARTING: "yellow",
            VMStatus.STOPPING: "yellow",
            VMStatus.PAUSED: "blue",
            VMStatus.ERROR: "red",
            VMStatus.NOT_CONFIGURED: "dim",
            VMStatus.PAUSING: "yellow",
            VMStatus.RESUMING: "yellow",
            VMStatus.CREATED: "cyan",
            VMStatus.UNKNOWN: "white"
        }
        
        color: str = status_colors.get(state, "white")
        
        # Get VM directory path
        vm_dir_path = str(Path.home() / "VMs" / vm_name)
        
        console.print(Panel(
            f"VM: [bold]{vm_name}[/bold]\n"
            f"State: [{color}]{state.value.title()}[/{color}]\n"
            f"Path: [dim]{vm_dir_path}[/dim]",
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
    vm_list: list[VMListItem] = list_vms()
    vm_exists: bool = any(vm.name == vm_name for vm in vm_list)
    
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
            if not creator.get_or_create_vm(name=vm_name):
                console.print(f"[red]❌ Failed to load VM configuration for '{vm_name}'[/red]")
                sys.exit(1)
            state: VMStatus = creator.get_vm_state()
        
        # Don't delete running VMs
        if state in [VMStatus.RUNNING, VMStatus.STARTING]:
            console.print(f"[red]❌ Cannot delete VM '{vm_name}' while it's {state.value}.[/red]")
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


@cli.command()
@click.argument("vm_name")
@click.option("--user", "-u", default="ubuntu", help="SSH username (default: ubuntu)")
@click.option("--key", "-k", help="Path to SSH private key (uses VM's generated key if not specified)")
def ssh(vm_name: str, user: str, key: str | None) -> None:
    """SSH into a running VM"""
    
    console.print(f"\n[bold blue]Connecting to VM: {vm_name}[/bold blue]")
    
    # Check if VM exists
    vm_list: list[VMListItem] = list_vms()
    vm_exists: bool = any(vm.name == vm_name for vm in vm_list)
    
    if not vm_exists:
        console.print(f"[red]❌ VM '{vm_name}' not found.[/red]")
        sys.exit(1)
    
    try:
        creator: VMCreator = VMCreator()
        
        # Load VM configuration to check state
        with console.status("[bold green]Checking VM state..."):
            if not creator.load_existing_vm(name=vm_name):
                console.print(f"[red]❌ Failed to load VM configuration for '{vm_name}'[/red]")
                sys.exit(1)
            state: VMStatus = creator.get_vm_state()
        
        if state != VMStatus.RUNNING:
            console.print(f"[red]❌ VM '{vm_name}' is not running (state: {state.value})[/red]")
            console.print("[yellow]💡 Tip:[/yellow] Start the VM first with 'macosprox start {vm_name}'")
            sys.exit(1)
        
        # Try to get VM IP
        with console.status("[bold green]Finding VM IP address..."):
            vm_ip = creator.get_vm_ip(vm_name)
        
        if not vm_ip:
            console.print("[red]❌ Could not determine VM IP address.[/red]")
            console.print("[yellow]💡 Try waiting a few minutes for the VM to boot and get an IP address.[/yellow]")
            sys.exit(1)
        
        console.print(f"[green]Found VM IP:[/green] {vm_ip}")
        
        # Determine SSH key to use
        if not key:
            vm_dir = Path.home() / "VMs" / vm_name / "ssh"
            generated_key = vm_dir / "vm_key"
            if generated_key.exists():
                key = str(generated_key)
                console.print(f"[dim]Using generated SSH key: {key}[/dim]")
            else:
                console.print("[yellow]No SSH key specified and no generated key found.[/yellow]")
                console.print("[dim]Trying SSH without key (password authentication)...[/dim]")
        
        # Build SSH command
        ssh_cmd = ["ssh", f"{user}@{vm_ip}"]
        if key:
            ssh_cmd.extend(["-i", key])
        
        # Add SSH options for better connection
        ssh_cmd.extend([
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10"
        ])
        
        console.print(f"[green]Connecting to {user}@{vm_ip}...[/green]")
        console.print("[dim]Use 'exit' to disconnect from the VM[/dim]")
        
        # Execute SSH command
        import os
        os.execvp("ssh", ssh_cmd)
        
    except Exception as e:
        console.print(f"[red]❌ Error connecting to VM:[/red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
