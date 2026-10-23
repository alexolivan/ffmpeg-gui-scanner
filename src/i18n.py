import os
from typing import Dict, Any

try:
    from PyQt5 import QtCore
except ImportError:
    class QtCore:
        class QLocale:
            @staticmethod
            def system():
                class _SysLocale:
                    def name(self):
                        return "en_US"
                return _SysLocale()

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Español",
    "ca": "Català"
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "app_title": "FFmpeg GUI - LAN Appliance Scanner",
        "header_title": "📡 FFmpeg GUI Appliance Scanner",
        "header_subtitle": "Live auto-discovery of ffmpeg-gui broadcast nodes across the local subnet",
        "btn_scan": "🔍 Scan LAN",
        "search_placeholder": "Filter nodes by name, alias, or IP address...",
        "autoscan_label": "Auto-scan (5s)",
        "status_listening": "Listening for UDP beacons on port 59990...",
        "status_query_sent": "Broadcast DISCOVER_QUERY sent on 59990/UDP...",
        "col_status": "Status",
        "col_name": "Node Name",
        "col_alias": "Alias",
        "col_ip": "IP Address",
        "col_ports": "Ports",
        "col_version": "Version",
        "col_streams": "Streams",
        "col_action": "Access",
        "badge_online": " 🟢 Online",
        "badge_offline": " 🔴 Offline",
        "tooltip_online": "Appliance responding actively to LAN beacons (<10s)",
        "tooltip_offline": "Appliance silent for >10s (disabled, updating, or disconnected)",
        "btn_open_gui": "Open Web GUI ↗",
        "stats_format": "Nodes: {total} ({online} online)",
        "streams_format": "⚡ {active} streams / {services} svcs"
    },
    "es": {
        "app_title": "FFmpeg GUI - Escáner de Equipos LAN",
        "header_title": "📡 Escáner de Equipos FFmpeg GUI",
        "header_subtitle": "Auto-descubrimiento en tiempo real de nodos ffmpeg-gui en la subred local",
        "btn_scan": "🔍 Escanear LAN",
        "search_placeholder": "Filtrar nodos por nombre, alias o dirección IP...",
        "autoscan_label": "Auto-escaneo (5s)",
        "status_listening": "Escuchando balizas UDP en el puerto 59990...",
        "status_query_sent": "Petición DISCOVER_QUERY emitida en 59990/UDP...",
        "col_status": "Estado",
        "col_name": "Nombre de Nodo",
        "col_alias": "Alias",
        "col_ip": "Dirección IP",
        "col_ports": "Puertos",
        "col_version": "Versión",
        "col_streams": "Streams",
        "col_action": "Acceso",
        "badge_online": " 🟢 En línea",
        "badge_offline": " 🔴 Desconectado",
        "tooltip_online": "Equipo respondiendo activamente a balizas LAN (<10s)",
        "tooltip_offline": "Equipo en silencio >10s (desactivado, actualizando o desconectado)",
        "btn_open_gui": "Abrir Web GUI ↗",
        "stats_format": "Nodos: {total} ({online} en línea)",
        "streams_format": "⚡ {active} streams / {services} svcs"
    },
    "ca": {
        "app_title": "FFmpeg GUI - Escàner d'Equips LAN",
        "header_title": "📡 Escàner d'Equips FFmpeg GUI",
        "header_subtitle": "Auto-descoberta en temps real de nodes ffmpeg-gui a la subxarxa local",
        "btn_scan": "🔍 Escanejar LAN",
        "search_placeholder": "Filtrar nodes per nom, àlies o adreça IP...",
        "autoscan_label": "Auto-escaneig (5s)",
        "status_listening": "Escoltant balises UDP al port 59990...",
        "status_query_sent": "Petició DISCOVER_QUERY emesa a 59990/UDP...",
        "col_status": "Estat",
        "col_name": "Nom de Node",
        "col_alias": "Àlies",
        "col_ip": "Adreça IP",
        "col_ports": "Ports",
        "col_version": "Versió",
        "col_streams": "Streams",
        "col_action": "Accés",
        "badge_online": " 🟢 En línia",
        "badge_offline": " 🔴 Desconnectat",
        "tooltip_online": "Equip responent activament a balises LAN (<10s)",
        "tooltip_offline": "Equip en silenci >10s (desactivat, actualitzant o desconnectat)",
        "btn_open_gui": "Obrir Web GUI ↗",
        "stats_format": "Nodes: {total} ({online} en línia)",
        "streams_format": "⚡ {active} streams / {services} svcs"
    }
}


def detect_system_language() -> str:
    """
    Detect desktop desktop environment language.
    Checks environment variables (LC_ALL, LC_MESSAGES, LANG) then QLocale.
    Returns 'ca', 'es', or defaults to 'en'.
    """
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            lower = val.lower()
            if lower.startswith("ca"):
                return "ca"
            elif lower.startswith("es"):
                return "es"
            elif lower.startswith("en"):
                return "en"

    try:
        name = QtCore.QLocale.system().name().lower()
        if name.startswith("ca"):
            return "ca"
        elif name.startswith("es"):
            return "es"
    except Exception:
        pass

    return "en"


def translate(key: str, lang: str = "en", **kwargs) -> str:
    """Retrieve translated string with variable interpolation and English fallback."""
    cat = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    text = cat.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
