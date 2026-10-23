#!/usr/bin/env python3
import sys
import os
import signal
import argparse
import logging

from PyQt5 import QtWidgets, QtCore

# Add src to module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from discovery_client import DiscoveryListener
from app_window import ScannerMainWindow


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S"
    )


def main():
    parser = argparse.ArgumentParser(description="FFmpeg GUI LAN Appliance Scanner")
    parser.add_argument("--port", type=int, default=59990, help="UDP discovery port (default: 59990)")
    parser.add_argument("--offline-threshold", type=float, default=10.0, help="Seconds before marking node offline (default: 10.0)")
    parser.add_argument("--expire-threshold", type=float, default=60.0, help="Seconds before removing silent node (default: 60.0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Enable Ctrl+C handling in Qt event loop
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # High DPI scaling support
    if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("ffmpeg-gui-scanner")
    app.setApplicationDisplayName("FFmpeg GUI Scanner")

    listener = DiscoveryListener(
        port=args.port,
        offline_threshold=args.offline_threshold,
        expire_threshold=args.expire_threshold
    )
    listener.start()

    window = ScannerMainWindow(listener)
    window.show()

    # Trigger an immediate active broadcast query upon launch
    QtCore.QTimer.singleShot(200, listener.send_query)

    exit_code = app.exec_()
    listener.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
