from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QSlider, QVBoxLayout, QWidget

from .nifti_loader import LoadedVolume, display_spacing, slice_count, slice_for_view, window_to_uint8


class SliceViewer(QWidget):
    def __init__(self, title: str, view: str, parent=None) -> None:
        super().__init__(parent)
        self.view = view
        self._volume: LoadedVolume | None = None
        self._lower = -160
        self._upper = 240
        self._last_slice: np.ndarray | None = None
        self._adapt_to_window = False

        self.title_label = QLabel(title)
        self.title_label.setObjectName("panelTitle")
        self.image_label = QLabel("No image")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(220, 220)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setObjectName("imageCanvas")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._render_current)

        self.count_label = QLabel("0 / 0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setObjectName("sliceCounter")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.image_label, 10)
        layout.addWidget(self.slider)
        layout.addWidget(self.count_label)

    def set_volume(self, volume: LoadedVolume) -> None:
        self._volume = volume
        count = slice_count(volume, self.view)
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(0, count - 1))
        self.slider.setValue(max(0, count // 2))
        self.slider.setEnabled(count > 0)
        self.slider.blockSignals(False)
        self._render_current()

    def clear(self, text: str = "Loading...") -> None:
        self._volume = None
        self._last_slice = None
        self.slider.setEnabled(False)
        self.slider.setRange(0, 0)
        self.count_label.setText("0 / 0")
        self.image_label.setText(text)
        self.image_label.setPixmap(QPixmap())

    def set_window(self, lower: int, upper: int) -> None:
        self._lower = lower
        self._upper = upper
        self._render_current()

    def set_adapt_to_window(self, enabled: bool) -> None:
        self._adapt_to_window = enabled
        self._paint_slice()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._paint_slice()

    def _render_current(self) -> None:
        if self._volume is None:
            return
        index = self.slider.value()
        total = slice_count(self._volume, self.view)
        self.count_label.setText(f"{index + 1} / {total}")
        self._last_slice = slice_for_view(self._volume, self.view, index)
        self._paint_slice()

    def _paint_slice(self) -> None:
        if self._last_slice is None:
            return
        image = window_to_uint8(self._last_slice, self._lower, self._upper)
        image = np.ascontiguousarray(image)
        height, width = image.shape
        qimage = QImage(image.data, width, height, width, QImage.Format.Format_Grayscale8).copy()
        pixmap = QPixmap.fromImage(qimage)
        target_width, target_height = self._target_display_size(width, height)
        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.image_label.setPixmap(scaled)

    def _target_display_size(self, image_width: int, image_height: int) -> tuple[int, int]:
        label_width = max(1, self.image_label.width())
        label_height = max(1, self.image_label.height())
        if self._adapt_to_window:
            return label_width, label_height
        if self._volume is None:
            return label_width, label_height

        column_spacing, row_spacing = display_spacing(self._volume, self.view)
        physical_width = max(1e-6, image_width * column_spacing)
        physical_height = max(1e-6, image_height * row_spacing)
        physical_aspect = physical_width / physical_height
        label_aspect = label_width / label_height

        if physical_aspect >= label_aspect:
            target_width = label_width
            target_height = round(label_width / physical_aspect)
        else:
            target_height = label_height
            target_width = round(label_height * physical_aspect)

        return max(1, target_width), max(1, target_height)
