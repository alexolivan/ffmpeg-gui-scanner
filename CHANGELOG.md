# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-23

### Added
- **LAN UDP Discovery Engine (`discovery_client.py`)**:
  - Passive listener on port `59990/udp` receiving broadcast heartbeats from active `ffmpeg-gui` nodes.
  - Active broadcast querying (`{"cmd": "DISCOVER_QUERY"}`) for instant node discovery upon startup and manual scan.
  - Primary-keyed indexing by immutable `node_id` (derived from machine-id) preventing duplicates across DHCP renewals and shared hostnames.
  - Reactive vitality state machine: 🟢 Online (<10s), 🔴 Offline (10–60s), auto-recovery on new packet, and ghost expiration cleanup (>=60s).
- **Studio Broadcast Dark UI (`app_window.py`)**:
  - Dark-themed table view reporting status, node name, alias, IP, HTTP/HTTPS ports, system version, streams telemetry, and 1-click web GUI launch.
  - Real-time search filter by name, alias, or IP address.
  - Configurable auto-scan timer (5s interval).
  - Version indicator badge (`v1.0.0`) in the header banner.
- **Multilingual Support & Desktop Auto-Detection (`i18n.py`)**:
  - Complete translations for English, Spanish, and Catalan.
  - Automatic detection of host desktop environment language on startup.
  - In-app dynamic language switcher with instantaneous UI retranslation.
- **Multi-Platform Automated Builds (`.github/workflows/build-binaries.yml`)**:
  - Automated GitHub Actions matrix generating standalone executables for Windows (`.exe`), macOS, and Linux.
  - Automatic release publishing upon version tags (`v*`).
