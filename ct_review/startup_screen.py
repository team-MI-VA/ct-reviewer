from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class StartupScreen(QWidget):
    startRequested = Signal(str, str, int, str)

    def __init__(
        self,
        parent=None,
        *,
        title: str = "CT Quality Review",
        subtitle: str = "Select a folder and a CSV report to start reviewing.",
        show_min_slices: bool = True,
        default_report_name: str = "ct_review_report.csv",
    ) -> None:
        super().__init__(parent)
        self.default_report_name = default_report_name
        self.folder_input = QLineEdit()
        self.report_input = QLineEdit()
        self.report_input.textChanged.connect(self._update_report_status)
        self.report_status = QLabel("Select an existing report or create a new one.")
        self.report_status.setObjectName("statusLabel")
        self.outcome_input = QLineEdit()
        self.min_slices_input = QSpinBox()
        self.min_slices_input.setRange(1, 5000)
        self.min_slices_input.setValue(100)

        folder_button = QPushButton("Browse")
        self._disable_enter_activation(folder_button)
        folder_button.clicked.connect(self._choose_folder)
        load_report_button = QPushButton("Load existing")
        self._disable_enter_activation(load_report_button)
        load_report_button.clicked.connect(self._load_existing_report)
        create_report_button = QPushButton("Create new")
        self._disable_enter_activation(create_report_button)
        create_report_button.clicked.connect(self._create_new_report)
        outcome_button = QPushButton("Load JSON")
        self._disable_enter_activation(outcome_button)
        outcome_button.clicked.connect(self._load_outcome_json)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(folder_button)

        report_row = QHBoxLayout()
        report_row.addWidget(self.report_input, 1)
        report_row.addWidget(load_report_button)
        report_row.addWidget(create_report_button)

        outcome_row = QHBoxLayout()
        outcome_row.addWidget(self.outcome_input, 1)
        outcome_row.addWidget(outcome_button)

        form = QFormLayout()
        form.addRow("NIfTI folder", folder_row)
        form.addRow("Report CSV", report_row)
        form.addRow("", self.report_status)
        form.addRow("Outcome JSON", outcome_row)
        if show_min_slices:
            form.addRow("Minimum axial slices", self.min_slices_input)

        title_label = QLabel(title)
        title_label.setObjectName("appTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("subtitle")

        start_button = QPushButton("Start review")
        self._disable_enter_activation(start_button)
        start_button.setObjectName("primaryButton")
        start_button.clicked.connect(self._start)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(16)
        layout.addStretch(1)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(12)
        layout.addLayout(form)
        layout.addWidget(start_button)
        layout.addStretch(2)

    def _disable_enter_activation(self, button: QPushButton) -> None:
        button.setDefault(False)
        button.setAutoDefault(False)

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select NIfTI folder")
        if not folder:
            return
        self.folder_input.setText(folder)
        if not self.report_input.text().strip():
            self.report_input.setText(str(Path(folder) / self.default_report_name))

    def _load_existing_report(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load existing report CSV", filter="CSV files (*.csv)")
        if path:
            self.report_input.setText(path)

    def _create_new_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Create new report CSV", filter="CSV files (*.csv)")
        if path:
            self.report_input.setText(path)

    def _load_outcome_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load outcome JSON", filter="JSON files (*.json)")
        if path:
            self.outcome_input.setText(path)

    def _start(self) -> None:
        folder = Path(self.folder_input.text().strip())
        report = Path(self.report_input.text().strip())
        if not folder.exists() or not folder.is_dir():
            QMessageBox.warning(self, "Invalid folder", "Please select a valid NIfTI folder.")
            return
        if not report.name:
            QMessageBox.warning(self, "Invalid report", "Please select a report CSV path.")
            return
        outcome_path = self.outcome_input.text().strip()
        if outcome_path and not Path(outcome_path).exists():
            QMessageBox.warning(self, "Invalid outcome JSON", "Please select a valid outcome JSON file.")
            return
        self.startRequested.emit(str(folder), str(report), self.min_slices_input.value(), outcome_path)

    def _update_report_status(self) -> None:
        text = self.report_input.text().strip()
        if not text:
            self.report_status.setText("Select an existing report or create a new one.")
            return
        path = Path(text)
        if path.exists():
            self.report_status.setText("Existing report found: previous decisions will be loaded.")
        else:
            self.report_status.setText("New report will be created.")
