# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-26

### Added
- **Official Application Branding & Multi-Platform Icons (`assets/`)**:
  - Designed official studio radar antenna branding in brand lime green (`#a3e635`).
  - Added high-resolution `assets/icon.png`, multi-resolution Windows `assets/icon.ico`, and Apple icon `assets/icon.icns`.
  - Integrated runtime window icon loading in `main.py` and `ScannerMainWindow` for both local development and frozen PyInstaller bundles.
  - Set explicit `AppUserModelID` on Windows to ensure proper taskbar icon display and grouping.
- **Native macOS Application Bundle & DMG Packaging**:
  - Configured CI/CD matrix to package `dist/ffmpeg-gui-scanner.app` into a native `.dmg` disk image (`ffmpeg-gui-scanner-macos.dmg`) with `CFBundleDisplayName` and bundle identifier, ensuring zero Terminal console windows on launch.

### Fixed
- **Browser Launch Reliability in Standalone Binaries**:
  - Implemented `open_browser()` in `src/app_window.py` with environment cleaning (`LD_LIBRARY_PATH` / `DYLD_LIBRARY_PATH` restoration) to prevent PyInstaller bundled glibc/glib conflicts from crashing host browsers or `xdg-open`.
  - Added multi-tier fallback: native `QDesktopServices.openUrl`, platform-specific clean subprocesses (`xdg-open`, `open`, `os.startfile`), and `webbrowser.open`.
- **Action Button Stability & State Preservation in Node Table**:
  - Fixed action button churn where incoming beacons every 4s destroyed and recreated the `QPushButton` widget, preventing click race conditions and maintaining stable mouse hover states.
  - Retained real-time search filter state upon receiving newly discovered nodes.

