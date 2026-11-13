import ipaddress
import re
from typing import Any, Dict, List, Optional

try:
    from PyQt5 import QtNetwork
except ImportError:
    QtNetwork = None

_IGNORED_IFACE_PREFIXES = (
    "lo",
    "docker",
    "veth",
    "virbr",
    "lxc",
    "lxd",
    "podman",
    "cni",
    "flannel",
    "kube",
    "calico",
    "tun",
    "tap",
    "wg",
    "tailscale",
    "zt",
    "vmnet",
    "vboxnet",
    "dummy",
    "ifb",
)
_DOCKER_BRIDGE_RE = re.compile(r"^br-[0-9a-f]{6,}$", re.IGNORECASE)


def is_virtual_or_ignored_iface(iface_name: str) -> bool:
    """Filter loopback, container, hypervisor, and tunnel virtual interfaces."""
    if not iface_name:
        return True
    lower = iface_name.lower()
    if lower == "lo" or lower.startswith(_IGNORED_IFACE_PREFIXES):
        return True
    if _DOCKER_BRIDGE_RE.match(lower):
        return True
    return False


def _parse_ipv4(raw_ip: Optional[str]) -> Optional[ipaddress.IPv4Address]:
    if not raw_ip or not isinstance(raw_ip, str):
        return None
    try:
        return ipaddress.IPv4Address(raw_ip.strip())
    except ValueError:
        return None


def _build_network(ip_str: str, netmask_str: Optional[str]) -> ipaddress.IPv4Interface:
    mask = netmask_str if netmask_str else "255.255.255.0"
    try:
        return ipaddress.IPv4Interface(f"{ip_str}/{mask}")
    except ValueError:
        return ipaddress.IPv4Interface(f"{ip_str}/255.255.255.0")


def build_web_url(
    ip: str,
    http_port: Optional[int] = 8000,
    https_port: Optional[int] = None,
) -> str:
    """Build canonical HTTP or HTTPS Web GUI URL for a given IP and ports."""
    if https_port:
        return f"https://{ip}:{https_port}"
    effective_http = http_port if http_port else 8000
    return f"http://{ip}:{effective_http}"


def get_local_subnets() -> List[Dict[str, Any]]:
    """
    Enumerate active, non-virtual local IPv4 subnets using PyQt5 QtNetwork.
    Returns an empty list when QtNetwork is unavailable (e.g. headless unit tests).
    """
    if QtNetwork is None:
        return []

    subnets: List[Dict[str, Any]] = []
    try:
        all_ifaces = QtNetwork.QNetworkInterface.allInterfaces()
    except Exception:
        return subnets

    for iface in all_ifaces:
        flags = iface.flags()
        is_up = bool(flags & QtNetwork.QNetworkInterface.IsUp)
        is_running = bool(flags & QtNetwork.QNetworkInterface.IsRunning)
        is_loopback = bool(flags & QtNetwork.QNetworkInterface.IsLoopBack)
        if not is_up or not is_running or is_loopback:
            continue

        raw_name = iface.name() or ""
        human_name = iface.humanReadableName() or raw_name
        if is_virtual_or_ignored_iface(raw_name) or is_virtual_or_ignored_iface(human_name):
            continue

        for entry in iface.addressEntries():
            q_ip = entry.ip()
            if q_ip.protocol() != QtNetwork.QAbstractSocket.IPv4Protocol:
                continue
            ip_obj = _parse_ipv4(q_ip.toString())
            if not ip_obj or ip_obj.is_loopback or ip_obj.is_unspecified or ip_obj.is_multicast:
                continue

            netmask_str = entry.netmask().toString() or "255.255.255.0"
            iface_net = _build_network(str(ip_obj), netmask_str)
            broadcast = (
                str(iface_net.network.broadcast_address)
                if iface_net.network.prefixlen < 32
                else None
            )
            subnets.append({
                "ip": str(ip_obj),
                "netmask": str(iface_net.netmask),
                "network": iface_net.network,
                "broadcast": broadcast,
                "iface": human_name,
                "is_link_local": ip_obj.is_link_local,
            })

    return subnets


def _match_local_subnet(
    ip_obj: ipaddress.IPv4Address,
    local_subnets: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    for sub in local_subnets:
        net = sub.get("network")
        if net is not None and ip_obj in net:
            return sub
    return None


def resolve_node_endpoints(
    msg: Dict[str, Any],
    sender_ip: str,
    local_subnets: List[Dict[str, Any]],
    preferred_ip: Optional[str] = None,
    current_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve all advertised/observed IP endpoints of a discovered node against local
    scanner subnets, returning a deterministic primary IP, web_url, and candidate list.
    """
    http_port = msg.get("http_port", 8000)
    https_port = msg.get("https_port")

    raw_ips = msg.get("ips")
    has_multi_nic_payload = isinstance(raw_ips, list) and len(raw_ips) > 0

    candidates: List[Dict[str, Any]] = []
    seen_ips = set()

    def _add_candidate(
        ip_str: Optional[str],
        netmask_str: Optional[str] = None,
        iface_name: str = "",
        mac: Optional[str] = None,
        is_default: bool = False,
    ) -> None:
        ip_obj = _parse_ipv4(ip_str)
        if not ip_obj or ip_obj.is_loopback or ip_obj.is_unspecified or ip_obj.is_multicast:
            return
        ip_clean = str(ip_obj)
        if ip_clean in seen_ips:
            return
        seen_ips.add(ip_clean)

        iface_net = _build_network(ip_clean, netmask_str)
        matched_sub = _match_local_subnet(ip_obj, local_subnets)
        candidates.append({
            "ip": ip_clean,
            "netmask": str(iface_net.netmask),
            "prefixlen": iface_net.network.prefixlen,
            "iface": iface_name or "-",
            "mac": mac,
            "default": bool(is_default),
            "same_subnet": matched_sub is not None,
            "local_iface": matched_sub.get("iface") if matched_sub else None,
            "is_link_local": ip_obj.is_link_local,
            "web_url": build_web_url(ip_clean, http_port, https_port),
        })

    if has_multi_nic_payload:
        for entry in raw_ips:
            if isinstance(entry, dict):
                _add_candidate(
                    entry.get("ip"),
                    entry.get("netmask"),
                    entry.get("iface") or "",
                    entry.get("mac"),
                    bool(entry.get("default", False)),
                )
        # Also include sender_ip if it wasn't listed (e.g. NAT/proxy or secondary alias)
        _add_candidate(sender_ip, None, "peer", None, False)
    else:
        _add_candidate(msg.get("ip"), None, "primary", None, True)
        _add_candidate(sender_ip, None, "peer", None, False)

    if not candidates:
        fallback_ip = msg.get("ip") or sender_ip or "127.0.0.1"
        fallback_url = msg.get("web_url") or build_web_url(fallback_ip, http_port, https_port)
        return {
            "selected_ip": fallback_ip,
            "selected_web_url": fallback_url,
            "candidates": [],
            "preferred_ip": None,
            "is_pinned": False,
        }

    # 1. Explicit user pin if still valid among current candidates
    selected: Optional[Dict[str, Any]] = None
    is_pinned = False
    if preferred_ip:
        for cand in candidates:
            if cand["ip"] == preferred_ip:
                selected = cand
                is_pinned = True
                break

    # 2. Deterministic auto-selection (anti-flapping)
    if selected is None:
        if has_multi_nic_payload:
            ranked = sorted(
                candidates,
                key=lambda c: (
                    not c["same_subnet"],
                    c["is_link_local"],
                    0 if (c["same_subnet"] and current_ip and c["ip"] == current_ip) else 1,
                    c["default"],
                    c["iface"],
                    c["ip"],
                ),
            )
        else:
            ranked = sorted(
                candidates,
                key=lambda c: (
                    not c["same_subnet"],
                    c["is_link_local"],
                    0 if c["ip"] == sender_ip else 1,
                    c["ip"],
                ),
            )
        selected = ranked[0]

    return {
        "selected_ip": selected["ip"],
        "selected_web_url": selected["web_url"],
        "candidates": candidates,
        "preferred_ip": preferred_ip if is_pinned else None,
        "is_pinned": is_pinned,
    }
