// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "MacOSProxSwift",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "macosprox", targets: ["MacOSProxSwift"])
    ],
    dependencies: [
        // Dependencies declare other packages that this package depends on.
        // .package(url: /* package url */, from: "1.0.0"),
    ],
    targets: [
        .executableTarget(
            name: "MacOSProxSwift",
            dependencies: [],
            path: "Sources",
            resources: [
                .copy("../Resources/entitlements.plist")
            ],
            swiftSettings: [
                .define("ENABLE_VIRTUALIZATION")
            ],
            linkerSettings: [
                .linkedFramework("Virtualization"),
                .linkedFramework("Foundation")
            ]
        )
    ]
)
