import json
import socket
import threading
import time
import logging
from typing import Dict, Any, Optional

try:
    from PyQt5 import QtCore
except ImportError:
    # Minimal fallback for headless unit testing without PyQt5 installed
    class _MockSignal:
        def __init__(self, *args):
            self._callbacks = []
        def connect(self, cb):
            self._callbacks.append(cb)
        def emit(self, *args):
            for cb in self._callbacks:
                try:
                    cb(*args)
                except Exception:
                    pass

    class _MockQObject:
        pass

    class QtCore:
        QObject = _MockQObject
        pyqtSignal = _MockSignal

logger = logging.getLogger("DiscoveryClient")


class DiscoveryListener(QtCore.QObject):
    """
    Asynchronous UDP Discovery Listener and Network Node Registry.
    Listens for passive broadcasts from ffmpeg-gui instances on port 59990/UDP,
    tracks node vitality (online <10s, offline 10-60s, expired >=60s),
    and dispatches active DISCOVER_QUERY packets across the LAN.
    """

    node_discovered = QtCore.pyqtSignal(dict)
    node_status_changed = QtCore.pyqtSignal(str, str)  # (node_id, status: "online" | "offline")
    node_expired = QtCore.pyqtSignal(str)  # (node_id)

    def __init__(
        self,
        port: int = 59990,
        offline_threshold: float = 10.0,
        expire_threshold: float = 60.0,
        parent: Optional[QtCore.QObject] = None
    ):
        super().__init__(parent) if parent else super().__init__()
        self.port = port
        self.offline_threshold = offline_threshold
        self.expire_threshold = expire_threshold

        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._stop_event = threading.Event()
        self._sock: Optional[socket.socket] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._timer_thread: Optional[threading.Thread] = None

    def get_nodes(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._nodes)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._nodes.get(node_id)

    def start(self) -> None:
        """Initialize the UDP socket and start listener + aging threads."""
        if self._running:
            return

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._sock.bind(('', self.port))
            self._sock.settimeout(1.0)
        except Exception as e:
            logger.error(f"Failed to bind discovery socket on port {self.port}: {e}")
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            return

        self._running = True
        self._stop_event.clear()

        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            name="DiscoveryListener-Worker",
            daemon=True
        )
        self._timer_thread = threading.Thread(
            target=self._timeout_loop,
            name="DiscoveryListener-TimeoutWatcher",
            daemon=True
        )

        self._listener_thread.start()
        self._timer_thread.start()
        logger.info(f"DiscoveryListener active on UDP port {self.port}")

    def stop(self) -> None:
        """Stop threads and close socket cleanly."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2.0)
        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=2.0)

        self._listener_thread = None
        self._timer_thread = None
        logger.info("DiscoveryListener stopped.")

    def send_query(self) -> None:
        """Broadcast an active discovery query across the local subnet."""
        if not self._sock:
            return
        query_payload = {
            "cmd": "DISCOVER_QUERY",
            "app": "ffmpeg-gui-scanner",
            "timestamp": time.time()
        }
        try:
            data = json.dumps(query_payload).encode("utf-8")
            self._sock.sendto(data, ("255.255.255.255", self.port))
            logger.debug(f"Broadcast DISCOVER_QUERY sent to 255.255.255.255:{self.port}")
        except Exception as e:
            logger.debug(f"Error broadcasting DISCOVER_QUERY: {e}")

    def process_packet(self, data: bytes, addr: tuple) -> Optional[Dict[str, Any]]:
        """
        Parse and validate an incoming UDP datagram.
        Returns parsed payload if valid and processed, None otherwise.
        """
        try:
            msg = json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return None

        if not isinstance(msg, dict):
            return None

        # Verify application identity
        if msg.get("app") != "ffmpeg-gui":
            return None

        node_id = msg.get("node_id")
        if not node_id or not isinstance(node_id, str):
            return None

        # Fix IP if node reported 127.0.0.1 but arrived from remote peer
        sender_ip = addr[0]
        reported_ip = msg.get("ip")
        if (not reported_ip or reported_ip.startswith("127.")) and not sender_ip.startswith("127."):
            msg["ip"] = sender_ip
            # Reconstruct web_url with real sender IP if needed
            http_port = msg.get("http_port", 8000)
            https_port = msg.get("https_port")
            if https_port:
                msg["web_url"] = f"https://{sender_ip}:{https_port}"
            else:
                msg["web_url"] = f"http://{sender_ip}:{http_port}"

        now = time.time()
        status_changed_to_online = False

        with self._lock:
            existing = self._nodes.get(node_id)
            if existing:
                prev_status = existing.get("status", "online")
                if prev_status == "offline":
                    status_changed_to_online = True
                existing["data"] = msg
                existing["last_seen"] = now
                existing["status"] = "online"
            else:
                self._nodes[node_id] = {
                    "data": msg,
                    "last_seen": now,
                    "status": "online"
                }

        if status_changed_to_online:
            self.node_status_changed.emit(node_id, "online")

        self.node_discovered.emit(msg)
        return msg

    def check_timeouts(self, current_time: Optional[float] = None) -> None:
        """
        Evaluate time since last beacon packet for all registered nodes.
        Transition:
          online -> offline when age >= offline_threshold (10s)
          offline -> expired (removal) when age >= expire_threshold (60s)
        """
        now = current_time if current_time is not None else time.time()
        expired_ids = []
        offline_ids = []

        with self._lock:
            for node_id, record in list(self._nodes.items()):
                age = now - record["last_seen"]
                if age >= self.expire_threshold:
                    expired_ids.append(node_id)
                    del self._nodes[node_id]
                elif age >= self.offline_threshold:
                    if record.get("status") == "online":
                        record["status"] = "offline"
                        offline_ids.append(node_id)

        for nid in offline_ids:
            logger.info(f"Node {nid} transitioned to OFFLINE (beacon timeout)")
            self.node_status_changed.emit(nid, "offline")

        for nid in expired_ids:
            logger.info(f"Node {nid} EXPIRED (removed after 60s without beacon)")
            self.node_expired.emit(nid)

    def _listen_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._sock:
                break
            try:
                data, addr = self._sock.recvfrom(4096)
                if data:
                    self.process_packet(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self._stop_event.is_set():
                    break
                logger.debug(f"Socket receive error: {e}")
                time.sleep(0.2)

    def _timeout_loop(self) -> None:
        while not self._stop_event.is_set():
            self.check_timeouts()
            # Check every second
            elapsed = 0.0
            while elapsed < 1.0 and not self._stop_event.is_set():
                time.sleep(0.2)
                elapsed += 0.2
