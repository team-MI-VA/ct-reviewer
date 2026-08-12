from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from .review_screen import ReviewScreen
from .startup_screen import StartupScreen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ICON_PATH = PROJECT_ROOT / "assets" / "app_icon.png"
WINDOWS_APP_USER_MODEL_ID = "ct_review.quality_review.viewer"


STYLE = """
QWidget {
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
    color: #111827;
    background: #f8fafc;
}
QLineEdit, QTextEdit, QSpinBox, QListWidget {
    background: #ffffff;
    border: 1px solid #cfd6e1;
    border-radius: 6px;
    padding: 6px;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #c7ced8;
    border-radius: 6px;
    padding: 7px 12px;
}
QPushButton:hover {
    background: #f1f5f9;
}
QPushButton:disabled {
    color: #9ca3af;
    background: #eef2f7;
}
#primaryButton, #acceptButton {
    background: #2563eb;
    color: white;
    border-color: #2563eb;
}
#rejectButton {
    background: #b91c1c;
    color: white;
    border-color: #b91c1c;
}
#skipButton {
    background: #4b5563;
    color: white;
    border-color: #4b5563;
}
#appTitle {
    font-size: 30px;
    font-weight: 700;
}
#subtitle {
    color: #4b5563;
}
#statusLabel {
    color: #4b5563;
}
#caseTitle {
    font-size: 18px;
    font-weight: 650;
}
#panelTitle {
    font-weight: 650;
}
#imageCanvas {
    background: #050505;
    border: 1px solid #111827;
    border-radius: 4px;
}
#sliceCounter {
    color: #4b5563;
}
#sidebar {
    background: #eef2f7;
    border-right: 1px solid #cfd6e1;
}
#warningLabel {
    color: #92400e;
}
#volumeInfoLabel {
    color: #4b5563;
}
#outcomePanel {
    background: #ffffff;
    border: 1px solid #cfd6e1;
    border-radius: 6px;
    padding: 6px 8px;
    color: #374151;
}
#outcomePanel[matchState="missing"] {
    color: #92400e;
    border-color: #f59e0b;
}
#checklistFrame {
    background: #ffffff;
    border: 1px solid #cfd6e1;
    border-radius: 6px;
}
#compactButton {
    padding: 4px 8px;
}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CT Quality Review")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(1280, 820)

        self.stack = QStackedWidget()
        self.startup = StartupScreen()
        self.review = ReviewScreen()
        self.stack.addWidget(self.startup)
        self.stack.addWidget(self.review)
        self.setCentralWidget(self.stack)

        self.startup.startRequested.connect(self._start_review)

    def _start_review(self, folder: str, report: str, min_slices: int, outcome_json: str) -> None:
        if self.review.start_review(folder, report, min_slices, outcome_json):
            self.stack.setCurrentWidget(self.review)

    def closeEvent(self, event) -> None:
        self.review.shutdown()
        super().closeEvent(event)


def main() -> None:
    _set_windows_app_user_model_id()
    app = QApplication(sys.argv)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def _set_windows_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_USER_MODEL_ID)
    except Exception:
        pass
