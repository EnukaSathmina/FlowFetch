from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow, resolve_asset_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FlowFetch")
    app.setOrganizationName("FlowFetch")
    from PySide6.QtGui import QIcon

    icon = QIcon(str(resolve_asset_path("icon.ico")))
    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
