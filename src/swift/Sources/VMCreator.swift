import Foundation
import Virtualization
import CryptoKit

// Define VMStatus enum
enum VMStatus: String, Codable {
    case created = "created"
    case stopped = "stopped"
    case running = "running"
    case starting = "starting"
    case stopping = "stopping"
    case paused = "paused"
    case pausing = "pausing"
    case resuming = "resuming"
    case error = "error"
    case notConfigured = "not_configured"
    case unknown = "unknown"
}

// Define VMInfo struct
struct VMInfo: Codable {
    let name: String
    let type: String  // Or enum for VM type
    let cpu_count: Int
    let memory_gb: Int
    let disk_gb: Int
    let disk_path: String
    let vm_dir: String
    let status: VMStatus
}

class VMCreator: NSObject, VZVirtualMachineDelegate {  // Inherit from NSObject and conform to VZVirtualMachineDelegate

    private var vm: VZVirtualMachine?

    func createVM(configuration: VMConfiguration) async {  // Add async
        // Set VM directory
        let vmName = configuration.name
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        let vmDir = homeDir.appendingPathComponent("VMs").appendingPathComponent(vmName, isDirectory: true)

        // Check if VM already exists
        let metadataFile = vmDir.appendingPathComponent("vm_metadata.json")

        if FileManager.default.fileExists(atPath: vmDir.path)
            && FileManager.default.fileExists(atPath: metadataFile.path)
        {
            print("Loading existing VM: \(vmName)")

            // Load existing VM metadata
            do {
                let data = try Data(contentsOf: metadataFile)
                let decoder = JSONDecoder()
                let metadata = try decoder.decode(VMInfo.self, from: data)
                print("Loaded VM metadata: \(metadata.name)")

            } catch {
                print("Error loading VM metadata: \(error.localizedDescription)")
                // Handle the error appropriately (e.g., create a new VM)
            }
        } else {
            print("Creating new Linux VM: \(vmName)")

            // Create VM directory
            do {
                try FileManager.default.createDirectory(
                    at: vmDir, withIntermediateDirectories: true, attributes: nil)
            } catch {
                print("Error creating VM directory: \(error.localizedDescription)")
                return
            }
        }
        // Create VM configuration
        let config = VZVirtualMachineConfiguration()
        config.cpuCount = configuration.cpuCount
        config.memorySize = UInt64(configuration.memorySizeGB) * 1024 * 1024 * 1024  // Convert GB to bytes

        // Platform configuration
        let platform = VZGenericPlatformConfiguration()
        config.platform = platform
        
        // Boot loader configuration - EFI for UEFI support
        let efiVariableStore = vmDir.appendingPathComponent("efi_vars.fd")
        if !FileManager.default.fileExists(atPath: efiVariableStore.path) {
            // Create EFI variable store
            do {
                _ = try VZEFIVariableStore.init(creatingVariableStoreAt: efiVariableStore)
            } catch {
                print("Error creating EFI variable store: \(error.localizedDescription)")
                return
            }
        }
        
        let variableStore = VZEFIVariableStore(url: efiVariableStore)
        let bootLoader = VZEFIBootLoader()
        bootLoader.variableStore = variableStore
        config.bootLoader = bootLoader

        // Disk setup
        let diskImageURL = vmDir.appendingPathComponent("\(vmName).img")

        if !FileManager.default.fileExists(atPath: diskImageURL.path) {
            createDiskImage(at: diskImageURL, sizeInGB: configuration.diskSizeGB)
        }

        do {
            let diskAttachment = try VZDiskImageStorageDeviceAttachment(
                url: diskImageURL, readOnly: false)
            let disk = VZVirtioBlockDeviceConfiguration(attachment: diskAttachment)
            config.storageDevices = [disk]
        } catch {
            print("Error creating disk attachment: \(error.localizedDescription)")
            return
        }

        // Networking - NAT with predictable MAC address
        let networkDevice = VZVirtioNetworkDeviceConfiguration()
        let natAttachment = VZNATNetworkDeviceAttachment()
        networkDevice.attachment = natAttachment
        
        // Generate predictable MAC address based on VM name
        let macAddress = generateMACAddress(for: vmName)
        networkDevice.macAddress = VZMACAddress(string: macAddress)!
        config.networkDevices = [networkDevice]
        
        print("VM Network MAC Address: \(macAddress)")

        // Configure entropy device (random number generator)
        let entropyDevice = VZVirtioEntropyDeviceConfiguration()
        config.entropyDevices = [entropyDevice]
        
        // Configure input devices
        let keyboard = VZUSBKeyboardConfiguration()
        let pointingDevice = VZUSBScreenCoordinatePointingDeviceConfiguration()
        config.keyboards = [keyboard]
        config.pointingDevices = [pointingDevice]
        
        // Configure graphics
        let graphicsDevice = VZVirtioGraphicsDeviceConfiguration()
        let scanout = VZVirtioGraphicsScanoutConfiguration(widthInPixels: 800, heightInPixels: 600)
        graphicsDevice.scanouts = [scanout]
        config.graphicsDevices = [graphicsDevice]
        
        // Configure audio (simplified for compatibility)
        let audioDevice = VZVirtioSoundDeviceConfiguration()
        let audioInputStreamConfig = VZVirtioSoundDeviceInputStreamConfiguration()
        let audioOutputStreamConfig = VZVirtioSoundDeviceOutputStreamConfiguration()
        audioDevice.streams = [audioInputStreamConfig, audioOutputStreamConfig]
        config.audioDevices = [audioDevice]
        
        // Console configuration for debugging
        let consoleDevice = VZVirtioConsoleDeviceConfiguration()
        let consolePort = VZVirtioConsolePortConfiguration()
        consolePort.isConsole = true
        
        // Create file handles for console logging
        let consoleLogPath = vmDir.appendingPathComponent("\(vmName)_console.log")
        FileManager.default.createFile(atPath: consoleLogPath.path, contents: "Console log for VM \(vmName)\n".data(using: .utf8))
        
        if let fileHandle = FileHandle(forWritingAtPath: consoleLogPath.path) {
            let consoleAttachment = VZFileHandleSerialPortAttachment(fileHandleForReading: FileHandle.standardInput,
                                                                    fileHandleForWriting: fileHandle)
            consolePort.attachment = consoleAttachment
            print("Console output will be written to: \(consoleLogPath.path)")
        }
        
        consoleDevice.ports[0] = consolePort
        config.consoleDevices = [consoleDevice]
        
        // ISO mounting for installation
        if let isoPath = configuration.isoPath, FileManager.default.fileExists(atPath: isoPath) {
            print("Mounting ISO: \(isoPath)")
            do {
                let isoURL = URL(fileURLWithPath: isoPath)
                let isoAttachment = try VZDiskImageStorageDeviceAttachment(url: isoURL, readOnly: true)
                let isoDisk = VZVirtioBlockDeviceConfiguration(attachment: isoAttachment)
                config.storageDevices.append(isoDisk)
            } catch {
                print("Error mounting ISO: \(error.localizedDescription)")
            }
        }
        
        // Cloud-init ISO creation and mounting
        if configuration.autoInstall {
            do {
                let cloudInitISOPath = try createCloudInitISO(vmDir: vmDir, vmName: vmName, sshKeyPath: configuration.sshKeyPath)
                if FileManager.default.fileExists(atPath: cloudInitISOPath) {
                    print("Mounting cloud-init ISO: \(cloudInitISOPath)")
                    let cloudInitURL = URL(fileURLWithPath: cloudInitISOPath)
                    let cloudInitAttachment = try VZDiskImageStorageDeviceAttachment(url: cloudInitURL, readOnly: true)
                    let cloudInitDisk = VZVirtioBlockDeviceConfiguration(attachment: cloudInitAttachment)
                    config.storageDevices.append(cloudInitDisk)
                    print("Cloud-init ISO mounted successfully")
                } else {
                    print("Warning: Cloud-init ISO creation failed or file not found")
                }
            } catch {
                print("Failed to create/mount cloud-init ISO: \(error.localizedDescription)")
            }
        }
        
        // Validate configuration
        do {
            try config.validate()
        } catch {
            print("VM configuration validation failed: \(error.localizedDescription)")
            return
        }
        
        // Create VM instance
        print("Creating VZVirtualMachine with configuration")
        let vm = VZVirtualMachine(configuration: config)
        self.vm = vm
        vm.delegate = self
        print("VZVirtualMachine created successfully")
        
        // Store VM metadata
        let vmMetadata = VMInfo(
            name: vmName,
            type: "linux",
            cpu_count: configuration.cpuCount,
            memory_gb: configuration.memorySizeGB,
            disk_gb: configuration.diskSizeGB,
            disk_path: diskImageURL.path,
            vm_dir: vmDir.path,
            status: .created
        )
        
        do {
            let metadataData = try JSONEncoder().encode(vmMetadata)
            let metadataFile = vmDir.appendingPathComponent("vm_metadata.json")
            try metadataData.write(to: metadataFile)
        } catch {
            print("Error saving VM metadata: \(error.localizedDescription)")
        }

        print("VM creation initiated with configuration: \(configuration)")

        // Example: Displaying the configuration details
        print("  Name: \(configuration.name)")
        print("  CPU Count: \(configuration.cpuCount)")
        print("  Memory: \(configuration.memorySizeGB) GB")
        print("  Disk Size: \(configuration.diskSizeGB) GB")
    }

    private func createDiskImage(at url: URL, sizeInGB: Int) {
        let ddProcess = Process()
        ddProcess.executableURL = URL(fileURLWithPath: "/bin/dd")
        ddProcess.arguments = [
            "if=/dev/zero",
            "of=\(url.path)",
            "bs=1m",  // Use 1MB blocks
            "count=\(sizeInGB * 1024)",  // 1GB = 1024MB
        ]

        let pipe = Pipe()
        ddProcess.standardError = pipe
        ddProcess.standardOutput = pipe

        do {
            try ddProcess.run()
            ddProcess.waitUntilExit()

            if ddProcess.terminationStatus != 0 {
                print("Disk image creation failed.")
            } else {
                print("Disk image created successfully at \(url.path)")
            }
        } catch {
            print("Error creating disk image: \(error.localizedDescription)")
        }
    }

    func guestDidStop(_ virtualMachine: VZVirtualMachine) {
        print("Guest stopped")
    }
    
    func virtualMachine(_ virtualMachine: VZVirtualMachine, didStopWithError error: Error) {
        print("Virtual machine stopped with error: \(error.localizedDescription)")
    }
    
    func virtualMachine(_ virtualMachine: VZVirtualMachine, didFailToStart error: Error) {
        print("Virtual machine failed to start: \(error.localizedDescription)")
    }
    
    // MARK: - VM Management Operations
    
    func startVM() async throws {
        guard let vm = self.vm else {
            throw NSError(domain: "VMCreator", code: 1, userInfo: [NSLocalizedDescriptionKey: "No VM configured"])
        }
        
        guard vm.canStart else {
            throw NSError(domain: "VMCreator", code: 2, userInfo: [NSLocalizedDescriptionKey: "VM cannot be started"])
        }
        
        print("Starting VM...")
        try await vm.start()
        print("VM started successfully")
    }
    
    func stopVM() async throws {
        guard let vm = self.vm else {
            throw NSError(domain: "VMCreator", code: 1, userInfo: [NSLocalizedDescriptionKey: "No VM configured"])
        }
        
        print("Stopping VM...")
        try await vm.stop()
        print("VM stopped successfully")
    }
    
    func getVMStatus() -> VMStatus {
        guard let vm = self.vm else {
            return .notConfigured
        }
        
        switch vm.state {
        case .stopped:
            return .stopped
        case .running:
            return .running
        case .paused:
            return .paused
        case .error:
            return .error
        case .starting:
            return .starting
        case .pausing:
            return .pausing
        case .resuming:
            return .resuming
        case .stopping:
            return .stopping
        case .saving:
            return .stopping  // Map saving to stopping for simplicity
        case .restoring:
            return .starting  // Map restoring to starting for simplicity
        @unknown default:
            return .unknown
        }
    }
    
    // MARK: - Helper Functions
    
    private func generateMACAddress(for vmName: String) -> String {
        let hash = abs(vmName.hashValue)
        let byte1 = (hash >> 16) & 0xFF
        let byte2 = (hash >> 8) & 0xFF
        let byte3 = hash & 0xFF
        return String(format: "52:54:00:%02x:%02x:%02x", byte1, byte2, byte3)
    }
    
    private func createCloudInitISO(vmDir: URL, vmName: String, sshKeyPath: String?) throws -> String {
        let cloudInitDir = vmDir.appendingPathComponent("cloud-init", isDirectory: true)
        try FileManager.default.createDirectory(at: cloudInitDir, withIntermediateDirectories: true)
        
        // Generate or read SSH key
        let sshKey: String
        if let keyPath = sshKeyPath, FileManager.default.fileExists(atPath: keyPath) {
            sshKey = try String(contentsOfFile: keyPath).trimmingCharacters(in: .whitespacesAndNewlines)
        } else {
            // Create SSH key pair
            let sshDir = vmDir.appendingPathComponent("ssh", isDirectory: true)
            try FileManager.default.createDirectory(at: sshDir, withIntermediateDirectories: true)
            
            let privateKeyPath = sshDir.appendingPathComponent("vm_key")
            let publicKeyPath = sshDir.appendingPathComponent("vm_key.pub")
            
            if !FileManager.default.fileExists(atPath: privateKeyPath.path) {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/usr/bin/ssh-keygen")
                process.arguments = ["-t", "rsa", "-b", "2048", "-f", privateKeyPath.path, "-N", ""]
                try process.run()
                process.waitUntilExit()
            }
            
            sshKey = try String(contentsOf: publicKeyPath).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        
        // Create user-data
        let userData = """
        #cloud-config
        hostname: \(vmName)
        manage_etc_hosts: true
        
        users:
          - name: ubuntu
            sudo: ALL=(ALL) NOPASSWD:ALL
            shell: /bin/bash
            lock_passwd: false
            passwd: $6$rounds=4096$aQ7lBLKCKLV$w0Jd8PkQmL8hZGdLNa1s1y3YI2IJ3j4K5L6M7N8O9P0Q1R2S3T4U5V6W7X8Y9Z0A1B2C3D4E5F6G7H8I9J0K1L2M3
            ssh_authorized_keys:
              - \(sshKey)
        
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
        
        let userDataFile = cloudInitDir.appendingPathComponent("user-data")
        try userData.write(to: userDataFile, atomically: true, encoding: .utf8)
        
        // Create meta-data
        let metaData = """
        instance-id: \(vmName)-001
        local-hostname: \(vmName)
        """
        
        let metaDataFile = cloudInitDir.appendingPathComponent("meta-data")
        try metaData.write(to: metaDataFile, atomically: true, encoding: .utf8)
        
        // Create cloud-init ISO
        let cloudInitISO = vmDir.appendingPathComponent("\(vmName)-cloud-init.iso")
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/hdiutil")
        process.arguments = [
            "makehybrid", "-o", cloudInitISO.path,
            "-hfs", "-joliet", "-iso", "-default-volume-name", "cidata",
            cloudInitDir.path
        ]
        
        try process.run()
        process.waitUntilExit()
        
        if process.terminationStatus != 0 {
            throw NSError(domain: "VMCreator", code: 3, userInfo: [NSLocalizedDescriptionKey: "Failed to create cloud-init ISO"])
        }
        
        print("Cloud-init ISO created: \(cloudInitISO.path)")
        return cloudInitISO.path
    }
    
    func getVMIP(vmName: String) -> String? {
        let macAddress = generateMACAddress(for: vmName)
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/arp")
        process.arguments = ["-a"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8) ?? ""
            
            for line in output.components(separatedBy: .newlines) {
                if line.lowercased().contains(macAddress.lowercased()) {
                    // Extract IP from line like: "? (192.168.64.2) at 52:54:00:xx:xx:xx on vmnet1 ifscope [ethernet]"
                    let regex = try NSRegularExpression(pattern: "\\((\\d+\\.\\d+\\.\\d+\\.\\d+)\\)")
                    let range = NSRange(location: 0, length: line.utf16.count)
                    if let match = regex.firstMatch(in: line, range: range) {
                        let ipRange = Range(match.range(at: 1), in: line)!
                        return String(line[ipRange])
                    }
                }
            }
        } catch {
            print("Error getting VM IP: \(error.localizedDescription)")
        }
        
        return nil
    }
}
