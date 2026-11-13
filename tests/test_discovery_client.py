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

    def test_multi_nic_subnet_match_picks_matching_subnet(self):
        import ipaddress
        local_subnets = [{
            "ip": "192.168.100.224",
            "netmask": "255.255.255.0",
            "network": ipaddress.IPv4Network("192.168.100.0/24"),
            "broadcast": "192.168.100.255",
            "iface": "eth0",
            "is_link_local": False,
        }]
        beacon = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "test3-uuid",
            "node_name": "test3",
            "ip": "192.168.5.217",
            "ips": [
                {"ip": "192.168.5.217", "netmask": "255.255.255.0", "iface": "eth0", "mac": "aa:bb:cc:00:00:01", "default": True},
                {"ip": "192.168.100.221", "netmask": "255.255.255.0", "iface": "eth1", "mac": "aa:bb:cc:00:00:02", "default": False},
            ],
            "http_port": 8000,
            "https_port": 8443,
            "web_url": "https://192.168.5.217:8443",
        }
        raw = json.dumps(beacon).encode("utf-8")
        with patch("discovery_client.get_local_subnets", return_value=local_subnets):
            res = self.listener.process_packet(raw, ("192.168.100.221", 59990))

        self.assertEqual(res["ip"], "192.168.100.221")
        self.assertEqual(res["web_url"], "https://192.168.100.221:8443")
        self.assertEqual(len(res["candidates"]), 2)

    def test_multi_nic_anti_flapping_when_scanner_also_dual_homed(self):
        import ipaddress
        local_subnets = [
            {
                "ip": "192.168.5.10",
                "netmask": "255.255.255.0",
                "network": ipaddress.IPv4Network("192.168.5.0/24"),
                "broadcast": "192.168.5.255",
                "iface": "wlan0",
                "is_link_local": False,
            },
            {
                "ip": "192.168.100.224",
                "netmask": "255.255.255.0",
                "network": ipaddress.IPv4Network("192.168.100.0/24"),
                "broadcast": "192.168.100.255",
                "iface": "eth0",
                "is_link_local": False,
            },
        ]
        beacon = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "test3-dual",
            "node_name": "test3",
            "ip": "192.168.5.217",
            "ips": [
                {"ip": "192.168.5.217", "netmask": "255.255.255.0", "iface": "eth0", "mac": "aa:bb:cc:00:00:01", "default": True},
                {"ip": "192.168.100.221", "netmask": "255.255.255.0", "iface": "eth1", "mac": "aa:bb:cc:00:00:02", "default": False},
            ],
            "http_port": 8000,
        }
        raw = json.dumps(beacon).encode("utf-8")
        with patch("discovery_client.get_local_subnets", return_value=local_subnets):
            r1 = self.listener.process_packet(raw, ("192.168.5.217", 59990))
            r2 = self.listener.process_packet(raw, ("192.168.100.221", 59990))
            r3 = self.listener.process_packet(raw, ("192.168.5.217", 59990))

        self.assertEqual(r1["ip"], "192.168.100.221")
        self.assertEqual(r2["ip"], "192.168.100.221")
        self.assertEqual(r3["ip"], "192.168.100.221")

    def test_legacy_beacon_fallback_to_sender_ip_in_subnet(self):
        import ipaddress
        local_subnets = [{
            "ip": "192.168.100.224",
            "netmask": "255.255.255.0",
            "network": ipaddress.IPv4Network("192.168.100.0/24"),
            "broadcast": "192.168.100.255",
            "iface": "eth0",
            "is_link_local": False,
        }]
        legacy_beacon = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "legacy-node",
            "node_name": "Legacy Node",
            "ip": "192.168.5.217",
            "http_port": 8000,
            "https_port": None,
            "web_url": "http://192.168.5.217:8000",
        }
        raw = json.dumps(legacy_beacon).encode("utf-8")
        with patch("discovery_client.get_local_subnets", return_value=local_subnets):
            res = self.listener.process_packet(raw, ("192.168.100.221", 59990))

        self.assertEqual(res["ip"], "192.168.100.221")
        self.assertEqual(res["web_url"], "http://192.168.100.221:8000")

    def test_set_preferred_ip_pins_and_unpins(self):
        import ipaddress
        local_subnets = [{
            "ip": "192.168.100.224",
            "netmask": "255.255.255.0",
            "network": ipaddress.IPv4Network("192.168.100.0/24"),
            "broadcast": "192.168.100.255",
            "iface": "eth0",
            "is_link_local": False,
        }]
        beacon = {
            "app": "ffmpeg-gui",
            "protocol_version": 1,
            "node_id": "pin-node",
            "node_name": "Pin Node",
            "ip": "192.168.5.217",
            "ips": [
                {"ip": "192.168.5.217", "netmask": "255.255.255.0", "iface": "eth0", "default": True},
                {"ip": "192.168.100.221", "netmask": "255.255.255.0", "iface": "eth1", "default": False},
            ],
            "http_port": 8000,
        }
        raw = json.dumps(beacon).encode("utf-8")
        with patch("discovery_client.get_local_subnets", return_value=local_subnets):
            r1 = self.listener.process_packet(raw, ("192.168.100.221", 59990))
            self.assertEqual(r1["ip"], "192.168.100.221")
            self.assertFalse(r1["is_pinned"])

            pinned = self.listener.set_preferred_ip("pin-node", "192.168.5.217")
            self.assertEqual(pinned["ip"], "192.168.5.217")
            self.assertTrue(pinned["is_pinned"])

            r2 = self.listener.process_packet(raw, ("192.168.100.221", 59990))
            self.assertEqual(r2["ip"], "192.168.5.217")
            self.assertTrue(r2["is_pinned"])

            unpinned = self.listener.set_preferred_ip("pin-node", None)
            self.assertEqual(unpinned["ip"], "192.168.100.221")
            self.assertFalse(unpinned["is_pinned"])

    def test_send_query_multi_subnet_broadcasts(self):
        import ipaddress
        mock_sock = MagicMock()
        self.listener._sock = mock_sock
        local_subnets = [{
            "ip": "192.168.100.224",
            "netmask": "255.255.255.0",
            "network": ipaddress.IPv4Network("192.168.100.0/24"),
            "broadcast": "192.168.100.255",
            "iface": "eth0",
            "is_link_local": False,
        }]
        with patch("discovery_client.get_local_subnets", return_value=local_subnets):
            self.listener.send_query()

        dests = [call.args[1] for call in mock_sock.sendto.call_args_list]
        self.assertEqual(dests, [("192.168.100.255", 59998), ("255.255.255.255", 59998)])


if __name__ == "__main__":
    unittest.main()
