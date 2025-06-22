#!/bin/bash

# Build and Sign macOS Prox Swift Implementation
# This script builds the Swift executable and signs it with the necessary entitlements

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
ENTITLEMENTS_FILE="$PROJECT_DIR/Resources/entitlements.plist"
EXECUTABLE_PATH="$PROJECT_DIR/.build/debug/macosprox"

echo "🔨 Building macOS Prox Swift implementation..."

# Clean and build
#swift package clean
swift build

# Check if the executable was created
if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "❌ Build failed: executable not found at $EXECUTABLE_PATH"
    exit 1
fi

echo "✅ Build completed successfully"

# Check if entitlements file exists
if [ ! -f "$ENTITLEMENTS_FILE" ]; then
    echo "❌ Entitlements file not found at $ENTITLEMENTS_FILE"
    exit 1
fi

echo "🔐 Signing executable with entitlements..."

# Sign the executable with entitlements
# Note: This requires a valid code signing identity
# For development, we'll use ad-hoc signing (-)
codesign --force --sign - --entitlements "$ENTITLEMENTS_FILE" "$EXECUTABLE_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Code signing completed successfully"
else
    echo "❌ Code signing failed"
    exit 1
fi

echo "🔍 Verifying entitlements..."
codesign -d --entitlements - "$EXECUTABLE_PATH"

echo ""
echo "🎉 Build and signing complete!"
echo "Executable location: $EXECUTABLE_PATH"
echo ""
echo "You can now run:"
echo "  $EXECUTABLE_PATH check"
echo "  $EXECUTABLE_PATH create --name test-vm --cpu 2 --memory 4 --disk 20"
