from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .case_scanner import scan_cases
from .models import CaseInfo
from .nifti_loader import LoadedVolume, load_nifti
from .outcome_store import OUTCOME_FIELDS, OutcomeStore
from .quality_checklist import QualityChecklist
from .range_slider import RangeSlider
from .report_store import ReportStore
from .viewer import SliceViewer


class ReviewScreen(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.cases: list[CaseInfo] = []
        self.folder: Path | None = None
        self.report: ReportStore | None = None
        self.min_slices = 100
        self.outcomes: OutcomeStore | None = None
        self.current_index = 0
        self._current_volume: LoadedVolume | None = None
        self._loaded: dict[str, LoadedVolume] = {}
        self._futures: dict[str, Future] = {}
        self._load_errors: dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        self.sidebar.setVisible(False)
        self.case_list = QListWidget()
        self.case_list.itemClicked.connect(self._case_clicked)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.addWidget(QLabel("Cases"))
        sidebar_layout.addWidget(self.case_list, 1)

        self.toggle_sidebar_button = QPushButton("Files")
        self._disable_enter_activation(self.toggle_sidebar_button)
        self.toggle_sidebar_button.clicked.connect(self._toggle_sidebar)

        self.case_label = QLabel("No case loaded")
        self.case_label.setObjectName("caseTitle")
        self.progress_label = QLabel("")
        self.warning_label = QLabel("")
        self.warning_label.setObjectName("warningLabel")
        self.volume_info_label = QLabel("")
        self.volume_info_label.setObjectName("volumeInfoLabel")
        self.outcome_label = QLabel("")
        self.outcome_label.setObjectName("outcomePanel")
        self.outcome_label.setWordWrap(True)
        self.outcome_label.setVisible(False)

        self.axial_viewer = SliceViewer("Axial", "axial")
        self.coronal_viewer = SliceViewer("Coronal", "coronal")
        self.sagittal_viewer = SliceViewer("Sagittal", "sagittal")
        self.viewers = [self.axial_viewer, self.coronal_viewer, self.sagittal_viewer]

        self.range_slider = RangeSlider()
        self.range_slider.rangeChanged.connect(self._window_changed)
        self.range_label = QLabel("")
        self._window_changed(*self.range_slider.values())
        self.adapt_to_window_check = QCheckBox("Adapt to window")
        self.adapt_to_window_check.setChecked(False)
        self.adapt_to_window_check.toggled.connect(self._adapt_to_window_changed)

        self.comment_box = QTextEdit()
        self.comment_box.setPlaceholderText("Comment")
        self.comment_box.setFixedHeight(48)
        self.comment_box.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.checklist = QualityChecklist()

        self.accept_button = QPushButton("Accept")
        self.reject_button = QPushButton("Reject")
        self.skip_button = QPushButton("Skip")
        for button in (self.accept_button, self.reject_button, self.skip_button):
            self._disable_enter_activation(button)
        self.accept_button.setObjectName("acceptButton")
        self.reject_button.setObjectName("rejectButton")
        self.skip_button.setObjectName("skipButton")
        self.accept_button.clicked.connect(lambda: self._record_decision("accepted"))
        self.reject_button.clicked.connect(lambda: self._record_decision("rejected"))
        self.skip_button.clicked.connect(lambda: self._record_decision("skipped"))

        self._set_action_buttons_enabled(False)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collect_finished_loads)
        self._timer.start(100)
        QApplication.instance().installEventFilter(self)

        self._build_layout()

    def eventFilter(self, watched, event) -> bool:
        del watched
        if not self.isVisible() or event.type() != QEvent.Type.KeyPress:
            return False
        app = QApplication.instance()
        active_window = app.activeWindow()
        if active_window is not None and active_window is not self.window():
            return False
        if event.modifiers() != Qt.KeyboardModifier.NoModifier:
            return False
        focus_widget = app.focusWidget()
        if focus_widget is self.comment_box or (
            focus_widget is not None and self.comment_box.isAncestorOf(focus_widget)
        ):
            return False
        if event.key() == Qt.Key.Key_Right:
            self._go_to_relative_case(1)
            return True
        if event.key() == Qt.Key.Key_Left:
            self._go_to_relative_case(-1)
            return True
        return False

    def _build_layout(self) -> None:
        top_row = QHBoxLayout()
        top_row.addWidget(self.toggle_sidebar_button)
        top_row.addWidget(self.case_label, 1)
        top_row.addWidget(self.progress_label)

        viewer_row = QHBoxLayout()
        viewer_row.setSpacing(12)
        for viewer in self.viewers:
            viewer_row.addWidget(viewer, 1)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("HU range"))
        range_row.addWidget(self.range_slider, 1)
        range_row.addWidget(self.range_label)
        range_row.addWidget(self.adapt_to_window_check)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addWidget(self.accept_button)
        action_row.addWidget(self.reject_button)
        action_row.addWidget(self.skip_button)

        comment_actions = QVBoxLayout()
        comment_actions.setSpacing(8)
        comment_actions.addWidget(QLabel("Comment"))
        comment_actions.addWidget(self.comment_box)
        comment_actions.addLayout(action_row)
        comment_actions.addStretch(1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        bottom_row.addWidget(self.checklist, 3)
        bottom_row.addLayout(comment_actions, 2)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(8)
        content_layout.addLayout(top_row)
        content_layout.addWidget(self.volume_info_label)
        content_layout.addWidget(self.warning_label)
        content_layout.addLayout(viewer_row, 10)
        content_layout.addLayout(range_row)
        content_layout.addWidget(self.outcome_label)
        content_layout.addLayout(bottom_row, 0)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.sidebar)
        root.addWidget(content, 1)

    def _disable_enter_activation(self, button: QPushButton) -> None:
        button.setDefault(False)
        button.setAutoDefault(False)

    def start_review(self, folder: str, report_path: str, min_slices: int, outcome_json: str = "") -> bool:
        self.folder = Path(folder)
        self.report = ReportStore(Path(report_path))
        self.min_slices = min_slices
        self.outcomes = None
        if outcome_json:
            try:
                self.outcomes = OutcomeStore.from_json(Path(outcome_json))
            except Exception as exc:
                QMessageBox.critical(self, "Outcome JSON error", str(exc))
                return False
        self.cases = scan_cases(self.folder)
        self.current_index = 0
        self._current_volume = None
        self._loaded.clear()
        self._futures.clear()
        self._load_errors.clear()
        self._populate_sidebar()
        self.sidebar.setVisible(False)
        self.adapt_to_window_check.setChecked(False)
        if not self.cases:
            QMessageBox.information(self, "No files", "No .nii or .nii.gz files were found in this folder.")
            return False
        self._load_case(0)
        return True

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _populate_sidebar(self) -> None:
        self.case_list.clear()
        for case in self.cases:
            item = QListWidgetItem(self._sidebar_text(case))
            item.setData(Qt.ItemDataRole.UserRole, case.index)
            self._style_item(item, case.file_name)
            self.case_list.addItem(item)

    def _sidebar_text(self, case: CaseInfo) -> str:
        status = self.report.get_status(case.file_name) if self.report else ""
        suffix = f" [{status}]" if status else ""
        return f"{case.index + 1:03d}  {case.file_name}{suffix}"

    def _style_item(self, item: QListWidgetItem, file_name: str) -> None:
        status = self.report.get_status(file_name) if self.report else ""
        colors = {
            "accepted": "#166534",
            "rejected": "#991b1b",
            "skipped": "#6b7280",
        }
        item.setForeground(QColor(colors.get(status, "#111827")))

    def _refresh_sidebar_item(self, index: int) -> None:
        item = self.case_list.item(index)
        if not item:
            return
        case = self.cases[index]
        item.setText(self._sidebar_text(case))
        self._style_item(item, case.file_name)

    def _case_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self._load_case(index)
            self.setFocus()

    def _toggle_sidebar(self) -> None:
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def _load_case(self, index: int) -> None:
        if index < 0 or index >= len(self.cases):
            return
        self.current_index = index
        self._current_volume = None
        case = self.cases[index]
        self.case_label.setText(case.file_name)
        self.progress_label.setText(f"{index + 1} / {len(self.cases)}")
        self.warning_label.setText("")
        self.volume_info_label.setText("")
        self._update_outcome_panel(case)
        self._load_existing_review(case)
        self.case_list.setCurrentRow(index)
        self._set_action_buttons_enabled(False)

        if case.file_name in self._loaded:
            self._display_volume(self._loaded[case.file_name])
        elif case.file_name in self._load_errors:
            self._show_load_error(case)
        else:
            for viewer in self.viewers:
                viewer.clear("Loading...")
            self._ensure_loading(index)

        self._ensure_loading(index + 1)
        self._trim_cache()
        self.setFocus()

    def _ensure_loading(self, index: int) -> None:
        if index < 0 or index >= len(self.cases):
            return
        case = self.cases[index]
        if case.file_name in self._loaded or case.file_name in self._futures:
            return
        self._futures[case.file_name] = self._executor.submit(load_nifti, case.absolute_path)

    def _collect_finished_loads(self) -> None:
        finished = [file_name for file_name, future in self._futures.items() if future.done()]
        for file_name in finished:
            future = self._futures.pop(file_name)
            try:
                self._loaded[file_name] = future.result()
            except Exception as exc:
                self._load_errors[file_name] = str(exc)

        if not self.cases:
            return
        current = self.cases[self.current_index]
        if self._current_volume is None and current.file_name in self._loaded:
            self._display_volume(self._loaded[current.file_name])
        elif self._current_volume is None and current.file_name in self._load_errors:
            self._show_load_error(current)

    def _display_volume(self, volume: LoadedVolume) -> None:
        self._current_volume = volume
        for viewer in self.viewers:
            viewer.set_volume(volume)
        dim_x, dim_y, dim_z = volume.shape
        self.volume_info_label.setText(
            f"Orientation: {volume.orientation}  |  "
            f"Dimensions: {dim_x} x {dim_y} x {dim_z}  |  "
            f"Slice thickness: {volume.slice_thickness:.2f} mm"
        )
        if volume.z_slices < self.min_slices:
            self.warning_label.setText(
                f"Warning: axial slice count is {volume.z_slices}, below configured minimum {self.min_slices}."
            )
        else:
            self.warning_label.setText("")
        existing = self.report.get_record(self.cases[self.current_index].file_name) if self.report else None
        if not existing or not existing.sufficient_z_axis:
            self.checklist.set_sufficient_z_axis_auto(volume.z_slices >= self.min_slices)
        self._set_action_buttons_enabled(True)

    def _show_load_error(self, case: CaseInfo) -> None:
        message = self._load_errors.get(case.file_name, "Unknown loading error")
        for viewer in self.viewers:
            viewer.clear("Load failed")
        self.volume_info_label.setText("")
        self.warning_label.setText(f"Could not load this file: {message}")
        self._set_action_buttons_enabled(False)

    def _window_changed(self, lower: int, upper: int) -> None:
        self.range_label.setText(f"{lower} to {upper} HU")
        for viewer in self.viewers:
            viewer.set_window(lower, upper)

    def _adapt_to_window_changed(self, enabled: bool) -> None:
        for viewer in self.viewers:
            viewer.set_adapt_to_window(enabled)

    def _record_decision(self, status: str) -> None:
        if self.report is None or not self.cases:
            return
        if status in {"accepted", "rejected"} and not self._validate_quality_decision(status):
            return
        case = self.cases[self.current_index]
        volume = self._current_volume
        z_slices = volume.z_slices if volume else 0
        volume_info: dict[str, str] = {}
        if volume is not None:
            dim_x, dim_y, dim_z = volume.shape
            volume_info = {
                "orientation": volume.orientation,
                "slice_thickness": f"{volume.slice_thickness:.3f}",
                "dim_x": str(dim_x),
                "dim_y": str(dim_y),
                "dim_z": str(dim_z),
            }
        self.report.upsert(
            file_name=case.file_name,
            relative_path=case.relative_path,
            status=status,
            comment=self.comment_box.toPlainText().strip(),
            z_slices=z_slices,
            checklist=self.checklist.values(),
            volume_info=volume_info,
        )
        self._refresh_sidebar_item(self.current_index)
        self.comment_box.clear()
        self.checklist.clear()

        next_index = self.current_index + 1
        if next_index < len(self.cases):
            self._load_case(next_index)
        else:
            QMessageBox.information(self, "Review complete", "You reached the end of the case list.")

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        self.accept_button.setEnabled(enabled)
        self.reject_button.setEnabled(enabled)
        self.skip_button.setEnabled(enabled)

    def _go_to_relative_case(self, offset: int) -> None:
        if not self.cases:
            return
        next_index = self.current_index + offset
        if 0 <= next_index < len(self.cases):
            self._load_case(next_index)

    def _update_outcome_panel(self, case: CaseInfo) -> None:
        if self.outcomes is None:
            self.outcome_label.clear()
            self.outcome_label.setVisible(False)
            return
        match = self.outcomes.match_file_name(case.file_name)
        self.outcome_label.setVisible(True)
        if match is None:
            self.outcome_label.setText("Outcome: No outcome match found")
            self.outcome_label.setProperty("matchState", "missing")
            self.outcome_label.style().unpolish(self.outcome_label)
            self.outcome_label.style().polish(self.outcome_label)
            return
        labels = {
            "treatment": "Treatment",
            "CRS": "CRS",
            "sensitivity": "Sensitivity",
            "overall_survival": "Survival",
            "residual_tumor": "Residual tumor",
        }
        parts = [f"{labels[field]}: {match.values.get(field, 'Not available')}" for field in OUTCOME_FIELDS]
        self.outcome_label.setText("Outcome | " + " | ".join(parts))
        self.outcome_label.setProperty("matchState", "found")
        self.outcome_label.style().unpolish(self.outcome_label)
        self.outcome_label.style().polish(self.outcome_label)

    def _load_existing_review(self, case: CaseInfo) -> None:
        self.comment_box.clear()
        self.checklist.clear()
        if not self.report:
            self.checklist.set_default_flags()
            return
        record = self.report.get_record(case.file_name)
        if not record:
            self.checklist.set_default_flags()
            return
        self.comment_box.setPlainText(record.comment)
        self.checklist.set_values(
            {
                "include_abdomen_pelvis": record.include_abdomen_pelvis,
                "include_head": record.include_head,
                "include_chest": record.include_chest,
                "sufficient_z_axis": record.sufficient_z_axis,
                "artifacts_or_technical_issues": record.artifacts_or_technical_issues,
            }
        )

    def _validate_quality_decision(self, status: str) -> bool:
        if not self.checklist.is_complete():
            QMessageBox.warning(
                self,
                "Incomplete checklist",
                "Please complete the CT quality checklist before accepting or rejecting.",
            )
            return False

        accept_blockers = self.checklist.accept_blocking_criteria()
        if status == "accepted" and accept_blockers:
            QMessageBox.warning(
                self,
                "Accept blocked",
                "This CT can be accepted only when these criteria are Yes:\n\n"
                + "\n".join(f"- {criterion}" for criterion in accept_blockers),
            )
            return False
        reject_criteria = self.checklist.reject_supporting_criteria()
        if status == "rejected" and not reject_criteria:
            QMessageBox.warning(
                self,
                "Reject blocked",
                "This CT can be rejected only if abdomen/pelvis or z-axis is No, or artifacts/problems is Yes.",
            )
            return False
        return True

    def _trim_cache(self) -> None:
        keep = set()
        for index in (self.current_index - 1, self.current_index, self.current_index + 1):
            if 0 <= index < len(self.cases):
                keep.add(self.cases[index].file_name)
        for file_name in list(self._loaded):
            if file_name not in keep:
                self._loaded.pop(file_name, None)
