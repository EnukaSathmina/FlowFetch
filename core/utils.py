from __future__ import annotations

import json
import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests


APP_DIR = Path(
    os.environ.get(
        "FLOWFETCH_HOME",
        Path(os.environ.get("LOCALAPPDATA", Path.home())) / "FlowFetch",
    )
)
DB_PATH = APP_DIR / "flowfetch.sqlite3"
SETTINGS_PATH = APP_DIR / "settings.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"
DEFAULT_SETTINGS = {
    "download_folder": str(DEFAULT_DOWNLOAD_DIR),
    "max_simultaneous": 3,
    "duplicate_file_behavior": "Auto rename duplicate files",
    "auto_category_folders": False,
    "auto_start_downloads": False,
    "auto_retry_failed": False,
    "retry_count": 2,
    "speed_limit_enabled": False,
    "speed_limit_mbps": 10.0,
    "show_total_speed": True,
    "speed_update_interval": "1 second",
    "theme_mode": "Dark",
    "accent_color": "Blue",
    "show_sidebar_icons": True,
    "confirm_delete_files": True,
    "minimize_to_tray": False,
    "show_notifications": True,
    "save_history": True,
}


def ensure_app_dirs() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def safe_filename(name: str) -> str:
    cleaned = unquote(name).strip().strip(".")
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:180] if cleaned else "download"


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).name
    return safe_filename(candidate or "download")


def unique_path(folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    base = safe_filename(filename)
    candidate = folder / base
    if not candidate.exists():
        return candidate

    stem = candidate.stem or "download"
    suffix = candidate.suffix
    index = 1
    while True:
        next_candidate = folder / f"{stem} ({index}){suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def format_bytes(value: int | float | None) -> str:
    if value is None or value < 0:
        return "Unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def format_speed(bytes_per_second: float) -> str:
    if bytes_per_second <= 0:
        return "0 B/s"
    return f"{format_bytes(bytes_per_second)}/s"


def format_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}h {minutes:02d}m"
    if minutes:
        return f"{minutes:d}m {secs:02d}s"
    return f"{secs:d}s"


def detect_remote_file(url: str, timeout: int = 8) -> tuple[str, int | None, bool]:
    filename = filename_from_url(url)
    size: int | None = None
    supports_ranges = False

    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        if response.ok:
            content_disposition = response.headers.get("content-disposition", "")
            match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', content_disposition, re.I)
            if match:
                filename = safe_filename(match.group(1))
            elif not Path(urlparse(response.url).path).name and response.headers.get("content-type"):
                extension = mimetypes.guess_extension(response.headers["content-type"].split(";")[0].strip())
                if extension:
                    filename = f"download{extension}"

            content_length = response.headers.get("content-length")
            if content_length and content_length.isdigit():
                size = int(content_length)
            supports_ranges = response.headers.get("accept-ranges", "").lower() == "bytes"
    except requests.RequestException:
        pass
    except Exception:
        pass

    return filename, size, supports_ranges


def load_settings() -> dict:
    ensure_app_dirs()
    defaults = DEFAULT_SETTINGS.copy()
    if not SETTINGS_PATH.exists():
        save_settings(defaults)
        return defaults
    try:
        stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(stored, dict):
        return defaults
    if "theme" in stored and "theme_mode" not in stored:
        stored["theme_mode"] = stored["theme"]
    merged = defaults | {key: stored[key] for key in defaults.keys() & stored.keys()}
    return merged


def save_settings(settings: dict) -> None:
    ensure_app_dirs()
    payload = DEFAULT_SETTINGS.copy()
    payload.update(settings)
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def reveal_in_file_manager(path: Path) -> None:
    folder = path if path.is_dir() else path.parent
    os.startfile(str(folder))
