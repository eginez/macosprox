import Foundation
import Virtualization

enum Command {
    case create(VMConfiguration)
    case start(String)
    case stop(String)
    case status(String)
    case list
    case delete(String)
    case ssh(String, String?, String?)
    case check
    case help
}

// Define a struct to hold VM configuration parameters
struct VMConfiguration {
    let name: String
    let cpuCount: Int
    let memorySizeGB: Int
    let diskSizeGB: Int
    let isoPath: String?
    let sshKeyPath: String?  // Optional path to SSH key
    let autoInstall: Bool

    // Add a default initializer to set all values
    init(
        name: String, cpuCount: Int = 2, memorySizeGB: Int = 4, diskSizeGB: Int = 20,
        isoPath: String? = nil, sshKeyPath: String? = nil, autoInstall: Bool = false
    ) {
        self.name = name
        self.cpuCount = cpuCount
        self.memorySizeGB = memorySizeGB
        self.diskSizeGB = diskSizeGB
        self.isoPath = isoPath
        self.sshKeyPath = sshKeyPath
        self.autoInstall = autoInstall
    }
}

// Function to parse command-line arguments
func parseArguments() -> Command? {
    let arguments = Array(CommandLine.arguments.dropFirst())  // Drop the executable path
    guard !arguments.isEmpty else {
        return .help
    }
    
    let command = arguments[0]
    let remainingArgs = Array(arguments.dropFirst())
    
    switch command {
    case "create":
        return parseCreateCommand(args: remainingArgs)
    case "start":
        guard remainingArgs.count == 1 else {
            print("Usage: macosprox start <vm_name>")
            return nil
        }
        return .start(remainingArgs[0])
    case "stop":
        guard remainingArgs.count == 1 else {
            print("Usage: macosprox stop <vm_name>")
            return nil
        }
        return .stop(remainingArgs[0])
    case "status":
        guard remainingArgs.count == 1 else {
            print("Usage: macosprox status <vm_name>")
            return nil
        }
        return .status(remainingArgs[0])
    case "list":
        return .list
    case "delete":
        guard remainingArgs.count == 1 else {
            print("Usage: macosprox delete <vm_name>")
            return nil
        }
        return .delete(remainingArgs[0])
    case "ssh":
        guard remainingArgs.count >= 1 else {
            print("Usage: macosprox ssh <vm_name> [--user <username>] [--key <key_path>]")
            return nil
        }
        let vmName = remainingArgs[0]
        var user: String?
        var keyPath: String?
        
        var i = 1
        while i < remainingArgs.count {
            switch remainingArgs[i] {
            case "--user":
                i += 1
                if i < remainingArgs.count {
                    user = remainingArgs[i]
                }
            case "--key":
                i += 1
                if i < remainingArgs.count {
                    keyPath = remainingArgs[i]
                }
            default:
                break
            }
            i += 1
        }
        return .ssh(vmName, user, keyPath)
    case "check":
        return .check
    case "help", "--help", "-h":
        return .help
    default:
        print("Unknown command: \(command)")
        return .help
    }
}

func parseCreateCommand(args: [String]) -> Command? {
    var name: String?
    var cpuCount: Int = 2
    var memorySizeGB: Int = 4
    var diskSizeGB: Int = 20
    var isoPath: String?
    var sshKeyPath: String?
    var autoInstall = false
    
    var index = 0
    while index < args.count {
        let arg = args[index]
        switch arg {
        case "--name":
            index += 1
            if index < args.count {
                name = args[index]
            } else {
                print("Error: Missing value for --name")
                return nil
            }
        case "--cpu":
            index += 1
            if index < args.count {
                if let cpu = Int(args[index]), cpu > 0 {
                    cpuCount = cpu
                } else {
                    print("Error: Invalid value for --cpu. Must be a positive integer.")
                    return nil
                }
            } else {
                print("Error: Missing value for --cpu")
                return nil
            }
        case "--memory":
            index += 1
            if index < args.count {
                if let memory = Int(args[index]), memory > 0 {
                    memorySizeGB = memory
                } else {
                    print("Error: Invalid value for --memory. Must be a positive integer.")
                    return nil
                }
            } else {
                print("Error: Missing value for --memory")
                return nil
            }
        case "--disk":
            index += 1
            if index < args.count {
                if let disk = Int(args[index]), disk > 0 {
                    diskSizeGB = disk
                } else {
                    print("Error: Invalid value for --disk. Must be a positive integer.")
                    return nil
                }
            } else {
                print("Error: Missing value for --disk")
                return nil
            }
        case "--iso":
            index += 1
            if index < args.count {
                isoPath = args[index]
            } else {
                print("Error: Missing value for --iso")
                return nil
            }
        case "--ssh-key":
            index += 1
            if index < args.count {
                sshKeyPath = args[index]
            } else {
                print("Error: Missing value for --ssh-key")
                return nil
            }
        case "--auto-install":
            autoInstall = true
        default:
            print("Error: Unknown argument \(arg)")
            return nil
        }
        index += 1
    }
    
    guard let vmName = name else {
        print("Error: Missing required argument --name")
        return nil
    }
    
    let config = VMConfiguration(
        name: vmName, cpuCount: cpuCount, memorySizeGB: memorySizeGB,
        diskSizeGB: diskSizeGB, isoPath: isoPath, sshKeyPath: sshKeyPath,
        autoInstall: autoInstall)
    
    return .create(config)
}

func printHelp() {
    print("""
    macOS Prox - VM Creator using Apple's Virtualization Framework
    
    Usage:
        macosprox <command> [options]
    
    Commands:
        create          Create a new VM
        start           Start a VM
        stop            Stop a VM
        status          Check VM status
        list            List all VMs
        delete          Delete a VM
        ssh             SSH into a VM
        check           Check virtualization support
        help            Show this help message
    
    Create Options:
        --name <name>       VM name (required)
        --cpu <count>       Number of CPU cores (default: 2)
        --memory <gb>       Memory in GB (default: 4)
        --disk <gb>         Disk size in GB (default: 20)
        --iso <path>        Path to ISO file
        --ssh-key <path>    Path to SSH public key
        --auto-install      Enable automatic installation with cloud-init
    
    SSH Options:
        --user <username>   SSH username (default: ubuntu)
        --key <path>        Path to SSH private key
    
    Examples:
        macosprox create --name ubuntu-vm --cpu 4 --memory 8 --disk 40 --iso ~/ubuntu.iso --auto-install
        macosprox start ubuntu-vm
        macosprox ssh ubuntu-vm --user ubuntu
        macosprox stop ubuntu-vm
    """)
}

func listVMs() {
    let homeDir = FileManager.default.homeDirectoryForCurrentUser
    let vmsDir = homeDir.appendingPathComponent("VMs")
    
    guard FileManager.default.fileExists(atPath: vmsDir.path) else {
        print("No VMs directory found")
        return
    }
    
    do {
        let contents = try FileManager.default.contentsOfDirectory(at: vmsDir, includingPropertiesForKeys: nil)
        let vmDirs = contents.filter { $0.hasDirectoryPath }
        
        if vmDirs.isEmpty {
            print("No VMs found")
            return
        }
        
        print("Available VMs:")
        for vmDir in vmDirs {
            let vmName = vmDir.lastPathComponent
            let metadataFile = vmDir.appendingPathComponent("vm_metadata.json")
            
            if FileManager.default.fileExists(atPath: metadataFile.path) {
                do {
                    let data = try Data(contentsOf: metadataFile)
                    let metadata = try JSONDecoder().decode(VMInfo.self, from: data)
                    print("  \(vmName) - \(metadata.cpu_count) CPU, \(metadata.memory_gb)GB RAM, \(metadata.disk_gb)GB disk")
                } catch {
                    print("  \(vmName) - (metadata error)")
                }
            } else {
                print("  \(vmName) - (no metadata)")
            }
        }
    } catch {
        print("Error listing VMs: \(error.localizedDescription)")
    }
}

func deleteVM(name: String) {
    let homeDir = FileManager.default.homeDirectoryForCurrentUser
    let vmDir = homeDir.appendingPathComponent("VMs").appendingPathComponent(name)
    
    guard FileManager.default.fileExists(atPath: vmDir.path) else {
        print("VM '\(name)' not found")
        return
    }
    
    do {
        try FileManager.default.removeItem(at: vmDir)
        print("VM '\(name)' deleted successfully")
    } catch {
        print("Error deleting VM: \(error.localizedDescription)")
    }
}

func sshToVM(name: String, user: String?, keyPath: String?) {
    let vmCreator = VMCreator()
    
    guard let ip = vmCreator.getVMIP(vmName: name) else {
        print("Could not find IP address for VM '\(name)'")
        print("Make sure the VM is running and has completed boot")
        return
    }
    
    let username = user ?? "ubuntu"
    var sshCommand = ["ssh", "\(username)@\(ip)"]
    
    if let key = keyPath {
        sshCommand.insert("-i", at: 1)
        sshCommand.insert(key, at: 2)
    } else {
        // Try to use auto-generated key
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        let vmDir = homeDir.appendingPathComponent("VMs").appendingPathComponent(name)
        let autoKeyPath = vmDir.appendingPathComponent("ssh").appendingPathComponent("vm_key")
        
        if FileManager.default.fileExists(atPath: autoKeyPath.path) {
            sshCommand.insert("-i", at: 1)
            sshCommand.insert(autoKeyPath.path, at: 2)
        }
    }
    
    print("Connecting to \(username)@\(ip)...")
    
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/ssh")
    process.arguments = Array(sshCommand.dropFirst())
    
    do {
        try process.run()
        process.waitUntilExit()
    } catch {
        print("Error running SSH: \(error.localizedDescription)")
    }
}

func checkVirtualizationSupport() {
    do {
        let config = VZVirtualMachineConfiguration()
        config.cpuCount = 1
        config.memorySize = 1024 * 1024 * 1024  // 1GB
        
        let platform = VZGenericPlatformConfiguration()
        config.platform = platform
        
        // Create a temporary EFI variable store for validation
        let tempURL = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("temp_efi_vars.fd")
        
        // Clean up any existing temp file
        try? FileManager.default.removeItem(at: tempURL)
        
        // Create temporary EFI variable store
        _ = try VZEFIVariableStore(creatingVariableStoreAt: tempURL)
        let variableStore = VZEFIVariableStore(url: tempURL)
        
        let bootLoader = VZEFIBootLoader()
        bootLoader.variableStore = variableStore
        config.bootLoader = bootLoader
        
        // Add minimal storage for validation
        let tempDiskURL = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("temp_disk.img")
        try? FileManager.default.removeItem(at: tempDiskURL)
        
        // Create a small temporary disk
        let data = Data(count: 1024 * 1024) // 1MB
        try data.write(to: tempDiskURL)
        
        let diskAttachment = try VZDiskImageStorageDeviceAttachment(url: tempDiskURL, readOnly: false)
        let disk = VZVirtioBlockDeviceConfiguration(attachment: diskAttachment)
        config.storageDevices = [disk]
        
        // Add network device
        let networkDevice = VZVirtioNetworkDeviceConfiguration()
        let natAttachment = VZNATNetworkDeviceAttachment()
        networkDevice.attachment = natAttachment
        config.networkDevices = [networkDevice]
        
        // Add entropy device
        let entropyDevice = VZVirtioEntropyDeviceConfiguration()
        config.entropyDevices = [entropyDevice]
        
        try config.validate()
        
        print("✅ Virtualization support: Available")
        print("✅ Apple Virtualization Framework: Working")
        print("✅ Configuration validation: Passed")
        print("✅ Entitlements: Properly configured")
        
        // Clean up temporary files
        try? FileManager.default.removeItem(at: tempURL)
        try? FileManager.default.removeItem(at: tempDiskURL)
        
    } catch {
        print("❌ Virtualization support check failed: \(error.localizedDescription)")
        
        // Clean up temporary files even on error
        let tempURL = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("temp_efi_vars.fd")
        let tempDiskURL = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("temp_disk.img")
        try? FileManager.default.removeItem(at: tempURL)
        try? FileManager.default.removeItem(at: tempDiskURL)
    }
}

// Main execution functions
func executeCommand(_ command: Command) async {
    switch command {
    case .create(let config):
        await createVM(config: config)
    case .start(let name):
        await startVM(name: name)
    case .stop(let name):
        await stopVM(name: name)
    case .status(let name):
        checkVMStatus(name: name)
    case .list:
        listVMs()
    case .delete(let name):
        deleteVM(name: name)
    case .ssh(let name, let user, let keyPath):
        sshToVM(name: name, user: user, keyPath: keyPath)
    case .check:
        checkVirtualizationSupport()
    case .help:
        printHelp()
    }
}

func createVM(config: VMConfiguration) async {
    print("Creating VM with configuration:")
    print("  Name: \(config.name)")
    print("  CPU Count: \(config.cpuCount)")
    print("  Memory: \(config.memorySizeGB) GB")
    print("  Disk Size: \(config.diskSizeGB) GB")
    if let isoPath = config.isoPath {
        print("  ISO Path: \(isoPath)")
    }
    if let sshKeyPath = config.sshKeyPath {
        print("  SSH Key Path: \(sshKeyPath)")
    }
    print("  Auto Install: \(config.autoInstall)")
    
    let vmCreator = VMCreator()
    await vmCreator.createVM(configuration: config)
}

func startVM(name: String) async {
    print("Starting VM: \(name)")
    let vmCreator = VMCreator()
    
    // Load existing VM configuration
    let homeDir = FileManager.default.homeDirectoryForCurrentUser
    let vmDir = homeDir.appendingPathComponent("VMs").appendingPathComponent(name)
    let metadataFile = vmDir.appendingPathComponent("vm_metadata.json")
    
    guard FileManager.default.fileExists(atPath: metadataFile.path) else {
        print("VM '\(name)' not found")
        return
    }
    
    do {
        let data = try Data(contentsOf: metadataFile)
        let metadata = try JSONDecoder().decode(VMInfo.self, from: data)
        
        let config = VMConfiguration(
            name: metadata.name,
            cpuCount: metadata.cpu_count,
            memorySizeGB: metadata.memory_gb,
            diskSizeGB: metadata.disk_gb
        )
        
        await vmCreator.createVM(configuration: config)
        try await vmCreator.startVM()
        
        print("VM '\(name)' started successfully")
        print("Console output: \(vmDir.appendingPathComponent("\(name)_console.log").path)")
        
        // Try to get IP address after a delay
        Task {
            try await Task.sleep(nanoseconds: 10_000_000_000) // Sleep for 10 seconds
            if let ip = vmCreator.getVMIP(vmName: name) {
                print("VM IP Address: \(ip)")
                print("SSH access: ssh ubuntu@\(ip)")
            }
        }
        
        // Keep the process running
        // Note: In production, you'd want to handle signals or user input to exit gracefully
        while true {
            try await Task.sleep(nanoseconds: 1_000_000_000) // Sleep for 1 second
        }
    } catch {
        print("Error starting VM: \(error.localizedDescription)")
    }
}

func stopVM(name: String) async {
    print("Stopping VM: \(name)")
    let vmCreator = VMCreator()
    
    do {
        try await vmCreator.stopVM()
        print("VM '\(name)' stopped successfully")
    } catch {
        print("Error stopping VM: \(error.localizedDescription)")
    }
}

func checkVMStatus(name: String) {
    let homeDir = FileManager.default.homeDirectoryForCurrentUser
    let vmDir = homeDir.appendingPathComponent("VMs").appendingPathComponent(name)
    let metadataFile = vmDir.appendingPathComponent("vm_metadata.json")
    
    guard FileManager.default.fileExists(atPath: metadataFile.path) else {
        print("VM '\(name)' not found")
        return
    }
    
    do {
        let data = try Data(contentsOf: metadataFile)
        let metadata = try JSONDecoder().decode(VMInfo.self, from: data)
        
        print("VM Status: \(name)")
        print("  Status: \(metadata.status.rawValue)")
        print("  CPU Count: \(metadata.cpu_count)")
        print("  Memory: \(metadata.memory_gb) GB")
        print("  Disk Size: \(metadata.disk_gb) GB")
        print("  VM Directory: \(metadata.vm_dir)")
        print("  Disk Path: \(metadata.disk_path)")
        
        // Try to get IP if running
        let vmCreator = VMCreator()
        if let ip = vmCreator.getVMIP(vmName: name) {
            print("  IP Address: \(ip)")
        }
    } catch {
        print("Error reading VM metadata: \(error.localizedDescription)")
    }
}

// Main entry point
func main() async {
    if let command = parseArguments() {
        await executeCommand(command)
    }
}

// Run the main function
Task {
    await main()
    exit(0)
}

// Keep the program running until the task completes
RunLoop.main.run()