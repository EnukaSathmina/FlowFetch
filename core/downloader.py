from __future__ import annotations

import time
from pathlib import Path

import requests
from PySide6.QtCore import QObject, QThread, Signal


class DownloadWorker(QObject):
    progress = Signal(str, int, int, float, float)
    status_changed = Signal(str, str)
    error = Signal(str, str)
    finished = Signal(str, str, int, str)

    def __init__(
        self,
        download_id: str,
        url: str,
        target_path: Path,
        expected_size: int | None = None,
        supports_ranges: bool = False,
    ) -> None:
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.target_path = target_path
        self.expected_size = expected_size
        self.supports_ranges = supports_ranges
        self._is_paused = False
        self._is_cancelled = False
        self._bytes_done = 0

    def cancel(self) -> None:
        self._is_cancelled = True
        self._is_paused = False

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def run(self) -> None:
        try:
            self._run_download()
        except requests.exceptions.InvalidURL:
            self._fail("Please enter a valid URL starting with http:// or https://")
        except requests.exceptions.MissingSchema:
            self._fail("Please enter a valid URL starting with http:// or https://")
        except requests.exceptions.ConnectionError:
            self._fail("Could not connect to the server.")
        except requests.exceptions.Timeout:
            self._fail("The server took too long to respond.")
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 404:
                self._fail("File not found on the server.")
            else:
                reason = getattr(exc.response, "reason", "Error")
                self._fail(f"Download failed: HTTP {status_code} {reason}")
        except requests.exceptions.RequestException as exc:
            self._fail(self._format_request_error(exc))
        except PermissionError:
            self._fail("Cannot save to this folder. Choose another location.")
        except OSError as exc:
            self._fail(f"Download failed: {exc}")
        except Exception as exc:
            self._fail(f"Unexpected download error: {exc}")

    def _run_download(self) -> None:
        bytes_done = self.target_path.stat().st_size if self.target_path.exists() else 0
        headers = {}
        mode = "wb"

        if self.supports_ranges and bytes_done > 0:
            headers["Range"] = f"bytes={bytes_done}-"
            mode = "ab"
        elif bytes_done > 0:
            self.target_path.unlink(missing_ok=True)
            bytes_done = 0
        self._bytes_done = bytes_done

        self.status_changed.emit(self.download_id, "Downloading")
        started = time.monotonic()
        window_started = started
        window_bytes = bytes_done
        total_size = self.expected_size or 0
        pause_emitted = False

        with requests.get(self.url, stream=True, headers=headers, timeout=15) as response:
            if response.status_code >= 400:
                raise requests.exceptions.HTTPError(
                    f"HTTP {response.status_code} {response.reason}",
                    response=response,
                )

            if response.status_code == 200 and mode == "ab":
                mode = "wb"
                bytes_done = 0
                window_bytes = 0

            content_length = response.headers.get("content-length")
            if total_size <= 0 and content_length and content_length.isdigit():
                total_size = int(content_length) + bytes_done

            self.target_path.parent.mkdir(parents=True, exist_ok=True)
            with self.target_path.open(mode) as file:
                for chunk in response.iter_content(chunk_size=1024 * 128):
                    if self._is_cancelled:
                        self.status_changed.emit(self.download_id, "Cancelled")
                        self.finished.emit(self.download_id, "Cancelled", bytes_done, "")
                        return

                    while self._is_paused and not self._is_cancelled:
                        if not pause_emitted:
                            self.progress.emit(self.download_id, bytes_done, total_size, 0.0, -1.0)
                            self.status_changed.emit(self.download_id, "Paused")
                            pause_emitted = True
                        time.sleep(0.1)

                    if self._is_cancelled:
                        self.status_changed.emit(self.download_id, "Cancelled")
                        self.finished.emit(self.download_id, "Cancelled", bytes_done, "")
                        return

                    if pause_emitted:
                        self.status_changed.emit(self.download_id, "Downloading")
                        window_started = time.monotonic()
                        window_bytes = bytes_done
                        pause_emitted = False

                    if not chunk:
                        continue

                    file.write(chunk)
                    bytes_done += len(chunk)
                    self._bytes_done = bytes_done

                    now = time.monotonic()
                    if now - window_started >= 1 or (total_size and bytes_done >= total_size):
                        elapsed = max(now - window_started, 0.001)
                        speed = (bytes_done - window_bytes) / elapsed
                        remaining = max(total_size - bytes_done, 0) if total_size else 0
                        eta = remaining / speed if speed > 0 and total_size else -1.0
                        self.progress.emit(self.download_id, bytes_done, total_size, speed, eta)
                        window_started = now
                        window_bytes = bytes_done

        self.progress.emit(self.download_id, bytes_done, total_size, 0.0, 0.0)
        self.status_changed.emit(self.download_id, "Completed")
        self.finished.emit(self.download_id, "Completed", bytes_done, "")

    def _format_request_error(self, exc: requests.exceptions.RequestException) -> str:
        if exc.response is not None and exc.response.status_code >= 400:
            if exc.response.status_code == 404:
                return "File not found on the server."
            return f"Download failed: HTTP {exc.response.status_code} {exc.response.reason}"
        return f"Download failed: {exc}"

    def _fail(self, message: str) -> None:
        self.error.emit(self.download_id, message)
        self.status_changed.emit(self.download_id, "Failed")
        self.finished.emit(self.download_id, "Failed", self._bytes_done, message)


class DownloadTask(QObject):
    progress = Signal(str, int, int, float, float)
    status_changed = Signal(str, str)
    error = Signal(str, str)
    finished = Signal(str, str, int, str)

    def __init__(
        self,
        download_id: str,
        url: str,
        target_path: Path,
        expected_size: int | None = None,
        supports_ranges: bool = False,
    ) -> None:
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.target_path = target_path
        self.expected_size = expected_size
        self.supports_ranges = supports_ranges
        self.thread = QThread()
        self.worker = DownloadWorker(download_id, url, target_path, expected_size, supports_ranges)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress)
        self.worker.status_changed.connect(self.status_changed)
        self.worker.error.connect(self.error)
        self.worker.finished.connect(self.finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

    def start(self) -> None:
        self.thread.start()

    def pause(self) -> None:
        self.worker.pause()

    def resume(self) -> None:
        self.worker.resume()

    def cancel(self) -> None:
        self.worker.cancel()
