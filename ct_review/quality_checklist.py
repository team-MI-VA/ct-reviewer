from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


CHECKLIST_ITEMS = [
    ("include_abdomen_pelvis", "Includes abdomen/pelvis", True),
    ("include_head", "Includes head", True),
    ("include_chest", "Includes chest", True),
    ("sufficient_z_axis", "Sufficient z axis", True),
    ("artifacts_or_technical_issues", "Artifacts/problems", False),
]

LABELS_BY_KEY = {key: label for key, label, _good_when_yes in CHECKLIST_ITEMS}

DEFAULT_FLAGS = {
    "include_abdomen_pelvis": "yes",
    "include_head": "no",
    "include_chest": "yes",
    "artifacts_or_technical_issues": "no",
}


class QualityChecklist(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, tuple[QRadioButton, QRadioButton]] = {}
        self._groups: list[QButtonGroup] = []
        self._button_groups: dict[QRadioButton, QButtonGroup] = {}

        title = QLabel("Quality checklist")
        title.setObjectName("panelTitle")
        clear_button = QPushButton("Clear checklist")
        self._disable_enter_activation(clear_button)
        clear_button.setObjectName("compactButton")
        clear_button.clicked.connect(self.clear)

        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(clear_button)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)
        grid.addWidget(QLabel("Criterion"), 0, 0)
        grid.addWidget(QLabel("Yes"), 0, 1)
        grid.addWidget(QLabel("No"), 0, 2)

        for row, (key, label, _good_when_yes) in enumerate(CHECKLIST_ITEMS, start=1):
            yes_button = QRadioButton()
            no_button = QRadioButton()
            group = QButtonGroup(self)
            group.setExclusive(True)
            group.addButton(yes_button)
            group.addButton(no_button)
            self._groups.append(group)
            self._button_groups[yes_button] = group
            self._button_groups[no_button] = group
            self._buttons[key] = (yes_button, no_button)
            yes_button.installEventFilter(self)
            no_button.installEventFilter(self)

            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(yes_button, row, 1)
            grid.addWidget(no_button, row, 2)

        frame = QFrame()
        frame.setObjectName("checklistFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 8, 10, 8)
        frame_layout.setSpacing(4)
        frame_layout.addLayout(title_row)
        frame_layout.addLayout(grid)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(frame)

    def values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, (yes_button, no_button) in self._buttons.items():
            if yes_button.isChecked():
                values[key] = "yes"
            elif no_button.isChecked():
                values[key] = "no"
            else:
                values[key] = ""
        return values

    def _disable_enter_activation(self, button: QPushButton) -> None:
        button.setDefault(False)
        button.setAutoDefault(False)

    def set_values(self, values: dict[str, str]) -> None:
        self.clear()
        for key, value in values.items():
            buttons = self._buttons.get(key)
            if not buttons:
                continue
            yes_button, no_button = buttons
            if value == "yes":
                yes_button.setChecked(True)
            elif value == "no":
                no_button.setChecked(True)

    def clear(self) -> None:
        for group in self._groups:
            checked = group.checkedButton()
            if checked:
                self._clear_button(checked)

    def eventFilter(self, watched, event) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and isinstance(watched, QRadioButton)
            and watched.isChecked()
        ):
            self._clear_button(watched)
            return True
        return super().eventFilter(watched, event)

    def _clear_button(self, button: QRadioButton) -> None:
        group = self._button_groups.get(button)
        if group is None:
            return
        group.setExclusive(False)
        button.setChecked(False)
        group.setExclusive(True)

    def set_default_flags(self) -> None:
        for key, value in DEFAULT_FLAGS.items():
            yes_button, no_button = self._buttons[key]
            if value == "yes":
                yes_button.setChecked(True)
            else:
                no_button.setChecked(True)

    def set_sufficient_z_axis_auto(self, sufficient: bool) -> None:
        yes_button, no_button = self._buttons["sufficient_z_axis"]
        yes_button.setChecked(sufficient)
        no_button.setChecked(not sufficient)

    def is_complete(self) -> bool:
        return all(value in {"yes", "no"} for value in self.values().values())

    def bad_criteria(self) -> list[str]:
        values = self.values()
        bad: list[str] = []
        for key, label, good_when_yes in CHECKLIST_ITEMS:
            value = values.get(key, "")
            if not value:
                continue
            is_good = (value == "yes") if good_when_yes else (value == "no")
            if not is_good:
                bad.append(label)
        return bad

    def is_quality_good(self) -> bool:
        return self.is_complete() and not self.bad_criteria()

    def accept_blocking_criteria(self) -> list[str]:
        values = self.values()
        blockers: list[str] = []
        for key in ("include_abdomen_pelvis", "sufficient_z_axis"):
            if values.get(key) != "yes":
                blockers.append(LABELS_BY_KEY[key])
        return blockers

    def reject_supporting_criteria(self) -> list[str]:
        values = self.values()
        criteria: list[str] = []
        for key in ("include_abdomen_pelvis", "sufficient_z_axis"):
            if values.get(key) == "no":
                criteria.append(LABELS_BY_KEY[key])
        if values.get("artifacts_or_technical_issues") == "yes":
            criteria.append(LABELS_BY_KEY["artifacts_or_technical_issues"])
        return criteria
