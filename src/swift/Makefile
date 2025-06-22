# Makefile for macOS Prox Swift Implementation

.PHONY: build clean test help sign

# Default target
all: build sign

# Build the Swift package
build:
	@echo "🔨 Building macOS Prox Swift implementation..."
	swift build

# Build and sign with entitlements
sign: build
	@echo "🔐 Signing executable with entitlements..."
	codesign --force --sign - --entitlements Resources/entitlements.plist .build/debug/macosprox
	@echo "✅ Build and signing complete!"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	swift package clean
	rm -rf .build

# Run tests
test: sign
	@echo "🧪 Running basic functionality tests..."
	./.build/debug/macosprox check
	./.build/debug/macosprox list
	@echo "✅ Basic tests passed!"

# Development build (faster, no signing)
dev:
	@echo "🔨 Building for development (no signing)..."
	swift build

# Release build
release:
	@echo "🔨 Building for release..."
	swift build -c release
	codesign --force --sign - --entitlements Resources/entitlements.plist .build/release/macosprox
	@echo "✅ Release build complete!"

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