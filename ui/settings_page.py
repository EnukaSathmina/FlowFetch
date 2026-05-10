from __future__ import annotations

import os
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from core.utils import APP_DIR, DB_PATH


def _icon_pixmap(icon_names: list[str], color: str, size: int = 18):
    for icon_name in icon_names:
        try:
            return qta.icon(icon_name, color=color).pixmap(size, size)
        except Exception:
            continue
    return None


class SettingsSection(QFrame):
    def __init__(self, title: str, icon_names: list[str], icon_color: str, description: str | None = None) -> None:
        super().__init__()
        self.setObjectName("SettingsSection")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(20, 20, 20, 20)
        self.body.setSpacing(16)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = _icon_pixmap(icon_names, icon_color, 18)
        if pixmap:
            icon_label.setPixmap(pixmap)
        header.addWidget(icon_label)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("SettingsTitle")
        text_column.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("SettingsDescription")
            desc_label.setWordWrap(True)
            text_column.addWidget(desc_label)

        header.addLayout(text_column, 1)
        self.body.addLayout(header)

    def add_row(self, label_text: str, widget: QWidget, description: str | None = None) -> None:
        row = QWidget()
        row.setObjectName("SettingsRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        label = QLabel(label_text)
        label.setObjectName("SettingsRowLabel")
        text_col.addWidget(label)

        if description:
            desc = QLabel(description)
            desc.setObjectName("SettingsDescription")
            desc.setWordWrap(True)
            text_col.addWidget(desc)

        layout.addLayout(text_col, 1)
        layout.addWidget(widget, 0, Qt.AlignRight | Qt.AlignVCenter)
        self.body.addWidget(row)

    def add_full_width(self, widget: QWidget) -> None:
        self.body.addWidget(widget)


class AboutCard(QFrame):
    github_requested = Signal()
    updates_requested = Signal()
    app_folder_requested = Signal()

    def __init__(self, icon_path: Path) -> None:
        super().__init__()
        self.setObjectName("AboutCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        top = QHBoxLayout()
        top.setSpacing(16)

        icon_box = QLabel()
        icon_box.setObjectName("AboutIcon")
        icon_box.setFixedSize(68, 68)
        icon_box.setAlignment(Qt.AlignCenter)
        if icon_path.exists():
            from PySide6.QtGui import QPixmap

            icon_box.setPixmap(QPixmap(str(icon_path)).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        top.addWidget(icon_box, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        name = QLabel("FlowFetch")
        name.setObjectName("SettingsTitle")
        subtitle = QLabel("Modern high-speed download manager")
        subtitle.setObjectName("SettingsDescription")
        version = QLabel("Version: v1.0.0")
        version.setObjectName("SettingsDescription")
        developer = QLabel("Developer: Enuka Sathmina")
        developer.setObjectName("SettingsDescription")
        license_label = QLabel("License: All Rights Reserved")
        license_label.setObjectName("SettingsDescription")
        built_with = QLabel("Built with: Python, PySide6, SQLite")
        built_with.setObjectName("SettingsDescription")
        summary = QLabel(
            "FlowFetch is a clean and modern download manager designed for fast, organized, and reliable file downloads."
        )
        summary.setObjectName("SettingsDescription")
        summary.setWordWrap(True)

        for widget in [name, subtitle, version, developer, license_label, built_with, summary]:
            text_col.addWidget(widget)
        top.addLayout(text_col, 1)
        layout.addLayout(top)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.github_button = QPushButton("GitHub")
        self.updates_button = QPushButton("Check for Updates")
        self.folder_button = QPushButton("Open App Folder")
        for button in [self.github_button, self.updates_button, self.folder_button]:
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.github_button.clicked.connect(self.github_requested.emit)
        self.updates_button.clicked.connect(self.updates_requested.emit)
        self.folder_button.clicked.connect(self.app_folder_requested.emit)


class SettingsPage(QWidget):
    save_requested = Signal(dict)
    clear_history_requested = Signal()
    clear_failed_requested = Signal()
    clear_completed_requested = Signal()
    delete_temporary_files_requested = Signal()

    def __init__(self, settings: dict) -> None:
        super().__init__()
        self._settings = settings.copy()
        self._project_root = Path(__file__).resolve().parent.parent
        self._app_icon_path = self._project_root / "assets" / "icon.ico"

        self._build_controls()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        layout.addWidget(self._build_download_section())
        layout.addWidget(self._build_speed_section())
        layout.addWidget(self._build_interface_section())
        layout.addWidget(self._build_privacy_section())
        layout.addWidget(self._build_about_section())
        layout.addStretch(1)

        self._load_values(self._settings)

    def _build_controls(self) -> None:
        self.folder_input = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, 10)

        self.duplicate_combo = QComboBox()
        self.duplicate_combo.addItems(
            [
                "Auto rename duplicate files",
                "Ask before replacing",
                "Replace existing file",
            ]
        )
        self.category_checkbox = QCheckBox("Enable")
        self.auto_start_checkbox = QCheckBox("Enable")
        self.auto_retry_checkbox = QCheckBox("Enable")
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 10)

        self.speed_limit_checkbox = QCheckBox("Enable")
        self.speed_limit_spin = QDoubleSpinBox()
        self.speed_limit_spin.setRange(0.1, 999.0)
        self.speed_limit_spin.setDecimals(1)
        self.speed_limit_spin.setSuffix(" MB/s")
        self.show_total_speed_checkbox = QCheckBox("Show")
        self.speed_interval_combo = QComboBox()
        self.speed_interval_combo.addItems(["0.5 seconds", "1 second", "2 seconds"])

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(["Blue", "Cyan", "Purple", "Green"])
        self.sidebar_icons_checkbox = QCheckBox("Show")
        self.confirm_delete_checkbox = QCheckBox("Show")
        self.minimize_to_tray_checkbox = QCheckBox("Enable")
        self.notifications_checkbox = QCheckBox("Enable")

        self.save_history_checkbox = QCheckBox("Enable")
        self.clear_history_button = QPushButton("Clear History")
        self.clear_history_button.setObjectName("DangerButton")
        self.clear_failed_button = QPushButton("Clear Failed")
        self.clear_failed_button.setObjectName("DangerButton")
        self.clear_completed_button = QPushButton("Clear Completed")
        self.clear_completed_button.setObjectName("DangerButton")
        self.delete_temp_button = QPushButton("Delete Temporary Files")
        self.delete_temp_button.setObjectName("DangerButton")
        self.copy_db_path_button = QPushButton("Copy Database Path")

        self.save_button = QPushButton("Save Settings")
        self.save_button.setObjectName("PrimaryButton")
        self.message = QLabel("")
        self.message.setObjectName("Subtitle")

        self.browse_button.clicked.connect(self._browse)
        self.save_button.clicked.connect(self._save)
        self.auto_retry_checkbox.toggled.connect(self.retry_count_spin.setEnabled)
        self.speed_limit_checkbox.toggled.connect(self.speed_limit_spin.setEnabled)
        self.clear_history_button.clicked.connect(self._confirm_clear_history)
        self.clear_failed_button.clicked.connect(self._confirm_clear_failed)
        self.clear_completed_button.clicked.connect(self._confirm_clear_completed)
        self.delete_temp_button.clicked.connect(self._confirm_delete_temp_files)
        self.copy_db_path_button.clicked.connect(self._copy_database_path)

    def _build_download_section(self) -> QWidget:
        section = SettingsSection(
            "Download Settings",
            ["fa5s.download"],
            "#22d3ee",
            "Choose how new downloads are named, started, and organized.",
        )

        folder_widget = QWidget()
        folder_layout = QHBoxLayout(folder_widget)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(self.browse_button)
        section.add_row("Default download folder", folder_widget, "Used for new downloads unless you choose another folder.")
        section.add_row("Max simultaneous downloads", self.max_spin, "How many downloads FlowFetch should run at the same time.")
        section.add_row("Default file naming behavior", self.duplicate_combo, "Choose what happens when a file name already exists.")
        section.add_row("Auto create category folders", self.category_checkbox, "Create folders like Videos, Images, Documents, Software, and Other.")
        section.add_row("Start downloads automatically after adding link", self.auto_start_checkbox)
        section.add_row("Retry failed downloads automatically", self.auto_retry_checkbox)
        section.add_row("Retry count", self.retry_count_spin, "Number of retry attempts after a failure.")
        return section

    def _build_speed_section(self) -> QWidget:
        section = SettingsSection(
            "Speed Settings",
            ["fa5s.tachometer-alt", "fa5s.wave-square"],
            "#38bdf8",
            "Control speed display behavior and optional throttling.",
        )
        section.add_row("Enable speed limit", self.speed_limit_checkbox)
        section.add_row("Download speed limit", self.speed_limit_spin, "Applies per app session when speed limiting is enabled.")
        section.add_row("Show total speed in status bar", self.show_total_speed_checkbox)
        section.add_row("Update speed display every", self.speed_interval_combo)
        return section

    def _build_interface_section(self) -> QWidget:
        section = SettingsSection(
            "Interface Settings",
            ["fa5s.palette"],
            "#7c9cff",
            "Adjust the app appearance and a few desktop behavior preferences.",
        )
        section.add_row("Theme mode", self.theme_combo)
        section.add_row("Accent color", self.accent_combo)
        section.add_row("Show sidebar icons", self.sidebar_icons_checkbox)
        section.add_row("Show confirmation before deleting files", self.confirm_delete_checkbox)
        section.add_row("Minimize to tray", self.minimize_to_tray_checkbox)
        section.add_row("Show completion notifications", self.notifications_checkbox)
        return section

    def _build_privacy_section(self) -> QWidget:
        section = SettingsSection(
            "Privacy & History",
            ["fa5s.database"],
            "#8b5cf6",
            "Manage the saved history and app data that FlowFetch keeps locally.",
        )
        section.add_row("Save download history", self.save_history_checkbox)

        actions = QGridLayout()
        actions.setHorizontalSpacing(10)
        actions.setVerticalSpacing(10)
        actions.addWidget(self.clear_history_button, 0, 0)
        actions.addWidget(self.clear_failed_button, 0, 1)
        actions.addWidget(self.clear_completed_button, 1, 0)
        actions.addWidget(self.delete_temp_button, 1, 1)
        actions_host = QWidget()
        actions_host.setLayout(actions)
        section.add_full_width(actions_host)
        section.add_row("Database tools", self.copy_db_path_button, str(DB_PATH))
        return section

    def _build_about_section(self) -> QWidget:
        wrapper = SettingsSection(
            "About FlowFetch",
            ["fa5s.info-circle"],
            "#60a5fa",
            "Version and support details for this installation.",
        )
        self.about_card = AboutCard(self._app_icon_path)
        self.about_card.github_requested.connect(self._open_github)
        self.about_card.updates_requested.connect(self._show_update_placeholder)
        self.about_card.app_folder_requested.connect(self._open_app_folder)
        wrapper.add_full_width(self.about_card)
        wrapper.add_full_width(self.message)
        wrapper.add_full_width(self.save_button)
        return wrapper

    def _load_values(self, settings: dict) -> None:
        self.folder_input.setText(settings.get("download_folder", ""))
        self.max_spin.setValue(int(settings.get("max_simultaneous", 3)))
        self.duplicate_combo.setCurrentText(settings.get("duplicate_file_behavior", "Auto rename duplicate files"))
        self.category_checkbox.setChecked(bool(settings.get("auto_category_folders", False)))
        self.auto_start_checkbox.setChecked(bool(settings.get("auto_start_downloads", False)))
        self.auto_retry_checkbox.setChecked(bool(settings.get("auto_retry_failed", False)))
        self.retry_count_spin.setValue(int(settings.get("retry_count", 2)))
        self.retry_count_spin.setEnabled(self.auto_retry_checkbox.isChecked())

        self.speed_limit_checkbox.setChecked(bool(settings.get("speed_limit_enabled", False)))
        self.speed_limit_spin.setValue(float(settings.get("speed_limit_mbps", 10.0)))
        self.speed_limit_spin.setEnabled(self.speed_limit_checkbox.isChecked())
        self.show_total_speed_checkbox.setChecked(bool(settings.get("show_total_speed", True)))
        self.speed_interval_combo.setCurrentText(settings.get("speed_update_interval", "1 second"))

        self.theme_combo.setCurrentText(settings.get("theme_mode", "Dark"))
        self.accent_combo.setCurrentText(settings.get("accent_color", "Blue"))
        self.sidebar_icons_checkbox.setChecked(bool(settings.get("show_sidebar_icons", True)))
        self.confirm_delete_checkbox.setChecked(bool(settings.get("confirm_delete_files", True)))
        self.minimize_to_tray_checkbox.setChecked(bool(settings.get("minimize_to_tray", False)))
        self.notifications_checkbox.setChecked(bool(settings.get("show_notifications", True)))

        self.save_history_checkbox.setChecked(bool(settings.get("save_history", True)))

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose default folder", self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def _save(self) -> None:
        folder = self.folder_input.text().strip()
        if not folder:
            self.message.setText("Choose a default download folder before saving.")
            return
        settings = {
            "download_folder": folder,
            "max_simultaneous": self.max_spin.value(),
            "duplicate_file_behavior": self.duplicate_combo.currentText(),
            "auto_category_folders": self.category_checkbox.isChecked(),
            "auto_start_downloads": self.auto_start_checkbox.isChecked(),
            "auto_retry_failed": self.auto_retry_checkbox.isChecked(),
            "retry_count": self.retry_count_spin.value(),
            "speed_limit_enabled": self.speed_limit_checkbox.isChecked(),
            "speed_limit_mbps": self.speed_limit_spin.value(),
            "show_total_speed": self.show_total_speed_checkbox.isChecked(),
            "speed_update_interval": self.speed_interval_combo.currentText(),
            "theme_mode": self.theme_combo.currentText(),
            "accent_color": self.accent_combo.currentText(),
            "show_sidebar_icons": self.sidebar_icons_checkbox.isChecked(),
            "confirm_delete_files": self.confirm_delete_checkbox.isChecked(),
            "minimize_to_tray": self.minimize_to_tray_checkbox.isChecked(),
            "show_notifications": self.notifications_checkbox.isChecked(),
            "save_history": self.save_history_checkbox.isChecked(),
        }
        self._settings.update(settings)
        self.save_requested.emit(settings)
        self.message.setText("Settings saved.")

    def _confirm_clear_history(self) -> None:
        if QMessageBox.question(self, "Clear history", "Clear all download history?") == QMessageBox.Yes:
            self.clear_history_requested.emit()

    def _confirm_clear_failed(self) -> None:
        if QMessageBox.question(self, "Clear failed downloads", "Remove failed and cancelled downloads from history?") == QMessageBox.Yes:
            self.clear_failed_requested.emit()

    def _confirm_clear_completed(self) -> None:
        if QMessageBox.question(self, "Clear completed downloads", "Remove completed downloads from history?") == QMessageBox.Yes:
            self.clear_completed_requested.emit()

    def _confirm_delete_temp_files(self) -> None:
        if QMessageBox.question(
            self,
            "Delete temporary files",
            "Delete temporary download files from the app data folder and current download folder?",
        ) == QMessageBox.Yes:
            self.delete_temporary_files_requested.emit()

    def _copy_database_path(self) -> None:
        QApplication.clipboard().setText(str(DB_PATH))
        self.message.setText("Database path copied.")

    def _open_github(self) -> None:
        try:
            webbrowser.open("https://github.com/EnukaSathmina")
        except Exception as exc:
            QMessageBox.warning(self, "GitHub", f"Could not open the GitHub profile.\n\n{exc}")

    def _show_update_placeholder(self) -> None:
        QMessageBox.information(self, "Check for updates", "Update checking is not configured yet.")

    def _open_app_folder(self) -> None:
        try:
            os.startfile(str(APP_DIR))
        except OSError as exc:
            QMessageBox.warning(self, "Open app folder", f"Could not open the app folder.\n\n{exc}")
