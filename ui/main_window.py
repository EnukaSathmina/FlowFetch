from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from core.database import Database
from core.downloader import DownloadTask
from core.utils import (
    APP_DIR,
    detect_remote_file,
    load_settings,
    reveal_in_file_manager,
    safe_filename,
    save_settings,
    unique_path,
)
from ui.dashboard_page import ActiveDownloadSummary, DashboardPage
from ui.history_page import HistoryPage
from ui.new_download_page import NewDownloadPage
from ui.queue_page import QueuePage
from ui.settings_page import SettingsPage


def resolve_asset_path(name: str) -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base_dir / "assets" / name


@dataclass
class DownloadInfo:
    id: str
    url: str
    target_path: Path
    expected_size: int | None
    supports_ranges: bool
    status: str = "Queued"
    speed: float = 0.0
    downloaded: int = 0
    eta: float = -1.0


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._app_icon = QIcon(str(resolve_asset_path("icon.ico")))
        self.setWindowTitle("FlowFetch")
        self.setWindowIcon(self._app_icon)
        self.resize(1320, 840)
        self.setMinimumSize(1000, 650)
        self._closing = False

        self.database = Database()
        self.settings = load_settings()
        self.downloads: dict[str, DownloadInfo] = {}
        self.tasks: dict[str, DownloadTask] = {}
        self.pending: list[DownloadInfo] = []

        self.dashboard_page = DashboardPage()
        self.new_download_page = NewDownloadPage(self.settings["download_folder"])
        self.queue_page = QueuePage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(self.settings)

        self.stack = QStackedWidget()
        for page in [
            self.dashboard_page,
            self.new_download_page,
            self.queue_page,
            self.history_page,
            self.settings_page,
        ]:
            self.stack.addWidget(page)

        self.nav_buttons: list[QPushButton] = []
        sidebar = self._build_sidebar()
        root = QWidget()
        root.setObjectName("CentralRoot")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        layout.addWidget(sidebar)

        scroll_container = QWidget()
        scroll_container.setObjectName("MainContentHost")
        scroll_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_layout.addWidget(self.stack)

        self.content_scroll = QScrollArea()
        self.content_scroll.setObjectName("MainScrollArea")
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.NoFrame)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_scroll.setWidget(scroll_container)

        layout.addWidget(self.content_scroll, 1)
        self.setCentralWidget(root)
        self.status_speed = QLabel("Total Speed: 0 B/s")
        self.status_speed.setObjectName("StatusText")
        self.statusBar().addPermanentWidget(self.status_speed)

        self._load_style()
        self._wire_signals()
        self._apply_settings()
        self._restore_queue()
        self._refresh_history()
        self._refresh_dashboard()

        self.metrics_timer = QTimer(self)
        self.metrics_timer.setInterval(self._speed_interval_ms())
        self.metrics_timer.timeout.connect(self._refresh_dashboard)
        self.metrics_timer.start()

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        title = QLabel("FlowFetch")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Download manager")
        subtitle.setObjectName("Subtitle")
        logo = QLabel()
        logo.setObjectName("LogoMark")
        logo.setPixmap(
            self._app_icon.pixmap(48, 48).scaled(
                48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.addWidget(logo)

        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(3)
        brand_copy.addWidget(title)
        brand_copy.addWidget(subtitle)
        brand_row.addLayout(brand_copy, 1)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 34, 18, 22)
        layout.setSpacing(12)
        layout.addLayout(brand_row)
        layout.addSpacing(26)

        pages = [
            ("Dashboard", "fa5s.desktop"),
            ("New Download", "fa5s.plus-circle"),
            ("Queue", "fa5s.list"),
            ("History", "fa5s.history"),
            ("Settings", "fa5s.cog"),
        ]
        for index, (label, icon) in enumerate(pages):
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setIcon(self._nav_icon(icon))
            button.setIconSize(QSize(18, 18))
            button.setProperty("icon_name", icon)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self._show_page(i))
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()
        self.nav_buttons[0].setChecked(True)
        return sidebar

    def _nav_icon(self, icon_name: str) -> QIcon:
        try:
            return qta.icon(icon_name, color="#9fb7d0", color_active="#ffffff", color_selected="#ffffff")
        except Exception:
            return QIcon()

    def _load_style(self) -> None:
        style_path = Path(__file__).with_name("styles.qss")
        self.setStyleSheet(style_path.read_text(encoding="utf-8"))

    def _wire_signals(self) -> None:
        self.new_download_page.start_requested.connect(self.start_download)
        self.queue_page.pause_requested.connect(self.pause_download)
        self.queue_page.resume_requested.connect(self.resume_download)
        self.queue_page.cancel_requested.connect(self.cancel_download)
        self.queue_page.open_folder_requested.connect(lambda path: reveal_in_file_manager(Path(path)))
        self.dashboard_page.history_requested.connect(lambda: self._show_page(3))
        self.history_page.search_changed.connect(self._refresh_history)
        self.history_page.clear_requested.connect(self._clear_history)
        self.history_page.open_folder_requested.connect(lambda path: reveal_in_file_manager(Path(path)))
        self.settings_page.save_requested.connect(self._save_settings)
        self.settings_page.clear_history_requested.connect(self._clear_history_now)
        self.settings_page.clear_failed_requested.connect(self._clear_failed_history)
        self.settings_page.clear_completed_requested.connect(self._clear_completed_history)
        self.settings_page.delete_temporary_files_requested.connect(self._delete_temporary_files)

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)
        if index == 3:
            self._refresh_history()

    def start_download(self, url: str, folder: str, save_name: str) -> None:
        try:
            detected_name, size, supports_ranges = detect_remote_file(url)
            final_name = safe_filename(save_name.strip()) or detected_name
            target_path = unique_path(Path(folder), final_name)
            download_id = uuid.uuid4().hex
            info = DownloadInfo(download_id, url, target_path, size, supports_ranges)
            self.downloads[download_id] = info
            self.queue_page.add_download(download_id, target_path.name, target_path, supports_ranges)
            self._persist_queue_item(info)
            self._show_page(2)
            self._enqueue_or_start(info)
            self._refresh_dashboard()
        except PermissionError:
            QMessageBox.warning(
                self,
                "Download failed",
                "Cannot save to this folder. Choose another location.",
            )
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Download failed",
                f"Cannot save to this folder. Choose another location.\n\n{exc}",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Download failed",
                f"Invalid download link. Please enter a valid direct file URL.\n\n{exc}",
            )

    def _enqueue_or_start(self, info: DownloadInfo) -> None:
        if self._running_count() < int(self.settings["max_simultaneous"]):
            self._start_task(info)
        else:
            info.status = "Queued"
            self.pending.append(info)
            self._persist_queue_item(info)
            self.queue_page.set_status(info.id, "Queued")

    def _start_task(self, info: DownloadInfo) -> None:
        task = DownloadTask(info.id, info.url, info.target_path, info.expected_size, info.supports_ranges)
        task.progress.connect(self._on_progress)
        task.status_changed.connect(self._on_status)
        task.finished.connect(self._on_finished)
        self.tasks[info.id] = task
        info.status = "Downloading"
        self._persist_queue_item(info)
        task.start()

    def pause_download(self, download_id: str) -> None:
        task = self.tasks.get(download_id)
        info = self.downloads.get(download_id)
        if task and info:
            task.pause()

    def resume_download(self, download_id: str) -> None:
        task = self.tasks.get(download_id)
        info = self.downloads.get(download_id)
        if task and info and info.status == "Paused":
            task.resume()
            return
        if info and info.status == "Paused":
            self._enqueue_or_start(info)

    def cancel_download(self, download_id: str) -> None:
        task = self.tasks.get(download_id)
        if task:
            task.cancel()
            return
        self.pending = [item for item in self.pending if item.id != download_id]
        self._finish_without_worker(download_id, "Cancelled")

    def _on_progress(self, download_id: str, downloaded: int, total: int, speed: float, eta: float) -> None:
        if download_id in self.downloads:
            self.downloads[download_id].downloaded = downloaded
            self.downloads[download_id].speed = speed
            self.downloads[download_id].eta = eta
            if total > 0:
                self.downloads[download_id].expected_size = total
            self._persist_queue_item(self.downloads[download_id])
        self.queue_page.update_progress(download_id, downloaded, total, speed, eta)

    def _on_status(self, download_id: str, status: str) -> None:
        if download_id in self.downloads:
            self.downloads[download_id].status = status
            if status != "Downloading":
                self.downloads[download_id].speed = 0.0
                self.downloads[download_id].eta = -1.0
            self._persist_queue_item(self.downloads[download_id])
            self.queue_page.update_progress(
                download_id,
                self.downloads[download_id].downloaded,
                self.downloads[download_id].expected_size or 0,
                self.downloads[download_id].speed,
                self.downloads[download_id].eta,
            )
        self.queue_page.set_status(download_id, status)
        self._refresh_dashboard()

    def _on_finished(self, download_id: str, status: str, bytes_done: int, error: str) -> None:
        self.tasks.pop(download_id, None)
        info = self.downloads.get(download_id)
        if not info:
            self._start_next_pending()
            return

        info.status = status
        info.speed = 0.0
        if status == "Paused":
            self._persist_queue_item(info)
        elif status in {"Completed", "Failed", "Cancelled"}:
            if self.settings.get("save_history", True):
                self.database.add_history(
                    file_name=info.target_path.name,
                    file_path=str(info.target_path),
                    url=info.url,
                    size=info.expected_size or bytes_done,
                    status=status,
                )
            if status == "Failed" and error:
                QMessageBox.warning(self, "Download failed", f"{info.target_path.name}\n\n{error}")
            self.downloads.pop(download_id, None)
            self.database.remove_queue_item(download_id)
            QTimer.singleShot(1200, lambda did=download_id: self.queue_page.remove_download(did))

        self._start_next_pending()
        self._refresh_history()
        self._refresh_dashboard()

    def _finish_without_worker(self, download_id: str, status: str) -> None:
        info = self.downloads.pop(download_id, None)
        if not info:
            return
        if self.settings.get("save_history", True):
            self.database.add_history(
                file_name=info.target_path.name,
                file_path=str(info.target_path),
                url=info.url,
                size=info.expected_size,
                status=status,
            )
        self.database.remove_queue_item(download_id)
        self.queue_page.set_status(download_id, status)
        QTimer.singleShot(1200, lambda: self.queue_page.remove_download(download_id))
        self._refresh_history()
        self._refresh_dashboard()

    def _start_next_pending(self) -> None:
        while self.pending and self._running_count() < int(self.settings["max_simultaneous"]):
            self._start_task(self.pending.pop(0))

    def _running_count(self) -> int:
        return sum(1 for item in self.downloads.values() if item.status == "Downloading")

    def _refresh_dashboard(self) -> None:
        active_downloads = [
            ActiveDownloadSummary(
                file_name=item.target_path.name,
                downloaded=item.downloaded,
                total=item.expected_size or 0,
                speed=item.speed,
                eta=item.eta,
                status=item.status,
            )
            for item in self.downloads.values()
        ]
        self.dashboard_page.update_dashboard(
            self.database.counts(),
            active_count=self._running_count(),
            speed=sum(item.speed for item in self.downloads.values()),
            active_downloads=active_downloads,
            recent_records=self.database.history("")[:4],
        )
        self.status_speed.setText(f"Total Speed: {sum(item.speed for item in self.downloads.values()) / 1024 / 1024:.2f} MB/s")

    def _persist_queue_item(self, info: DownloadInfo) -> None:
        self.database.upsert_queue_item(
            download_id=info.id,
            url=info.url,
            file_name=info.target_path.name,
            file_path=str(info.target_path),
            size=info.expected_size,
            supports_ranges=info.supports_ranges,
            status=info.status,
            downloaded=info.downloaded,
        )

    def _restore_queue(self) -> None:
        for record in self.database.queue_items():
            restored_status = "Paused" if record.status in {"Downloading", "Pausing"} else record.status
            info = DownloadInfo(
                id=record.download_id,
                url=record.url,
                target_path=Path(record.file_path),
                expected_size=record.size,
                supports_ranges=record.supports_ranges,
                status=restored_status,
                downloaded=max(record.downloaded, 0),
            )
            self.downloads[info.id] = info
            self.queue_page.add_download(info.id, info.target_path.name, info.target_path, info.supports_ranges)
            self.queue_page.update_progress(info.id, info.downloaded, info.expected_size or 0, 0.0, -1.0)
            self.queue_page.set_status(info.id, info.status)
            self._persist_queue_item(info)
            if info.status == "Queued":
                self.pending.append(info)

        self._start_next_pending()

    def _refresh_history(self, search: str = "") -> None:
        self.history_page.set_records(self.database.history(search))

    def _clear_history(self) -> None:
        if QMessageBox.question(self, "Clear history", "Clear all download history?") == QMessageBox.Yes:
            self._clear_history_now()

    def _clear_history_now(self) -> None:
        self.database.clear_history()
        self._refresh_history()
        self._refresh_dashboard()

    def _clear_failed_history(self) -> None:
        self.database.clear_history_by_status({"failed", "cancelled"})
        self._refresh_history()
        self._refresh_dashboard()

    def _clear_completed_history(self) -> None:
        self.database.clear_history_by_status({"completed"})
        self._refresh_history()
        self._refresh_dashboard()

    def _delete_temporary_files(self) -> None:
        folders = {APP_DIR, Path(self.settings.get("download_folder", ""))}
        removed = 0
        for folder in folders:
            if not folder or not folder.exists() or not folder.is_dir():
                continue
            for pattern in ("*.part", "*.partial", "*.tmp"):
                for candidate in folder.glob(pattern):
                    try:
                        candidate.unlink()
                        removed += 1
                    except OSError:
                        continue
        if removed:
            QMessageBox.information(self, "Temporary files", f"Deleted {removed} temporary file(s).")
        else:
            QMessageBox.information(self, "Temporary files", "No temporary files were found.")

    def _save_settings(self, settings: dict) -> None:
        self.settings.update(settings)
        save_settings(self.settings)
        self._apply_settings()

    def _apply_settings(self) -> None:
        self.new_download_page.set_default_folder(self.settings["download_folder"])
        self.metrics_timer.setInterval(self._speed_interval_ms()) if hasattr(self, "metrics_timer") else None
        self.status_speed.setVisible(bool(self.settings.get("show_total_speed", True)))
        self._apply_sidebar_icon_setting()
        self._refresh_dashboard()

    def _apply_sidebar_icon_setting(self) -> None:
        show_icons = bool(self.settings.get("show_sidebar_icons", True))
        for button in self.nav_buttons:
            icon_name = button.property("icon_name")
            button.setIcon(self._nav_icon(icon_name) if show_icons and icon_name else QIcon())

    def _speed_interval_ms(self) -> int:
        interval = self.settings.get("speed_update_interval", "1 second")
        if interval == "0.5 seconds":
            return 500
        if interval == "2 seconds":
            return 2000
        return 1000

    def closeEvent(self, event) -> None:
        active = [task for task in self.tasks.values()]
        if active:
            reply = QMessageBox.question(
                self,
                "Quit FlowFetch",
                "Active downloads will be paused and restored next time. Quit?",
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self._closing = True
            for info in self.downloads.values():
                if info.status in {"Downloading", "Pausing"}:
                    info.status = "Paused"
                    info.speed = 0.0
                self._persist_queue_item(info)
            for task in active:
                task.pause()
        event.accept()
