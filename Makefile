# Makefile for macOS Prox Swift Implementation

.PHONY: build clean test help sign

# Swift project directory
SWIFT_DIR = src/swift

# Default target
all: build sign

# Build the Swift package
build:
	@echo "🔨 Building macOS Prox Swift implementation..."
	cd $(SWIFT_DIR) && swift build

# Build and sign with entitlements
sign: build
	@echo "🔐 Signing executable with entitlements..."
	cd $(SWIFT_DIR) && codesign --force --sign - --entitlements Resources/entitlements.plist .build/debug/macosprox
	@echo "✅ Build and signing complete!"
	@echo "Executable: $(SWIFT_DIR)/.build/debug/macosprox"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	cd $(SWIFT_DIR) && swift package clean
	cd $(SWIFT_DIR) && rm -rf .build

# Run tests
test: sign
	@echo "🧪 Running basic functionality tests..."
	cd $(SWIFT_DIR) && ./.build/debug/macosprox check
	cd $(SWIFT_DIR) && ./.build/debug/macosprox list
	@echo "✅ Basic tests passed!"

# Development build (faster, no signing)
dev:
	@echo "🔨 Building for development (no signing)..."
	cd $(SWIFT_DIR) && swift build

# Release build
release:
	@echo "🔨 Building for release..."
	cd $(SWIFT_DIR) && swift build -c release
	cd $(SWIFT_DIR) && codesign --force --sign - --entitlements Resources/entitlements.plist .build/release/macosprox
	@echo "✅ Release build complete!"
	@echo "Executable: $(SWIFT_DIR)/.build/release/macosprox"

# Show help
help:
	@echo "Available targets:"
	@echo "  build    - Build the Swift package"
	@echo "  sign     - Build and sign with entitlements (default)"
	@echo "  clean    - Clean build artifacts"
	@echo "  test     - Run basic functionality tests"
	@echo "  dev      - Development build (faster, no signing)"
	@echo "  release  - Release build with optimizations"
	@echo "  help     - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make           # Build and sign"
	@echo "  make test      # Build, sign, and test"
	@echo "  make release   # Build optimized release version"
	@echo ""
	@echo "Executables will be created at:"
	@echo "  Debug:   $(SWIFT_DIR)/.build/debug/macosprox"
	@echo "  Release: $(SWIFT_DIR)/.build/release/macosprox"