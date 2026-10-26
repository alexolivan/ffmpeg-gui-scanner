#!/bin/bash
set -e

echo "=== Building ffmpeg-gui-scanner for Linux ==="

# Check pyinstaller
if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "Installing PyInstaller..."
    pip install --break-system-packages pyinstaller 2>/dev/null || pip install pyinstaller
fi

echo "Running PyInstaller..."
pyinstaller --noconfirm --onefile --windowed --paths src --icon assets/icon.png --add-data "assets:assets" --name ffmpeg-gui-scanner main.py

echo "Build complete! Executable is at dist/ffmpeg-gui-scanner"
