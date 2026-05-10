from __future__ import annotations

from collections import deque
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from core.utils import format_speed


class Panel(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("Panel")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.setMinimumHeight(220)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("PanelTitle")
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(12)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        self.body = QVBoxLayout()
        self.body.setSpacing(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(16)
        layout.addLayout(self.header_layout)
        layout.addLayout(self.body, 1)

    def set_title_widget(self, widget: QWidget) -> None:
        self.header_layout.replaceWidget(self.title_label, widget)
        self.title_label.deleteLater()
        self.title_label = widget

    def set_header_widget(self, widget: QWidget) -> None:
        self.header_layout.addWidget(widget)


class SectionTitle(QWidget):
    FALLBACKS = {
        "fa5s.tachometer-alt": ["fa5s.wave-square"],
        "fa5s.wave-square": ["fa5s.tachometer-alt"],
        "fa5s.history": ["fa5s.clock"],
        "fa5s.clock": ["fa5s.history"],
        "fa5s.download": ["fa5s.arrow-down"],
        "fa5s.arrow-down": ["fa5s.download"],
    }

    def __init__(self, title: str, icon_name: str, icon_color: str = "#38bdf8") -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(22, 22)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setPixmap(self._icon_pixmap(icon_name, icon_color))

        self.title_label = QLabel(title)
        self.title_label.setObjectName("PanelTitle")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addStretch()

    def _icon_pixmap(self, icon_name: str, icon_color: str):
        for candidate in [icon_name, *self.FALLBACKS.get(icon_name, [])]:
            try:
                return qta.icon(candidate, color=icon_color).pixmap(18, 18)
            except Exception:
                continue
        return qta.icon("fa5s.circle", color=icon_color).pixmap(14, 14)


class MetricIcon(QLabel):
    FALLBACKS = {
        "fa5s.th-large": ["fa5s.table", "fa5s.border-all"],
        "fa5s.border-all": ["fa5s.th-large", "fa5s.table"],
        "fa5s.play": ["fa5s.caret-right"],
        "fa5s.check": [],
        "fa5s.times": [],
    }

    def __init__(self, icon_name: str, icon_color: str, circle_background: str) -> None:
        super().__init__()
        self.icon_name = icon_name
        self.setObjectName("MetricIcon")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(56, 56)
        self.setMaximumSize(56, 56)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"""
            QLabel#MetricIcon {{
                background: {circle_background};
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 28px;
            }}
            """
        )
        self.setPixmap(self._icon_pixmap(icon_name, icon_color))

    def _icon_pixmap(self, icon_name: str, icon_color: str):
        for candidate in [icon_name, *self.FALLBACKS.get(icon_name, [])]:
            try:
                return qta.icon(candidate, color=icon_color).pixmap(24, 24)
            except Exception:
                continue
        return qta.icon("fa5s.circle", color=icon_color).pixmap(18, 18)


class MetricCard(QFrame):
    def __init__(
        self,
        title: str,
        value: str | int,
        icon_name: str,
        icon_color: str,
        circle_background: str,
        progress_color: str,
    ) -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        self.setMinimumHeight(108)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.icon = MetricIcon(icon_name, icon_color, circle_background)
        self.value = QLabel(str(value))
        self.value.setObjectName("MetricValue")
        self.label = QLabel(title)
        self.label.setObjectName("MetricLabel")
        self.bar = QProgressBar()
        self.bar.setObjectName("MiniProgress")
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(
            f"""
            QProgressBar#MiniProgress {{
                border: 0;
                min-height: 3px;
                max-height: 3px;
                background: rgba(255, 255, 255, 0.09);
                border-radius: 2px;
            }}
            QProgressBar#MiniProgress::chunk {{
                background: {progress_color};
                border-radius: 2px;
            }}
            """
        )

        copy = QVBoxLayout()
        copy.setSpacing(5)
        copy.addWidget(self.value)
        copy.addWidget(self.label)
        copy.addWidget(self.bar)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)
        layout.addWidget(self.icon)
        layout.addLayout(copy, 1)

    def set_value(self, value: str | int, progress: int = 0) -> None:
        self.value.setText(str(value))
        self.bar.setValue(max(0, min(progress, 100)))


class DownloadRowCard(QFrame):
    interaction_started = Signal()
    menu_opened = Signal()
    menu_closed = Signal()
    pause_requested = Signal()
    resume_requested = Signal()
    open_file_requested = Signal()
    open_folder_requested = Signal()
    copy_url_requested = Signal()
    retry_requested = Signal()
    remove_requested = Signal()
    delete_requested = Signal()

    STATUS_STYLES = {
        "Downloading": ("#d7ebff", "#123b67", "#238cff"),
        "Paused": ("#efe7ff", "#32224f", "#8b5cf6"),
        "Completed": ("#dbffe8", "#103b23", "#22c55e"),
        "Failed": ("#ffe0e7", "#481421", "#fb7185"),
        "Cancelled": ("#e2e8f0", "#283648", "#6b7280"),
    }

    def __init__(
        self,
        file_name: str,
        downloaded_text: str,
        progress_percent: int,
        speed_text: str,
        eta_text: str,
        status_text: str,
        *,
        download_url: str = "",
        file_path: str = "",
    ) -> None:
        super().__init__()
        self.setObjectName("DownloadRowCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.download_url = download_url
        self.file_path = Path(file_path) if file_path else None
        self.status_text = status_text

        self.file_icon = QLabel()
        self.file_icon.setObjectName("RowIcon")
        self.file_icon.setAlignment(Qt.AlignCenter)
        self.file_icon.setFixedSize(42, 42)
        self.file_icon.setPixmap(self._icon_pixmap(["fa5s.file-alt", "fa5s.file"], "#8ed8ff", 18))

        self.file_name_label = QLabel(file_name)
        self.file_name_label.setObjectName("DownloadFileName")
        self.file_name_label.setWordWrap(True)
        self.file_meta_label = QLabel(downloaded_text)
        self.file_meta_label.setObjectName("DownloadMeta")

        file_copy = QVBoxLayout()
        file_copy.setContentsMargins(0, 0, 0, 0)
        file_copy.setSpacing(4)
        file_copy.addWidget(self.file_name_label)
        file_copy.addWidget(self.file_meta_label)

        file_block = QHBoxLayout()
        file_block.setContentsMargins(0, 0, 0, 0)
        file_block.setSpacing(12)
        file_block.addWidget(self.file_icon, 0, Qt.AlignTop)
        file_block.addLayout(file_copy, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("DownloadRowProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(max(0, min(progress_percent, 100)))

        self.progress_value = QLabel(f"{max(0, min(progress_percent, 100))}%")
        self.progress_value.setObjectName("DownloadProgressValue")
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(10)
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_value, 0, Qt.AlignRight | Qt.AlignVCenter)

        progress_widget = QWidget()
        progress_widget.setLayout(progress_layout)

        self.speed_label = QLabel(speed_text)
        self.speed_label.setObjectName("DownloadInfoValue")
        self.eta_label = QLabel(eta_text)
        self.eta_label.setObjectName("DownloadInfoValue")

        self.status_badge = QLabel(status_text)
        self.status_badge.setObjectName("DownloadStatusBadge")
        self._apply_status_style(status_text)

        self.pause_button = QPushButton()
        self.pause_button.setObjectName("RowActionButton")
        self.pause_button.setFixedSize(34, 34)
        self.pause_button.clicked.connect(self.toggle_pause_resume)
        self._update_pause_button()

        self.more_button = QPushButton()
        self.more_button.setObjectName("RowActionButton")
        self.more_button.setFixedSize(34, 34)
        self.more_button.setIcon(self._button_icon("fa5s.ellipsis-v", "fa5s.ellipsis-h"))
        self.more_button.setToolTip("More options")
        self.more_button.clicked.connect(self.show_more_menu)

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        actions_layout.addWidget(self.pause_button)
        actions_layout.addWidget(self.more_button)

        actions_widget = QWidget()
        actions_widget.setLayout(actions_layout)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)
        layout.addLayout(file_block, 30)
        layout.addWidget(progress_widget, 28)
        layout.addWidget(self.speed_label, 10, Qt.AlignCenter)
        layout.addWidget(self.eta_label, 10, Qt.AlignCenter)
        layout.addWidget(self.status_badge, 12, Qt.AlignCenter)
        layout.addWidget(actions_widget, 10, Qt.AlignRight | Qt.AlignVCenter)

    def _icon_pixmap(self, names: list[str], color: str, size: int):
        for name in names:
            try:
                return qta.icon(name, color=color).pixmap(size, size)
            except Exception:
                continue
        return qta.icon("fa5s.circle", color=color).pixmap(max(12, size - 4), max(12, size - 4))

    def _button_icon(self, *names: str):
        for name in names:
            try:
                return qta.icon(name, color="#d8ebff")
            except Exception:
                continue
        return qta.icon("fa5s.circle", color="#d8ebff")

    def _apply_status_style(self, status_text: str) -> None:
        fg, bg, border = self.STATUS_STYLES.get(status_text, ("#dcecff", "#203246", "#365572"))
        self.status_badge.setStyleSheet(
            f"""
            QLabel#DownloadStatusBadge {{
                color: {fg};
                background: {bg};
                border: 1px solid {border};
                border-radius: 11px;
                padding: 4px 10px;
                font-weight: 700;
            }}
            """
        )

    def _update_pause_button(self) -> None:
        if self.status_text == "Paused":
            self.pause_button.setIcon(self._button_icon("fa5s.play"))
            self.pause_button.setToolTip("Resume this download")
            self.pause_button.setEnabled(True)
        elif self.status_text in {"Completed", "Failed", "Cancelled"}:
            self.pause_button.setIcon(self._button_icon("fa5s.pause"))
            self.pause_button.setToolTip("Pause unavailable")
            self.pause_button.setEnabled(False)
        elif self.status_text == "Pausing":
            self.pause_button.setIcon(self._button_icon("fa5s.pause"))
            self.pause_button.setToolTip("Pausing download")
            self.pause_button.setEnabled(False)
        else:
            self.pause_button.setIcon(self._button_icon("fa5s.pause"))
            self.pause_button.setToolTip("Pause this download")
            self.pause_button.setEnabled(True)

    def toggle_pause_resume(self) -> None:
        self.interaction_started.emit()
        self.pause_button.setEnabled(False)
        if self.status_text == "Paused":
            self.resume_requested.emit()
        elif self.status_text == "Downloading":
            self.pause_requested.emit()

    def show_more_menu(self) -> None:
        menu = QMenu(self)
        menu.aboutToHide.connect(self.menu_closed.emit)
        open_file_action = self._add_menu_action(menu, "Open File", "fa5s.file", self.open_file)
        open_folder_action = self._add_menu_action(menu, "Open Folder", "fa5s.folder-open", self.open_folder)
        copy_url_action = self._add_menu_action(menu, "Copy Download URL", "fa5s.link", self.copy_url)
        retry_action = self._add_menu_action(menu, "Retry Download", "fa5s.redo", self.retry_download)
        menu.addSeparator()
        remove_action = self._add_menu_action(menu, "Remove from List", "fa5s.trash-alt", self.remove_from_list)
        delete_action = self._add_menu_action(menu, "Delete File", "fa5s.times-circle", self.delete_file)

        file_exists = bool(self.file_path and self.file_path.exists())
        retry_enabled = self.status_text in {"Failed", "Cancelled", "Paused"}
        remove_enabled = self.status_text != "Downloading"
        delete_enabled = file_exists and self.status_text != "Downloading"

        open_file_action.setEnabled(file_exists)
        open_folder_action.setEnabled(file_exists)
        copy_url_action.setEnabled(bool(self.download_url))
        retry_action.setEnabled(retry_enabled)
        remove_action.setEnabled(remove_enabled)
        delete_action.setEnabled(delete_enabled)

        self.menu_opened.emit()
        menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))

    def _add_menu_action(self, menu: QMenu, text: str, icon_name: str, slot) -> QAction:
        action = menu.addAction(text)
        try:
            action.setIcon(qta.icon(icon_name, color="#dcecff"))
        except Exception:
            action.setIcon(qta.icon("fa5s.circle", color="#dcecff"))
        action.triggered.connect(slot)
        return action

    def open_file(self) -> None:
        self.open_file_requested.emit()

    def open_folder(self) -> None:
        self.open_folder_requested.emit()

    def copy_url(self) -> None:
        self.copy_url_requested.emit()

    def retry_download(self) -> None:
        self.retry_requested.emit()

    def remove_from_list(self) -> None:
        self.remove_requested.emit()

    def delete_file(self) -> None:
        self.delete_requested.emit()


class SpeedDial(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("SpeedDial")
        self.setMinimumSize(178, 178)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.speed_value = 0.0
        self.speed_text = "0 B/s"
        self.caption_text = "Current Total Speed"

    def set_speed(self, speed: float) -> None:
        self.speed_value = max(0.0, speed)
        self.speed_text = format_speed(speed)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        rect = self.rect().adjusted(10, 10, -10, -10)
        diameter = min(rect.width(), rect.height())
        square = rect
        if rect.width() != rect.height():
            left = rect.left() + (rect.width() - diameter) / 2
            top = rect.top() + (rect.height() - diameter) / 2
            square = rect.adjusted(
                int(left - rect.left()),
                int(top - rect.top()),
                -int(rect.right() - (left + diameter - 1)),
                -int(rect.bottom() - (top + diameter - 1)),
            )

        ring_width = max(8, diameter // 24)
        painter.setPen(QPen(QColor("#17365a"), ring_width))
        painter.setBrush(QColor("#081a2d"))
        painter.drawEllipse(square)

        inner_square = square.adjusted(ring_width + 4, ring_width + 4, -(ring_width + 4), -(ring_width + 4))
        painter.setPen(QPen(QColor("#0f2a48"), max(5, ring_width - 3)))
        painter.drawEllipse(inner_square)

        max_reference_speed = max(10 * 1024 * 1024, self.speed_value * 1.25)
        progress = min(self.speed_value / max_reference_speed, 1.0) if max_reference_speed > 0 else 0.0
        span_angle = max(0, int(280 * progress))

        painter.setPen(QPen(QColor("#238cff"), max(6, diameter // 28), Qt.SolidLine, Qt.RoundCap))
        if span_angle > 0:
            painter.drawArc(square, 40 * 16, span_angle * 16)

        painter.setPen(QColor("#ffffff"))
        value_font = QFont("Segoe UI", max(16, diameter // 10), QFont.Bold)
        painter.setFont(value_font)
        painter.drawText(square.adjusted(18, 22, -18, -14), Qt.AlignCenter, self.speed_text)

        painter.setPen(QColor("#9db0c8"))
        caption_font = QFont("Segoe UI", max(8, diameter // 24))
        painter.setFont(caption_font)
        painter.drawText(square.adjusted(12, 86, -12, -10), Qt.AlignCenter, self.caption_text)


class SpeedTimeline(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("SpeedTimeline")
        self.setMinimumHeight(210)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.samples = deque([0.0] * 61, maxlen=61)

    def push_speed(self, speed: float) -> None:
        self.samples.append(max(0.0, speed))
        self.update()

    def reset(self) -> None:
        self.samples = deque([0.0] * 61, maxlen=61)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), Qt.transparent)

        left = 66
        top = 14
        right = 16
        bottom = 36
        plot = self.rect().adjusted(left, top, -right, -bottom)
        if plot.width() <= 0 or plot.height() <= 0:
            return

        max_speed = max(max(self.samples), 10 * 1024 * 1024)
        grid_pen = QPen(QColor("#183653"), 1)
        text_pen = QPen(QColor("#a8bad1"))
        line_pen = QPen(QColor("#238cff"), 2)

        painter.setPen(grid_pen)
        for index in range(5):
            y = plot.top() + plot.height() * index / 4
            painter.drawLine(plot.left(), int(y), plot.right(), int(y))
        for index in range(6):
            x = plot.left() + plot.width() * index / 5
            painter.drawLine(int(x), plot.top(), int(x), plot.bottom())

        painter.setPen(text_pen)
        y_labels = ["10 MB/s", "7.5 MB/s", "5 MB/s", "2.5 MB/s", "0 B/s"]
        for index, label in enumerate(y_labels):
            y = plot.top() + plot.height() * index / 4
            painter.drawText(4, int(y) - 8, 56, 16, Qt.AlignRight | Qt.AlignVCenter, label)

        x_labels = ["60s", "45s", "30s", "15s", "Now"]
        x_positions = [0.0, 0.25, 0.5, 0.75, 1.0]
        for label, position in zip(x_labels, x_positions):
            x = plot.left() + plot.width() * position
            align = Qt.AlignHCenter | Qt.AlignTop
            if label == "60s":
                align = Qt.AlignLeft | Qt.AlignTop
            elif label == "Now":
                align = Qt.AlignRight | Qt.AlignTop
            painter.drawText(int(x) - 22, plot.bottom() + 12, 44, 18, align, label)

        path = QPainterPath()
        sample_count = len(self.samples)
        for index, sample in enumerate(self.samples):
            x = plot.left() + (plot.width() * index / max(sample_count - 1, 1))
            normalized = min(sample / max_speed, 1.0) if max_speed > 0 else 0.0
            y = plot.bottom() - normalized * plot.height()
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.setPen(line_pen)
        painter.drawPath(path)
