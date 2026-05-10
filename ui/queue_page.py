from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QApplication,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from core.utils import format_bytes, format_eta, format_speed


class DownloadRow(QFrame):
    pause_requested = Signal(str)
    resume_requested = Signal(str)
    cancel_requested = Signal(str)
    open_folder_requested = Signal(str)

    def __init__(self, download_id: str, file_name: str, target_path: Path, supports_resume: bool) -> None:
        super().__init__()
        self.download_id = download_id
        self.target_path = target_path
        self.supports_resume = supports_resume
        self.setObjectName("Card")

        self.name_label = QLabel(file_name)
        self.name_label.setStyleSheet("font-weight: 700;")
        self.detail_label = QLabel("Waiting")
        self.detail_label.setObjectName("Subtitle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label = QLabel("Queued")
        self.status_label.setObjectName("Subtitle")

        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.cancel_button = QPushButton("Cancel")
        self.open_button = QPushButton("Open folder")
        style = QApplication.style()
        self.pause_button.setIcon(style.standardIcon(QStyle.SP_MediaPause))
        self.resume_button.setIcon(style.standardIcon(QStyle.SP_MediaPlay))
        self.cancel_button.setIcon(style.standardIcon(QStyle.SP_DialogCancelButton))
        self.open_button.setIcon(style.standardIcon(QStyle.SP_DirOpenIcon))
        self.resume_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.pause_button.setToolTip("Pause this download.")
        if not supports_resume:
            self.resume_button.setToolTip("This server may not support resume; FlowFetch will restart the file if needed.")

        self.pause_button.clicked.connect(lambda: self.pause_requested.emit(self.download_id))
        self.resume_button.clicked.connect(lambda: self.resume_requested.emit(self.download_id))
        self.cancel_button.clicked.connect(lambda: self.cancel_requested.emit(self.download_id))
        self.open_button.clicked.connect(lambda: self.open_folder_requested.emit(str(self.target_path)))

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addWidget(self.pause_button)
        button_row.addWidget(self.resume_button)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.open_button)
        button_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        layout.addWidget(self.name_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.status_label)
        layout.addLayout(button_row)

    def update_progress(self, downloaded: int, total: int, speed: float, eta: float) -> None:
        if total > 0:
            self.progress.setValue(int(downloaded * 100 / total))
            size_text = f"{format_bytes(downloaded)} / {format_bytes(total)}"
        else:
            self.progress.setValue(0)
            size_text = f"{format_bytes(downloaded)} / Unknown"
        self.detail_label.setText(f"{size_text}   {format_speed(speed)}   ETA {format_eta(eta)}")

    def set_status(self, status: str) -> None:
        self.status_label.setText(status)
        if status == "Paused":
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)
        elif status == "Pausing":
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
        elif status in {"Completed", "Failed", "Cancelled"}:
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
        elif status == "Downloading":
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)
            self.cancel_button.setEnabled(True)


class QueuePage(QWidget):
    pause_requested = Signal(str)
    resume_requested = Signal(str)
    cancel_requested = Signal(str)
    open_folder_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.rows: dict[str, DownloadRow] = {}
        self.empty_label = QLabel("No active downloads")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setObjectName("PageTitle")

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.list_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("Queue")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(self.empty_label)
        layout.addWidget(scroll, 1)
        self._sync_empty()

    def add_download(self, download_id: str, file_name: str, target_path: Path, supports_resume: bool) -> None:
        row = DownloadRow(download_id, file_name, target_path, supports_resume)
        row.pause_requested.connect(self.pause_requested)
        row.resume_requested.connect(self.resume_requested)
        row.cancel_requested.connect(self.cancel_requested)
        row.open_folder_requested.connect(self.open_folder_requested)
        self.rows[download_id] = row
        self.list_layout.insertWidget(max(self.list_layout.count() - 1, 0), row)
        self._sync_empty()

    def remove_download(self, download_id: str) -> None:
        row = self.rows.pop(download_id, None)
        if row:
            row.setParent(None)
            row.deleteLater()
        self._sync_empty()

    def update_progress(self, download_id: str, downloaded: int, total: int, speed: float, eta: float) -> None:
        if download_id in self.rows:
            self.rows[download_id].update_progress(downloaded, total, speed, eta)

    def set_status(self, download_id: str, status: str) -> None:
        if download_id in self.rows:
            self.rows[download_id].set_status(status)

    def _sync_empty(self) -> None:
        self.empty_label.setVisible(not self.rows)
