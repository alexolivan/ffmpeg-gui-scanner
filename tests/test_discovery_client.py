import unittest
from unittest.mock import MagicMock, patch
import json
import time
import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from discovery_client import DiscoveryListener


class TestDiscoveryClient(unittest.TestCase):
    def setUp(self):
        self.listener = DiscoveryListener(port=59998, offline_threshold=10.0, expire_threshold=60.0)

    def tearDown(self):
        self.listener.stop()

    def test_process_packet_valid(self):
        discovered_events = []
        self.listener.node_discovered.connect(lambda d: discovered_events.append(d))

        sample_beacon = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "test-node-uuid-001",
            "node_name": "Encoder Studio A",
            "node_alias": "ENC-01",
            "ip": "192.168.1.105",
            "http_port": 8000,
            "https_port": 8443,
            "web_url": "https://192.168.1.105:8443",
            "version": "2.50.0",
            "running_services": 3,
            "active_streams": 2
        }

        raw = json.dumps(sample_beacon).encode("utf-8")
        result = self.listener.process_packet(raw, ("192.168.1.105", 59990))

        self.assertIsNotNone(result)
        self.assertEqual(len(discovered_events), 1)
        self.assertEqual(discovered_events[0]["node_id"], "test-node-uuid-001")

        nodes = self.listener.get_nodes()
        self.assertIn("test-node-uuid-001", nodes)
        self.assertEqual(nodes["test-node-uuid-001"]["status"], "online")

    def test_process_packet_invalid_app(self):
        foreign_packet = {
            "app": "other-app",
            "node_id": "other-123"
        }
        raw = json.dumps(foreign_packet).encode("utf-8")
        result = self.listener.process_packet(raw, ("192.168.1.200", 59990))
        self.assertIsNone(result)
        self.assertEqual(len(self.listener.get_nodes()), 0)

    def test_process_packet_missing_node_id(self):
        bad_packet = {
            "app": "ffmpeg-gui",
            "node_name": "Ghost"
        }
        raw = json.dumps(bad_packet).encode("utf-8")
        result = self.listener.process_packet(raw, ("192.168.1.200", 59990))
        self.assertIsNone(result)
        self.assertEqual(len(self.listener.get_nodes()), 0)

    def test_timeout_transitions_and_recovery(self):
        status_changes = []
        expired_events = []
        self.listener.node_status_changed.connect(lambda nid, st: status_changes.append((nid, st)))
        self.listener.node_expired.connect(lambda nid: expired_events.append(nid))

        t0 = 1000.0
        sample_beacon = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "lifecycle-node-1",
            "node_name": "Test Node",
            "ip": "192.168.1.50",
            "http_port": 8000,
            "https_port": None,
            "web_url": "http://192.168.1.50:8000",
            "version": "2.50.0"
        }

        # 1. Packet arrives at t0
        with patch("time.time", return_value=t0):
            raw = json.dumps(sample_beacon).encode("utf-8")
            self.listener.process_packet(raw, ("192.168.1.50", 59990))

        self.assertEqual(self.listener.get_node("lifecycle-node-1")["status"], "online")

        # 2. Check timeouts at t0 + 5.0 (still under 10s)
        self.listener.check_timeouts(current_time=t0 + 5.0)
        self.assertEqual(self.listener.get_node("lifecycle-node-1")["status"], "online")
        self.assertEqual(len(status_changes), 0)

        # 3. Check timeouts at t0 + 11.0 (>= 10s -> offline)
        self.listener.check_timeouts(current_time=t0 + 11.0)
        self.assertEqual(self.listener.get_node("lifecycle-node-1")["status"], "offline")
        self.assertEqual(len(status_changes), 1)
        self.assertEqual(status_changes[-1], ("lifecycle-node-1", "offline"))

        # 4. New beacon packet arrives at t0 + 20.0 (reactive recovery to online!)
        with patch("time.time", return_value=t0 + 20.0):
            self.listener.process_packet(raw, ("192.168.1.50", 59990))

        self.assertEqual(self.listener.get_node("lifecycle-node-1")["status"], "online")
        self.assertEqual(len(status_changes), 2)
        self.assertEqual(status_changes[-1], ("lifecycle-node-1", "online"))

        # 5. Let it go silent until t0 + 85.0 (age = 65s > 60s expire threshold)
        self.listener.check_timeouts(current_time=t0 + 85.0)
        self.assertIsNone(self.listener.get_node("lifecycle-node-1"))
        self.assertEqual(len(expired_events), 1)
        self.assertEqual(expired_events[0], "lifecycle-node-1")

    def test_send_query(self):
        mock_sock = MagicMock()
        self.listener._sock = mock_sock
        self.listener.send_query()

        self.assertTrue(mock_sock.sendto.called)
        sent_data, dest = mock_sock.sendto.call_args[0]
        self.assertEqual(dest, ("255.255.255.255", 59998))
        parsed = json.loads(sent_data.decode("utf-8"))
        self.assertEqual(parsed["cmd"], "DISCOVER_QUERY")
        self.assertEqual(parsed["app"], "ffmpeg-gui-scanner")


if __name__ == "__main__":
    unittest.main()
