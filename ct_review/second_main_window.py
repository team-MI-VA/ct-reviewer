from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .main_window import APP_ICON_PATH, STYLE, MainWindow, _set_windows_app_user_model_id
from .second_review_screen import SecondReviewScreen
from .startup_screen import StartupScreen


WINDOWS_APP_USER_MODEL_ID = "ct_review.second_review.viewer"


class SecondReviewerMainWindow(MainWindow):
    def __init__(self) -> None:
        startup = StartupScreen(
            title="CT Second Review",
            subtitle="Select a folder and a second-review CSV report to start reviewing.",
            show_min_slices=False,
            default_report_name="ct_second_review_report.csv",
        )
        super().__init__(
            window_title="CT Second Review",
            startup=startup,
            review=SecondReviewScreen(),
        )


def main() -> None:
    _set_windows_app_user_model_id(WINDOWS_APP_USER_MODEL_ID)
    app = QApplication(sys.argv)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    app.setStyleSheet(STYLE)
    window = SecondReviewerMainWindow()
    window.show()
    sys.exit(app.exec())
