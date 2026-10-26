import unittest
import os
import sys

# Ensure offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from unittest.mock import patch, MagicMock
from PyQt5 import QtWidgets, QtCore
from discovery_client import DiscoveryListener
from app_window import ScannerMainWindow, open_browser
from i18n import detect_system_language, translate

# Singleton QApplication for test suite
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


class TestAppWindow(unittest.TestCase):
    def setUp(self):
        self.listener = DiscoveryListener(port=59997)
        self.window = ScannerMainWindow(self.listener, initial_lang="en")

    def tearDown(self):
        self.window.close()
        self.listener.stop()

    def test_window_initial_state(self):
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertIn("Nodes: 0", self.window.lbl_stats.text())

    def test_on_node_discovered_adds_and_updates_row(self):
        sample_node = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "window-test-uuid-01",
            "node_name": "Studio Main Ingest",
            "node_alias": "INGEST-1",
            "ip": "192.168.1.80",
            "http_port": 8000,
            "https_port": 8443,
            "web_url": "https://192.168.1.80:8443",
            "version": "2.50.0",
            "running_services": 4,
            "active_streams": 3
        }

        # 1. Discovered
        self.window.on_node_discovered(sample_node)
        self.assertEqual(self.window.table.rowCount(), 1)
        self.assertIn("1 online", self.window.lbl_stats.text())

        name_item = self.window.table.item(0, ScannerMainWindow.COL_NAME)
        self.assertEqual(name_item.text(), "Studio Main Ingest")

        alias_item = self.window.table.item(0, ScannerMainWindow.COL_ALIAS)
        self.assertEqual(alias_item.text(), "INGEST-1")

        ip_item = self.window.table.item(0, ScannerMainWindow.COL_IP)
        self.assertEqual(ip_item.text(), "192.168.1.80")

        # 2. Status change to offline
        self.window.on_node_status_changed("window-test-uuid-01", "offline")
        status_item = self.window.table.item(0, ScannerMainWindow.COL_STATUS)
        self.assertIn("Offline", status_item.text())
        self.assertIn("0 online", self.window.lbl_stats.text())

        # 3. Reactive recovery back to online
        self.window.on_node_status_changed("window-test-uuid-01", "online")
        status_item = self.window.table.item(0, ScannerMainWindow.COL_STATUS)
        self.assertIn("Online", status_item.text())
        self.assertIn("1 online", self.window.lbl_stats.text())

        # 4. Expiration / removal
        self.window.on_node_expired("window-test-uuid-01")
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertIn("Nodes: 0", self.window.lbl_stats.text())

    def test_filter_rows(self):
        node1 = {"node_id": "n1", "node_name": "Encoder Alpha", "node_alias": "ENC-A", "ip": "192.168.1.10"}
        node2 = {"node_id": "n2", "node_name": "Mixer Beta", "node_alias": "MIX-B", "ip": "192.168.1.20"}

        self.window.on_node_discovered(node1)
        self.window.on_node_discovered(node2)
        self.assertEqual(self.window.table.rowCount(), 2)

        # Filter for "alpha"
        self.window._filter_rows("alpha")
        self.assertFalse(self.window.table.isRowHidden(0))
        self.assertTrue(self.window.table.isRowHidden(1))

        # Reset filter
        self.window._filter_rows("")
        self.assertFalse(self.window.table.isRowHidden(0))
        self.assertFalse(self.window.table.isRowHidden(1))

    def test_language_switching(self):
        # Switch to Spanish
        idx_es = self.window.combo_lang.findData("es")
        self.window.combo_lang.setCurrentIndex(idx_es)
        self.assertEqual(self.window._current_lang, "es")
        self.assertIn("Escáner", self.window.title_label.text())
        self.assertEqual(self.window.btn_scan.text(), "🔍 Escanear LAN")

        # Switch to Catalan
        idx_ca = self.window.combo_lang.findData("ca")
        self.window.combo_lang.setCurrentIndex(idx_ca)
        self.assertEqual(self.window._current_lang, "ca")
        self.assertIn("Escàner", self.window.title_label.text())
        self.assertEqual(self.window.btn_scan.text(), "🔍 Escanejar LAN")

    def test_button_persistence_across_beacons_and_click(self):
        sample_node = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "btn-test-01",
            "node_name": "Encoder Beta",
            "ip": "192.168.1.99",
            "http_port": 8000,
            "web_url": "http://192.168.1.99:8000",
            "running_services": 1,
            "active_streams": 1
        }
        self.window.on_node_discovered(sample_node)
        btn1 = self.window.table.cellWidget(0, ScannerMainWindow.COL_ACTION)
        self.assertIsNotNone(btn1)

        # Subsequent beacon for same node with updated stream count
        sample_node["active_streams"] = 2
        self.window.on_node_discovered(sample_node)
        btn2 = self.window.table.cellWidget(0, ScannerMainWindow.COL_ACTION)
        # Button instance MUST be preserved (not recreated)
        self.assertIs(btn1, btn2)

        # Streams column must be updated
        streams_item = self.window.table.item(0, ScannerMainWindow.COL_STREAMS)
        self.assertIn("2 streams", streams_item.text())

        # Clicking the button must trigger open_browser
        with patch("app_window.open_browser") as mock_open:
            btn1.click()
            mock_open.assert_called_once_with("http://192.168.1.99:8000")

    def test_open_browser_cleans_pyinstaller_environment(self):
        fake_env = {
            "LD_LIBRARY_PATH": "/tmp/_MEI12345:/usr/lib",
            "LD_LIBRARY_PATH_ORIG": "/usr/local/lib",
            "DYLD_LIBRARY_PATH": "/tmp/_MEI12345",
        }
        with patch.dict(os.environ, fake_env, clear=True):
            with patch("PyQt5.QtGui.QDesktopServices.openUrl", return_value=True) as mock_qdesktop:
                res = open_browser("http://192.168.1.50:8000")
                self.assertTrue(res)
                mock_qdesktop.assert_called_once()
                # Verify that environment in current process was restored after call
                self.assertEqual(os.environ.get("LD_LIBRARY_PATH"), "/tmp/_MEI12345:/usr/lib")


if __name__ == "__main__":
    unittest.main()
