from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.database import HistoryRecord
from core.utils import format_bytes, format_eta, format_speed, reveal_in_file_manager
from ui.components import DownloadRowCard, MetricCard, Panel, SectionTitle, SpeedDial, SpeedTimeline


@dataclass(frozen=True)
class ActiveDownloadSummary:
    file_name: str
    downloaded: int
    total: int
    speed: float
    eta: float
    status: str
    download_id: str = ""
    url: str = ""
    file_path: str = ""


class DashboardPage(QWidget):
    history_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._row_menu_open = False
        self._row_action_locked = False
        self._pending_active_downloads: list[ActiveDownloadSummary] | None = None
        self.total = MetricCard(
            title="Total",
            value=0,
            icon_name="fa5s.th-large",
            icon_color="#4db8ff",
            circle_background="qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #123d67, stop:1 #071a34)",
            progress_color="#24b8ff",
        )
        self.active = MetricCard(
            title="Active",
            value=0,
            icon_name="fa5s.play",
            icon_color="#2ee6e6",
            circle_background="qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0c4c55, stop:1 #061f2c)",
            progress_color="#28e3ff",
        )
        self.completed = MetricCard(
            title="Completed",
            value=0,
            icon_name="fa5s.check",
            icon_color="#7dff9b",
            circle_background="qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #145536, stop:1 #071f1b)",
            progress_color="#6cff8c",
        )
        self.failed = MetricCard(
            title="Failed",
            value=0,
            icon_name="fa5s.times",
            icon_color="#ff6b8a",
            circle_background="qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5a1730, stop:1 #240917)",
            progress_color="#ff5f7e",
        )
        self.metric_cards = [self.total, self.active, self.completed, self.failed]

        self.speed_dial = SpeedDial()
        self.speed_timeline = SpeedTimeline()

        self.speed_panel = Panel("Download Speed")
        self.speed_panel.setObjectName("SpeedPanel")
        self.speed_panel.setMinimumHeight(285)
        self.speed_panel.set_title_widget(
            SectionTitle("Download Speed", "fa5s.tachometer-alt", "#38bdf8")
        )
        self.speed_mode = QComboBox()
        self.speed_mode.setObjectName("SpeedMode")
        self.speed_mode.addItem("Real-time")
        self.speed_panel.set_header_widget(self.speed_mode)
        self.speed_panel_inner = QGridLayout()
        self.speed_panel_inner.setSpacing(22)

        self.speed_chart_frame = QFrame()
        self.speed_chart_frame.setObjectName("SpeedChartSurface")
        self.speed_chart_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chart_layout = QVBoxLayout(self.speed_chart_frame)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        chart_layout.addWidget(self.speed_timeline, 1)

        self.speed_dial_container = QWidget()
        self.speed_dial_container.setObjectName("TransparentContainer")
        self.speed_dial_container.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)
        self.speed_dial_wrap = QVBoxLayout(self.speed_dial_container)
        self.speed_dial_wrap.setContentsMargins(0, 0, 0, 0)
        self.speed_dial_wrap.setSpacing(0)
        self.speed_dial_wrap.addWidget(self.speed_dial, 1)

        self.speed_panel.body.addLayout(self.speed_panel_inner)

        self.recent_panel = Panel("Recent Activity")
        self.recent_panel.setMinimumHeight(285)
        self.recent_panel.set_title_widget(
            SectionTitle("Recent Activity", "fa5s.history", "#60a5fa")
        )
        self.recent_list = QVBoxLayout()
        self.recent_list.setSpacing(8)
        self.view_history = QPushButton("View full history")
        self.view_history.clicked.connect(self.history_requested)
        self.recent_panel.body.addLayout(self.recent_list)
        self.recent_panel.body.addWidget(self.view_history)

        self.active_panel = Panel("Active Downloads")
        self.active_panel.setMinimumHeight(245)
        self.active_panel.set_title_widget(
            SectionTitle("Active Downloads", "fa5s.download", "#22d3ee")
        )
        self.active_section = QWidget()
        self.active_section.setObjectName("DownloadSection")
        self.active_section_layout = QVBoxLayout(self.active_section)
        self.active_section_layout.setContentsMargins(0, 0, 0, 0)
        self.active_section_layout.setSpacing(12)

        self.active_header = QWidget()
        self.active_header.setObjectName("DownloadHeader")
        header_layout = QHBoxLayout(self.active_header)
        header_layout.setContentsMargins(18, 0, 18, 0)
        header_layout.setSpacing(16)
        for text, stretch, align in [
            ("Name", 30, Qt.AlignLeft | Qt.AlignVCenter),
            ("Progress", 28, Qt.AlignLeft | Qt.AlignVCenter),
            ("Speed", 10, Qt.AlignCenter),
            ("ETA", 10, Qt.AlignCenter),
            ("Status", 12, Qt.AlignCenter),
            ("Actions", 10, Qt.AlignRight | Qt.AlignVCenter),
        ]:
            label = QLabel(text)
            label.setObjectName("DownloadHeaderLabel")
            header_layout.addWidget(label, stretch, align)

        self.active_scroll = QScrollArea()
        self.active_scroll.setObjectName("DownloadScrollArea")
        self.active_scroll.setWidgetResizable(True)
        self.active_scroll.setFrameShape(QFrame.NoFrame)
        self.active_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.active_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.active_scroll.setMinimumHeight(220)

        self.active_list_host = QWidget()
        self.active_list_host.setObjectName("DownloadListHost")
        self.active_list = QVBoxLayout(self.active_list_host)
        self.active_list.setContentsMargins(0, 0, 0, 0)
        self.active_list.setSpacing(10)
        self.active_list.addStretch()
        self.active_scroll.setWidget(self.active_list_host)

        self.active_empty = QLabel("No active downloads\nYour current downloads will appear here")
        self.active_empty.setObjectName("EmptyState")
        self.active_empty.setAlignment(Qt.AlignCenter)
        self.active_section_layout.addWidget(self.active_header)
        self.active_section_layout.addWidget(self.active_empty)
        self.active_section_layout.addWidget(self.active_scroll, 1)
        self.active_panel.body.addWidget(self.active_section, 1)

        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(16)

        self.middle_grid = QGridLayout()
        self.middle_grid.setSpacing(18)

        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Overview of your downloads and system activity")
        subtitle.setObjectName("Subtitle")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(26, 26, 26, 20)
        self.main_layout.setSpacing(16)
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(subtitle)
        self.main_layout.addLayout(self.stats_grid)
        self.main_layout.addLayout(self.middle_grid)
        self.main_layout.addWidget(self.active_panel, 1)

        self.update_responsive_layout(self._responsive_width())

    def _responsive_width(self) -> int:
        window = self.window()
        return window.width() if window is not None else self.width()

    def update_responsive_layout(self, width: int) -> None:
        if width >= 1100:
            stats_columns = 4
            middle_columns = 2
        elif width >= 850:
            stats_columns = 2
            middle_columns = 1
        else:
            stats_columns = 1
            middle_columns = 1

        while self.stats_grid.count():
            self.stats_grid.takeAt(0)
        for index, card in enumerate(self.metric_cards):
            row = index // stats_columns
            column = index % stats_columns
            self.stats_grid.addWidget(card, row, column)
        for column in range(stats_columns):
            self.stats_grid.setColumnStretch(column, 1)

        while self.middle_grid.count():
            self.middle_grid.takeAt(0)
        while self.speed_panel_inner.count():
            self.speed_panel_inner.takeAt(0)

        if middle_columns == 2:
            self.middle_grid.addWidget(self.speed_panel, 0, 0)
            self.middle_grid.addWidget(self.recent_panel, 0, 1)
            self.middle_grid.setColumnStretch(0, 3)
            self.middle_grid.setColumnStretch(1, 2)

            self.speed_panel_inner.addWidget(self.speed_dial_container, 0, 0)
            self.speed_panel_inner.addWidget(self.speed_chart_frame, 0, 1)
            self.speed_panel_inner.setColumnStretch(0, 1)
            self.speed_panel_inner.setColumnStretch(1, 2)
        else:
            self.middle_grid.addWidget(self.speed_panel, 0, 0)
            self.middle_grid.addWidget(self.recent_panel, 1, 0)
            self.middle_grid.setColumnStretch(0, 1)

            self.speed_panel_inner.addWidget(self.speed_dial_container, 0, 0)
            self.speed_panel_inner.addWidget(self.speed_chart_frame, 1, 0)
            self.speed_panel_inner.setColumnStretch(0, 1)

        self.speed_panel_inner.setRowStretch(self.speed_panel_inner.rowCount(), 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_responsive_layout(self._responsive_width())

    def update_dashboard(
        self,
        counts: dict[str, int],
        active_count: int,
        speed: float,
        active_downloads: list[ActiveDownloadSummary],
        recent_records: list[HistoryRecord],
    ) -> None:
        stored_total = counts.get("total", 0)
        total = stored_total + active_count
        completed = counts.get("completed", 0)
        failed = counts.get("failed", 0)

        self.total.set_value(total, 100 if total else 0)
        self.active.set_value(active_count, 100 if active_count else 0)
        self.completed.set_value(completed, int(completed * 100 / total) if total else 0)
        self.failed.set_value(failed, int(failed * 100 / total) if total else 0)
        self.speed_dial.set_speed(speed)
        self.speed_timeline.push_speed(speed)
        self._set_active_downloads(active_downloads)
        self._set_recent_records(recent_records)

    def _set_active_downloads(self, downloads: list[ActiveDownloadSummary]) -> None:
        if self._row_menu_open or self._row_action_locked:
            self._pending_active_downloads = downloads
            return

        while self.active_list.count() > 1:
            item = self.active_list.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        used_ids: set[str] = set()
        for item in downloads:
            resolved = self._resolve_download(item, used_ids)
            if item.total > 0:
                progress = int(item.downloaded * 100 / item.total)
                progress_text = f"{format_bytes(item.downloaded)} / {format_bytes(item.total)}"
            else:
                progress = 0
                progress_text = f"{format_bytes(item.downloaded)} / Unknown"
            row = DownloadRowCard(
                file_name=resolved.file_name,
                downloaded_text=progress_text,
                progress_percent=progress,
                speed_text=format_speed(resolved.speed),
                eta_text=format_eta(resolved.eta),
                status_text=resolved.status,
                download_url=resolved.url,
                file_path=resolved.file_path,
            )
            row.pause_requested.connect(lambda resolved=resolved: self.pause_download(resolved))
            row.resume_requested.connect(lambda resolved=resolved: self.resume_download(resolved))
            row.open_file_requested.connect(lambda resolved=resolved: self.open_file(resolved))
            row.open_folder_requested.connect(lambda resolved=resolved: self.open_folder(resolved))
            row.copy_url_requested.connect(lambda resolved=resolved: self.copy_url(resolved))
            row.retry_requested.connect(lambda resolved=resolved: self.retry_download(resolved))
            row.remove_requested.connect(lambda resolved=resolved: self.remove_from_list(resolved))
            row.delete_requested.connect(lambda resolved=resolved: self.delete_file(resolved))
            row.interaction_started.connect(self._on_row_interaction_started)
            row.menu_opened.connect(self._on_row_menu_opened)
            row.menu_closed.connect(self._on_row_menu_closed)
            self.active_list.insertWidget(max(self.active_list.count() - 1, 0), row)

        empty = not downloads
        self.active_empty.setVisible(empty)
        self.active_header.setVisible(not empty)
        self.active_scroll.setVisible(not empty)
        self._pending_active_downloads = None

    def _on_row_menu_opened(self) -> None:
        self._row_menu_open = True

    def _on_row_menu_closed(self) -> None:
        self._row_menu_open = False
        self._flush_pending_active_downloads()

    def _on_row_interaction_started(self) -> None:
        self._row_action_locked = True
        QTimer.singleShot(0, self._release_row_action_lock)

    def _release_row_action_lock(self) -> None:
        self._row_action_locked = False
        self._flush_pending_active_downloads()

    def _flush_pending_active_downloads(self) -> None:
        if self._row_menu_open or self._row_action_locked:
            return
        if self._pending_active_downloads is not None:
            pending = self._pending_active_downloads
            self._pending_active_downloads = None
            self._set_active_downloads(pending)

    def _resolve_download(self, item: ActiveDownloadSummary, used_ids: set[str]) -> ActiveDownloadSummary:
        if item.download_id and item.file_path and item.url:
            used_ids.add(item.download_id)
            return item

        window = self.window()
        downloads = getattr(window, "downloads", {})
        for info in downloads.values():
            if info.id in used_ids:
                continue
            if info.target_path.name != item.file_name:
                continue
            if info.downloaded != item.downloaded:
                continue
            if info.status != item.status:
                continue
            used_ids.add(info.id)
            return ActiveDownloadSummary(
                download_id=info.id,
                file_name=info.target_path.name,
                downloaded=info.downloaded,
                total=info.expected_size or 0,
                speed=info.speed,
                eta=info.eta,
                status=info.status,
                url=info.url,
                file_path=str(info.target_path),
            )
        return item

    def open_file(self, item: ActiveDownloadSummary) -> None:
        file_path = Path(item.file_path)
        if file_path.exists():
            try:
                import os
                os.startfile(str(file_path))
            except OSError:
                pass

    def open_folder(self, item: ActiveDownloadSummary) -> None:
        file_path = Path(item.file_path)
        if file_path.exists():
            reveal_in_file_manager(file_path)

    def copy_url(self, item: ActiveDownloadSummary) -> None:
        if item.url:
            QApplication.clipboard().setText(item.url)

    def pause_download(self, item: ActiveDownloadSummary) -> None:
        window = self.window()
        if item.download_id and hasattr(window, "pause_download"):
            window.pause_download(item.download_id)

    def resume_download(self, item: ActiveDownloadSummary) -> None:
        window = self.window()
        if item.download_id and hasattr(window, "resume_download"):
            window.resume_download(item.download_id)

    def retry_download(self, item: ActiveDownloadSummary) -> None:
        window = self.window()
        if item.status == "Paused" and item.download_id and hasattr(window, "resume_download"):
            window.resume_download(item.download_id)
            return
        if item.status in {"Failed", "Cancelled"} and item.url and item.file_path and hasattr(window, "start_download"):
            target_path = Path(item.file_path)
            window.start_download(item.url, str(target_path.parent), target_path.name)

    def remove_from_list(self, item: ActiveDownloadSummary) -> None:
        if item.status == "Downloading" or not item.download_id:
            return
        self._remove_download_entry(item.download_id)

    def delete_file(self, item: ActiveDownloadSummary) -> None:
        if item.status == "Downloading" or not item.file_path:
            return
        file_path = Path(item.file_path)
        reply = QMessageBox.question(
            self,
            "Delete file",
            f"Delete {file_path.name} from disk and remove it from the list?",
        )
        if reply != QMessageBox.Yes:
            return
        window = self.window()
        tasks = getattr(window, "tasks", {})
        if item.download_id and item.download_id in tasks:
            tasks[item.download_id].cancel()
            QTimer.singleShot(200, lambda item=item: self._finish_delete_file(item, 0))
            return
        self._finish_delete_file(item, 0)

    def _finish_delete_file(self, item: ActiveDownloadSummary, attempts: int) -> None:
        window = self.window()
        if item.download_id and item.download_id in getattr(window, "tasks", {}):
            if attempts < 40:
                QTimer.singleShot(200, lambda item=item, attempts=attempts + 1: self._finish_delete_file(item, attempts))
            else:
                QMessageBox.warning(
                    self,
                    "Delete file",
                    "Could not delete the file while the download is still active.",
                )
            return

        file_path = Path(item.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as exc:
                QMessageBox.warning(
                    self,
                    "Delete file",
                    f"Could not delete the file.\n\n{exc}",
                )
                return
        if item.download_id:
            self._remove_download_entry(item.download_id)

    def _remove_download_entry(self, download_id: str) -> None:
        window = self.window()
        info = getattr(window, "downloads", {}).pop(download_id, None)
        if info is None:
            return

        pending = getattr(window, "pending", None)
        if isinstance(pending, list):
            window.pending = [entry for entry in pending if entry.id != download_id]

        tasks = getattr(window, "tasks", {})
        tasks.pop(download_id, None)

        if hasattr(window, "database"):
            window.database.remove_queue_item(download_id)
        if hasattr(window, "queue_page"):
            window.queue_page.remove_download(download_id)
        if hasattr(window, "_refresh_dashboard"):
            window._refresh_dashboard()

    def _set_recent_records(self, records: list[HistoryRecord]) -> None:
        while self.recent_list.count():
            item = self.recent_list.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not records:
            empty = QLabel("No recent activity")
            empty.setObjectName("Subtitle")
            empty.setAlignment(Qt.AlignCenter)
            self.recent_list.addWidget(empty)
            return

        for record in records[:4]:
            row = QFrame()
            row.setObjectName("ActivityRow")
            name = QLabel(record.file_name)
            name.setObjectName("ActivityName")
            name.setWordWrap(True)
            meta = QLabel(f"{format_bytes(record.size)}  -  {record.status}")
            meta.setObjectName("Subtitle")
            layout = QVBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)
            layout.addWidget(name)
            layout.addWidget(meta)
            self.recent_list.addWidget(row)
