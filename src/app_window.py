import sys
import os
import subprocess
import webbrowser
import logging
from typing import Dict, Any, Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from discovery_client import DiscoveryListener
from i18n import detect_system_language, translate, SUPPORTED_LANGUAGES
from version import __version__

logger = logging.getLogger("ScannerWindow")


def open_browser(url: str) -> bool:
    """
    Open a web URL in the user's default browser safely.
    Handles PyInstaller LD_LIBRARY_PATH / DYLD_LIBRARY_PATH pollution that
    causes external browsers and xdg-open/gio to crash with symbol errors.
    """
    if not url:
        return False
    logger.info(f"Opening browser URL: {url}")

    # Clean environment copy to prevent PyInstaller library clashes
    clean_env = dict(os.environ)
    for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "LIBPATH", "SHLIB_PATH"):
        orig = f"{var}_ORIG"
        if orig in clean_env:
            clean_env[var] = clean_env[orig]
        else:
            clean_env.pop(var, None)

    # 1. Native QDesktopServices with cleaned environment
    # On Unix, QDesktopServices may invoke xdg-open / gio, so temporarily patch os.environ
    saved_env = {}
    for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        if var in os.environ:
            saved_env[var] = os.environ[var]
            if f"{var}_ORIG" in os.environ:
                os.environ[var] = os.environ[f"{var}_ORIG"]
            else:
                del os.environ[var]

    try:
        qurl = QtCore.QUrl(url)
        if QtGui.QDesktopServices.openUrl(qurl):
            return True
    except Exception as e:
        logger.debug(f"QDesktopServices.openUrl error: {e}")
    finally:
        for var, val in saved_env.items():
            os.environ[var] = val

    # 2. Platform-specific fallback subprocesses with cleaned environment
    try:
        if sys.platform.startswith("linux"):
            for launcher in ("xdg-open", "gio", "x-www-browser", "firefox", "chromium", "google-chrome"):
                if any(os.access(os.path.join(p, launcher), os.X_OK) for p in os.environ.get("PATH", "").split(os.pathsep)):
                    cmd = [launcher, "open", url] if launcher == "gio" else [launcher, url]
                    subprocess.Popen(cmd, env=clean_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url], env=clean_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif sys.platform in ("win32", "cygwin"):
            if hasattr(os, "startfile"):
                os.startfile(url)
                return True
    except Exception as e:
        logger.debug(f"Subprocess launcher fallback failed: {e}")

    # 3. Final fallback: standard webbrowser module
    try:
        return webbrowser.open(url)
    except Exception as e:
        logger.error(f"Failed to open browser URL {url}: {e}")
        return False

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #121316;
    color: #f3f4f6;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QTableWidget {
    background-color: #18191e;
    alternate-background-color: #1e2026;
    border: 1px solid #282b33;
    border-radius: 8px;
    gridline-color: #282b33;
    selection-background-color: #2d3340;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #22252c;
}

QHeaderView::section {
    background-color: #15161b;
    color: #9ca3af;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #282b33;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QPushButton {
    background-color: #22252b;
    color: #f3f4f6;
    border: 1px solid #323640;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2b3038;
    border-color: #a3e635;
    color: #a3e635;
}

QPushButton:pressed {
    background-color: #191c21;
}

QPushButton#btnScan {
    background-color: #84cc16;
    color: #121316;
    border: 1px solid #a3e635;
    font-weight: 700;
    padding: 6px 16px;
}

QPushButton#btnScan:hover {
    background-color: #a3e635;
    color: #000000;
}

QPushButton#btnOpenGui {
    background-color: rgba(163, 230, 53, 0.12);
    color: #a3e635;
    border: 1px solid rgba(163, 230, 53, 0.35);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    min-height: 26px;
    margin: 2px 4px;
}

QPushButton#btnOpenGui:hover {
    background-color: #a3e635;
    color: #121316;
}

QLineEdit {
    background-color: #18191e;
    color: #f3f4f6;
    border: 1px solid #282b33;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border: 1px solid #a3e635;
}

QComboBox {
    background-color: #18191e;
    color: #f3f4f6;
    border: 1px solid #282b33;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
}

QComboBox:hover {
    border-color: #a3e635;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #18191e;
    color: #f3f4f6;
    selection-background-color: #282b33;
    selection-color: #a3e635;
    border: 1px solid #323640;
    padding: 4px;
}

QCheckBox {
    spacing: 8px;
    color: #9ca3af;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #323640;
    background-color: #18191e;
}

QCheckBox::indicator:checked {
    background-color: #84cc16;
    border-color: #a3e635;
}

QStatusBar {
    background-color: #15161b;
    color: #9ca3af;
    border-top: 1px solid #282b33;
    font-size: 11px;
}
"""


class ScannerMainWindow(QtWidgets.QMainWindow):
    COL_STATUS = 0
    COL_NAME = 1
    COL_ALIAS = 2
    COL_IP = 3
    COL_PORTS = 4
    COL_VERSION = 5
    COL_STREAMS = 6
    COL_ACTION = 7

    def __init__(self, listener: DiscoveryListener, initial_lang: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.listener = listener
        self._current_lang = initial_lang or detect_system_language()
        self._node_rows: Dict[str, int] = {}  # node_id -> row_index

        self.resize(1050, 580)
        self.setMinimumSize(820, 420)
        self.setStyleSheet(DARK_STYLE)

        app_icon = QtWidgets.QApplication.windowIcon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        else:
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            for p in [os.path.join(base_dir, "assets", "icon.png"), os.path.join(base_dir, "assets", "icon.ico")]:
                if os.path.exists(p):
                    self.setWindowIcon(QtGui.QIcon(p))
                    break

        self._setup_ui()
        self._retranslate_ui()
        self._connect_signals()

        # Background auto-scan timer (5 seconds)
        self._auto_scan_timer = QtCore.QTimer(self)
        self._auto_scan_timer.setInterval(5000)
        self._auto_scan_timer.timeout.connect(self._on_auto_scan_tick)
        self._auto_scan_timer.start()

    def t(self, key: str, **kwargs) -> str:
        return translate(key, lang=self._current_lang, **kwargs)

    def _setup_ui(self):
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header bar
        header_layout = QtWidgets.QHBoxLayout()
        header_title_layout = QtWidgets.QVBoxLayout()
        header_title_layout.setSpacing(2)

        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.title_label = QtWidgets.QLabel(self)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #f3f4f6;")

        self.version_badge = QtWidgets.QLabel(f"v{__version__}", self)
        self.version_badge.setStyleSheet(
            "font-size: 11px; font-weight: 700; font-family: monospace; "
            "color: #a3e635; background-color: rgba(163, 230, 53, 0.12); "
            "border: 1px solid rgba(163, 230, 53, 0.3); border-radius: 4px; padding: 2px 6px;"
        )

        title_row.addWidget(self.title_label)
        title_row.addWidget(self.version_badge)

        self.subtitle_label = QtWidgets.QLabel(self)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #9ca3af;")

        header_title_layout.addLayout(title_row)
        header_title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(header_title_layout)
        header_layout.addStretch()

        # Language switcher combo
        self.combo_lang = QtWidgets.QComboBox(self)
        for code, label in SUPPORTED_LANGUAGES.items():
            self.combo_lang.addItem(label, code)
        # Select active language
        idx = self.combo_lang.findData(self._current_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(self._on_language_changed)
        header_layout.addWidget(self.combo_lang)

        # Scan LAN Button
        self.btn_scan = QtWidgets.QPushButton(self)
        self.btn_scan.setObjectName("btnScan")
        self.btn_scan.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_scan.clicked.connect(self.scan_now)
        header_layout.addWidget(self.btn_scan)

        main_layout.addLayout(header_layout)

        # Filter and Controls Bar
        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.setSpacing(12)

        self.search_input = QtWidgets.QLineEdit(self)
        self.search_input.textChanged.connect(self._filter_rows)
        controls_layout.addWidget(self.search_input, stretch=1)

        self.cb_autoscan = QtWidgets.QCheckBox(self)
        self.cb_autoscan.setChecked(True)
        self.cb_autoscan.toggled.connect(self._toggle_autoscan)
        controls_layout.addWidget(self.cb_autoscan)

        self.lbl_stats = QtWidgets.QLabel(self)
        self.lbl_stats.setStyleSheet("color: #a3e635; font-weight: 700; font-size: 12px; padding: 0 4px;")
        controls_layout.addWidget(self.lbl_stats)

        main_layout.addLayout(controls_layout)

        # Nodes Table
        self.table = QtWidgets.QTableWidget(0, 8, self)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)  # Generous height preventing button vertical clipping
        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_STATUS, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_NAME, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_ALIAS, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_IP, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_PORTS, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_VERSION, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_STREAMS, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_ACTION, QtWidgets.QHeaderView.Fixed)
        self.table.setColumnWidth(self.COL_ACTION, 155)  # Fixed width ensuring "Open Web GUI ↗" fits comfortably

        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        main_layout.addWidget(self.table)

        # Status Bar
        self.status_bar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _retranslate_ui(self):
        """Update all user-visible text in current language."""
        self.setWindowTitle(self.t("app_title"))
        self.title_label.setText(self.t("header_title"))
        self.subtitle_label.setText(self.t("header_subtitle"))
        self.btn_scan.setText(self.t("btn_scan"))
        self.search_input.setPlaceholderText(self.t("search_placeholder"))
        self.cb_autoscan.setText(self.t("autoscan_label"))

        headers = [
            self.t("col_status"),
            self.t("col_name"),
            self.t("col_alias"),
            self.t("col_ip"),
            self.t("col_ports"),
            self.t("col_version"),
            self.t("col_streams"),
            self.t("col_action")
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.status_bar.showMessage(self.t("status_listening"))

        # Retranslate existing table rows
        for r in range(self.table.rowCount()):
            status_item = self.table.item(r, self.COL_STATUS)
            if status_item:
                is_online = ("Online" in status_item.text() or "línea" in status_item.text().lower() or "línia" in status_item.text().lower())
                self._apply_status_styling(status_item, "online" if is_online else "offline")

            btn = self.table.cellWidget(r, self.COL_ACTION)
            if isinstance(btn, QtWidgets.QPushButton):
                btn.setText(self.t("btn_open_gui"))

        self._update_stats()

    def _on_language_changed(self, index: int):
        lang_code = self.combo_lang.itemData(index)
        if lang_code and lang_code != self._current_lang:
            self._current_lang = lang_code
            self._retranslate_ui()

    def _connect_signals(self):
        self.listener.node_discovered.connect(self.on_node_discovered)
        self.listener.node_status_changed.connect(self.on_node_status_changed)
        self.listener.node_expired.connect(self.on_node_expired)

    def scan_now(self):
        """Send broadcast discovery query."""
        self.listener.send_query()
        self.status_bar.showMessage(self.t("status_query_sent"), 3000)

    def _on_auto_scan_tick(self):
        if self.cb_autoscan.isChecked():
            self.listener.send_query()

    def _toggle_autoscan(self, checked: bool):
        if checked:
            self._auto_scan_timer.start()
        else:
            self._auto_scan_timer.stop()

    def on_node_discovered(self, data: Dict[str, Any]):
        node_id = data.get("node_id")
        if not node_id:
            return

        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        row = self._find_row_by_node_id(node_id)
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._node_rows[node_id] = row

        self._populate_row(row, data, status="online")

        self.table.setSortingEnabled(sorting_enabled)
        self._rebuild_row_map()
        self._update_stats()
        if self.search_input.text():
            self._filter_rows(self.search_input.text())

    def on_node_status_changed(self, node_id: str, new_status: str):
        row = self._find_row_by_node_id(node_id)
        if row is not None:
            self._update_status_item(row, new_status)
            self._update_stats()

    def on_node_expired(self, node_id: str):
        row = self._find_row_by_node_id(node_id)
        if row is not None:
            self.table.removeRow(row)
            self._rebuild_row_map()
            self._update_stats()

    def _find_row_by_node_id(self, node_id: str) -> Optional[int]:
        for r in range(self.table.rowCount()):
            item = self.table.item(r, self.COL_STATUS)
            if item and item.data(QtCore.Qt.UserRole) == node_id:
                return r
        return None

    def _rebuild_row_map(self):
        self._node_rows.clear()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, self.COL_STATUS)
            if item:
                nid = item.data(QtCore.Qt.UserRole)
                if nid:
                    self._node_rows[nid] = r

    def _populate_row(self, row: int, data: Dict[str, Any], status: str = "online"):
        node_id = data.get("node_id", "")
        node_name = data.get("node_name", "Unknown Node")
        node_alias = data.get("node_alias", "-")
        ip = data.get("ip", "127.0.0.1")
        http_port = data.get("http_port", 8000)
        https_port = data.get("https_port")
        version = data.get("version", "unknown")
        web_url = data.get("web_url") or f"http://{ip}:{http_port}"
        running_services = data.get("running_services", 0)
        active_streams = data.get("active_streams", 0)

        # 1. Status Column
        status_item = self.table.item(row, self.COL_STATUS)
        if not status_item:
            status_item = QtWidgets.QTableWidgetItem()
            self.table.setItem(row, self.COL_STATUS, status_item)
        status_item.setData(QtCore.Qt.UserRole, node_id)
        status_item.setData(QtCore.Qt.UserRole + 1, web_url)
        self._apply_status_styling(status_item, status)

        # 2. Name Column
        name_item = self.table.item(row, self.COL_NAME)
        if not name_item:
            name_item = QtWidgets.QTableWidgetItem()
            name_item.setFont(QtGui.QFont("", 11, QtGui.QFont.Bold))
            self.table.setItem(row, self.COL_NAME, name_item)
        name_item.setText(node_name)
        name_item.setData(QtCore.Qt.UserRole + 1, web_url)

        # 3. Alias Column
        alias_item = self.table.item(row, self.COL_ALIAS)
        if not alias_item:
            alias_item = QtWidgets.QTableWidgetItem()
            alias_item.setTextAlignment(QtCore.Qt.AlignCenter)
            alias_item.setForeground(QtGui.QBrush(QtGui.QColor("#a3e635")))
            font = QtGui.QFont("Monospace", 10)
            font.setBold(True)
            alias_item.setFont(font)
            self.table.setItem(row, self.COL_ALIAS, alias_item)
        alias_item.setText(node_alias)

        # 4. IP Column
        ip_item = self.table.item(row, self.COL_IP)
        if not ip_item:
            ip_item = QtWidgets.QTableWidgetItem()
            ip_item.setTextAlignment(QtCore.Qt.AlignCenter)
            ip_item.setFont(QtGui.QFont("Monospace", 10))
            self.table.setItem(row, self.COL_IP, ip_item)
        ip_item.setText(ip)

        # 5. Ports Column
        ports_str = f"HTTP:{http_port}"
        if https_port:
            ports_str += f" | HTTPS:{https_port}"
        ports_item = self.table.item(row, self.COL_PORTS)
        if not ports_item:
            ports_item = QtWidgets.QTableWidgetItem()
            ports_item.setTextAlignment(QtCore.Qt.AlignCenter)
            ports_item.setForeground(QtGui.QBrush(QtGui.QColor("#9ca3af")))
            self.table.setItem(row, self.COL_PORTS, ports_item)
        ports_item.setText(ports_str)

        # 6. Version Column
        ver_item = self.table.item(row, self.COL_VERSION)
        if not ver_item:
            ver_item = QtWidgets.QTableWidgetItem()
            ver_item.setTextAlignment(QtCore.Qt.AlignCenter)
            ver_item.setForeground(QtGui.QBrush(QtGui.QColor("#cbd5e1")))
            self.table.setItem(row, self.COL_VERSION, ver_item)
        ver_item.setText(f"v{version}")

        # 7. Streams Column
        streams_str = self.t("streams_format", active=active_streams, services=running_services)
        streams_item = self.table.item(row, self.COL_STREAMS)
        if not streams_item:
            streams_item = QtWidgets.QTableWidgetItem()
            streams_item.setTextAlignment(QtCore.Qt.AlignCenter)
            streams_item.setForeground(QtGui.QBrush(QtGui.QColor("#9ca3af")))
            self.table.setItem(row, self.COL_STREAMS, streams_item)
        streams_item.setText(streams_str)

        # 8. Action Button (created once per row to prevent click race conditions)
        btn_open = self.table.cellWidget(row, self.COL_ACTION)
        if not isinstance(btn_open, QtWidgets.QPushButton):
            btn_open = QtWidgets.QPushButton(self.t("btn_open_gui"), self.table)
            btn_open.setObjectName("btnOpenGui")
            btn_open.setCursor(QtCore.Qt.PointingHandCursor)
            btn_open.clicked.connect(self._on_open_gui_clicked)
            self.table.setCellWidget(row, self.COL_ACTION, btn_open)
        else:
            btn_open.setText(self.t("btn_open_gui"))

    def _on_open_gui_clicked(self):
        btn = self.sender()
        if not btn:
            return
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, self.COL_ACTION) is btn:
                status_item = self.table.item(r, self.COL_STATUS)
                if status_item:
                    url = status_item.data(QtCore.Qt.UserRole + 1)
                    if url:
                        open_browser(url)
                break

    def _update_status_item(self, row: int, status: str):
        item = self.table.item(row, self.COL_STATUS)
        if item:
            self._apply_status_styling(item, status)

    def _apply_status_styling(self, item: QtWidgets.QTableWidgetItem, status: str):
        if status == "online":
            item.setText(self.t("badge_online"))
            item.setForeground(QtGui.QBrush(QtGui.QColor("#4ade80")))
            item.setToolTip(self.t("tooltip_online"))
        else:
            item.setText(self.t("badge_offline"))
            item.setForeground(QtGui.QBrush(QtGui.QColor("#f87171")))
            item.setToolTip(self.t("tooltip_offline"))

    def _on_cell_double_clicked(self, row: int, column: int):
        status_item = self.table.item(row, self.COL_STATUS)
        if status_item:
            url = status_item.data(QtCore.Qt.UserRole + 1)
            if url:
                open_browser(url)

    def _update_stats(self):
        total = self.table.rowCount()
        online = 0
        online_badge = self.t("badge_online").strip()
        for r in range(total):
            item = self.table.item(r, self.COL_STATUS)
            if item and online_badge in item.text():
                online += 1
        self.lbl_stats.setText(self.t("stats_format", total=total, online=online))

    def _filter_rows(self, query: str):
        query = query.strip().lower()
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, self.COL_NAME)
            alias_item = self.table.item(r, self.COL_ALIAS)
            ip_item = self.table.item(r, self.COL_IP)

            name = name_item.text().lower() if name_item else ""
            alias = alias_item.text().lower() if alias_item else ""
            ip = ip_item.text().lower() if ip_item else ""

            match = (not query) or (query in name) or (query in alias) or (query in ip)
            self.table.setRowHidden(r, not match)

    def closeEvent(self, event):
        self._auto_scan_timer.stop()
        self.listener.stop()
        event.accept()
