# ffmpeg-gui-scanner

A lightweight, dark-themed desktop utility built with PyQt5 to discover and connect to `ffmpeg-gui` appliances running across local broadcast networks.

## Features

- **Automatic LAN Discovery**: Passively receives UDP beacons emitted on port `59990/udp` by active `ffmpeg-gui` instances.
- **Immediate Active Scan**: Dispatches broadcast `DISCOVER_QUERY` packets across `255.255.255.255:59990` for instant node discovery without waiting for heartbeat cycles.
- **Robust Machine Tracking**: Primary-keyed by unique `node_id` (derived from `/etc/machine-id`), preventing duplicate or ghost rows when appliances obtain new DHCP leases or share hostnames.
- **Reactive Vitality States**:
  - 🟢 **Online**: Appliance beacon received within the last 10 seconds.
  - 🔴 **Offline**: Appliance has been silent for 10–60 seconds (disabled, updating, or disconnected).
  - 🗑️ **Expired**: Gracefully removes ghost entries after 60 seconds of continuous silence.
  - **Auto-Recovery**: Instantly returns to 🟢 Online state as soon as a new packet is observed.
- **One-Click Launch**: Direct `Open Web GUI` action to launch the appliance dashboard in the system default browser (HTTP or HTTPS).
- **Search & Filter**: Real-time filtering by node name, alias, or IP address.
- **Multilingual Support**: Fully aligned with `ffmpeg-gui` with support for English, Spanish, and Catalan. Automatically detects system desktop language with instant in-app language switcher.

## Installation & Requirements

- Python 3.8+
- PyQt5 >= 5.15.0

```bash
git clone https://github.com/alexolivan/ffmpeg-gui-scanner.git
cd ffmpeg-gui-scanner
pip install -r requirements.txt
```

On Debian/Ubuntu systems, PyQt5 can also be installed via apt:
```bash
sudo apt install python3-pyqt5
```

## Usage

Launch the GUI application:
```bash
python3 main.py
```

### Optional Command-Line Arguments

```
usage: main.py [-h] [--port PORT] [--offline-threshold OFFLINE_THRESHOLD]
               [--expire-threshold EXPIRE_THRESHOLD] [-v]

options:
  --port PORT           UDP discovery port (default: 59990)
  --offline-threshold S Seconds before marking node offline (default: 10.0)
  --expire-threshold S  Seconds before removing silent node (default: 60.0)
  -v, --verbose         Enable verbose debug logging
```

## Running Tests

Execute the unit test suite:
```bash
python3 -m unittest discover tests
```

## License

GPLv3 / Apache 2.0 (consistent with the ffmpeg-gui ecosystem).

## Precompiled Binaries (Windows, macOS, Linux)

Automated standalone executables are compiled on every release via GitHub Actions:
- **Windows**: `ffmpeg-gui-scanner-windows-x64.exe` (standalone `.exe`, no Python installation required)
- **macOS**: `ffmpeg-gui-scanner-macos` (Apple Silicon & Intel)
- **Linux**: `ffmpeg-gui-scanner-linux-x64` (standalone executable)

Download the latest precompiled executable from the [Releases](https://github.com/alexolivan/ffmpeg-gui-scanner/releases) tab.
