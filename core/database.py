from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.utils import DB_PATH, ensure_app_dirs


@dataclass(frozen=True)
class HistoryRecord:
    id: int
    file_name: str
    file_path: str
    url: str
    size: int | None
    status: str
    created_at: str


@dataclass(frozen=True)
class QueueRecord:
    download_id: str
    url: str
    file_name: str
    file_path: str
    size: int | None
    supports_ranges: bool
    status: str
    downloaded: int
    created_at: str


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        ensure_app_dirs()
        self.path = path
        self._init_schema()
        self._columns = self._download_columns()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    url TEXT NOT NULL,
                    size INTEGER,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_items (
                    download_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    size INTEGER,
                    supports_ranges INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    downloaded INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_queue_items_status ON queue_items(status)"
            )

    def _download_columns(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute("PRAGMA table_info(downloads)").fetchall()
        return {row["name"] for row in rows}

    def add_history(
        self,
        *,
        file_name: str,
        file_path: str,
        url: str,
        size: int | None,
        status: str,
    ) -> None:
        with self._connect() as connection:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if {"file_name", "file_path"} <= self._columns:
                connection.execute(
                    """
                    INSERT INTO downloads (file_name, file_path, url, size, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (file_name, file_path, url, size, status, created_at),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO downloads (url, filename, save_path, size, downloaded, status, created_at, completed_at, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        file_name,
                        file_path,
                        size if size is not None else -1,
                        size if size is not None and status == "Completed" else 0,
                        status,
                        created_at,
                        created_at if status == "Completed" else None,
                        None if status == "Completed" else status,
                    ),
                )

    def history(self, search: str = "") -> list[HistoryRecord]:
        if {"file_name", "file_path"} <= self._columns:
            query = """
                SELECT id, file_name, file_path, url, size, status, created_at
                FROM downloads
            """
            search_clause = " WHERE file_name LIKE ? OR url LIKE ? OR status LIKE ?"
        else:
            query = """
                SELECT
                    id,
                    filename AS file_name,
                    save_path AS file_path,
                    url,
                    NULLIF(size, -1) AS size,
                    status,
                    created_at
                FROM downloads
            """
            search_clause = " WHERE filename LIKE ? OR url LIKE ? OR status LIKE ?"
        params: tuple[str, ...] = ()
        if search.strip():
            query += search_clause
            term = f"%{search.strip()}%"
            params = (term, term, term)
        query += " ORDER BY id DESC"

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [HistoryRecord(**dict(row)) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM downloads GROUP BY status"
            ).fetchall()
            total = connection.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        result = {"total": total, "completed": 0, "failed": 0}
        for row in rows:
            status = row["status"].lower()
            if status == "completed":
                result["completed"] = row["count"]
            elif status in {"failed", "cancelled"}:
                result["failed"] += row["count"]
        return result

    def clear_history(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM downloads")

    def clear_history_by_status(self, statuses: list[str] | tuple[str, ...] | set[str]) -> None:
        normalized = tuple(statuses)
        if not normalized:
            return
        placeholders = ", ".join("?" for _ in normalized)
        with self._connect() as connection:
            connection.execute(
                f"DELETE FROM downloads WHERE LOWER(status) IN ({placeholders})",
                tuple(status.lower() for status in normalized),
            )

    def upsert_queue_item(
        self,
        *,
        download_id: str,
        url: str,
        file_name: str,
        file_path: str,
        size: int | None,
        supports_ranges: bool,
        status: str,
        downloaded: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO queue_items (
                    download_id, url, file_name, file_path, size,
                    supports_ranges, status, downloaded, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(download_id) DO UPDATE SET
                    url = excluded.url,
                    file_name = excluded.file_name,
                    file_path = excluded.file_path,
                    size = excluded.size,
                    supports_ranges = excluded.supports_ranges,
                    status = excluded.status,
                    downloaded = excluded.downloaded
                """,
                (
                    download_id,
                    url,
                    file_name,
                    file_path,
                    size,
                    1 if supports_ranges else 0,
                    status,
                    downloaded,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

    def remove_queue_item(self, download_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM queue_items WHERE download_id = ?", (download_id,))

    def queue_items(self) -> list[QueueRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    download_id,
                    url,
                    file_name,
                    file_path,
                    size,
                    supports_ranges,
                    status,
                    downloaded,
                    created_at
                FROM queue_items
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [
            QueueRecord(
                download_id=row["download_id"],
                url=row["url"],
                file_name=row["file_name"],
                file_path=row["file_path"],
                size=row["size"],
                supports_ranges=bool(row["supports_ranges"]),
                status=row["status"],
                downloaded=row["downloaded"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
