from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import HistoryRecord
from core.utils import format_bytes


class HistoryPage(QWidget):
    search_changed = Signal(str)
    clear_requested = Signal()
    open_folder_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search history")
        self.clear_button = QPushButton("Clear history")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["File name", "Size", "Status", "Date", "Folder"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.empty_state = QFrame()
        self.empty_state.setObjectName("Card")
        self.empty_title = QLabel("No history yet")
        self.empty_title.setObjectName("PageTitle")
        self.empty_title.setAlignment(Qt.AlignCenter)
        self.empty_title.setStyleSheet("font-size: 20px;")
        self.empty_message = QLabel("Completed, failed, and cancelled downloads will appear here.")
        self.empty_message.setObjectName("Subtitle")
        self.empty_message.setAlignment(Qt.AlignCenter)
        self.empty_message.setWordWrap(True)
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(28, 36, 28, 36)
        empty_layout.setSpacing(10)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_message)

        self.search.textChanged.connect(self.search_changed)
        self.clear_button.clicked.connect(self.clear_requested)

        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("History")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addLayout(top)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table, 1)

    def set_records(self, records: list[HistoryRecord]) -> None:
        self.table.setRowCount(0)
        for record in records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(record.file_name))
            self.table.setItem(row, 1, QTableWidgetItem(format_bytes(record.size)))
            self.table.setItem(row, 2, QTableWidgetItem(record.status))
            self.table.setItem(row, 3, QTableWidgetItem(record.created_at))
            button = QPushButton("Open")
            button.clicked.connect(lambda checked=False, path=record.file_path: self.open_folder_requested.emit(path))
            self.table.setCellWidget(row, 4, button)
        empty = not records
        self.empty_state.setVisible(empty)
        self.table.setVisible(not empty)
