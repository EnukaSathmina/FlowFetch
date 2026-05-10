from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.utils import filename_from_url, is_valid_url, safe_filename


class NewDownloadPage(QWidget):
    start_requested = Signal(str, str, str)

    def __init__(self, default_folder: str) -> None:
        super().__init__()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/file.zip")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Detected automatically")
        self.folder_input = QLineEdit(default_folder)
        self.browse_button = QPushButton("Browse")
        self.start_button = QPushButton("Start Download")
        self.start_button.setObjectName("PrimaryButton")
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #fb7185;")
        self._name_manually_edited = False

        self.browse_button.clicked.connect(self._browse)
        self.start_button.clicked.connect(self._start)
        self.url_input.textChanged.connect(self._sync_name_from_url)
        self.name_input.textEdited.connect(self._mark_name_edited)

        form = QFrame()
        form.setObjectName("Card")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)
        form_layout.addWidget(QLabel("URL"))
        form_layout.addWidget(self.url_input)
        form_layout.addWidget(QLabel("Save name"))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(QLabel("Save location"))

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(self.browse_button)
        form_layout.addLayout(folder_row)
        form_layout.addWidget(self.error_label)
        form_layout.addWidget(self.start_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("New Download")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(form)
        layout.addStretch()

    def set_default_folder(self, folder: str) -> None:
        if not self.folder_input.text().strip():
            self.folder_input.setText(folder)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose download folder", self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def _mark_name_edited(self) -> None:
        self._name_manually_edited = True

    def _sync_name_from_url(self, text: str) -> None:
        if not self._name_manually_edited or not self.name_input.text().strip():
            self.name_input.setText(filename_from_url(text) if text.strip() else "")
            self._name_manually_edited = False

    def _start(self) -> None:
        url = self.url_input.text().strip()
        name = safe_filename(self.name_input.text().strip())
        folder = self.folder_input.text().strip()
        if not url:
            self._show_error(
                "Invalid download link. Please enter a valid direct file URL.",
                "Please enter a valid URL starting with http:// or https://",
            )
            return
        if not url.startswith(("http://", "https://")) or not is_valid_url(url):
            self._show_error(
                "Invalid download link. Please enter a valid direct file URL.",
                "Please enter a valid URL starting with http:// or https://",
            )
            return
        if not name:
            self.error_label.setText("Enter a file name.")
            return
        if not folder:
            self.error_label.setText("Choose a save folder.")
            return
        path = Path(folder)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error(
                "Cannot save to this folder. Choose another location.",
                f"Cannot save to this folder. Choose another location.\n\n{exc}",
            )
            return
        self.error_label.setText("")
        self.start_requested.emit(url, str(path), name)
        self.url_input.clear()
        self.name_input.clear()
        self._name_manually_edited = False

    def _show_error(self, inline_text: str, dialog_text: str) -> None:
        self.error_label.setText(inline_text)
        QMessageBox.warning(self, "Invalid download link", dialog_text)
