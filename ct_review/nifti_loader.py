from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np


@dataclass(frozen=True)
class LoadedVolume:
    path: Path
    data: np.ndarray
    voxel_sizes: tuple[float, float, float]
    orientation: str

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.data.shape

    @property
    def z_slices(self) -> int:
        return self.data.shape[2]

    @property
    def slice_thickness(self) -> float:
        return self.voxel_sizes[2]


def load_nifti(path: Path) -> LoadedVolume:
    image = nib.load(str(path))
    orientation = "".join(nib.aff2axcodes(image.affine))
    canonical = nib.as_closest_canonical(image)
    data = canonical.get_fdata(dtype=np.float32)
    data = np.nan_to_num(data, copy=False)

    zooms = canonical.header.get_zooms()[:3]
    voxel_sizes = tuple(float(value) for value in zooms)
    return LoadedVolume(path=Path(path), data=data, voxel_sizes=voxel_sizes, orientation=orientation)


def slice_for_view(volume: LoadedVolume, view: str, index: int) -> np.ndarray:
    data = volume.data
    if view == "axial":
        return np.flipud(np.fliplr(np.transpose(data[:, :, index])))
    if view == "coronal":
        return np.flipud(np.fliplr(np.transpose(data[:, index, :])))
    if view == "sagittal":
        return np.flipud(np.fliplr(np.transpose(data[index, :, :])))
    raise ValueError(f"Unsupported view: {view}")


def slice_count(volume: LoadedVolume, view: str) -> int:
    if view == "sagittal":
        return volume.shape[0]
    if view == "coronal":
        return volume.shape[1]
    if view == "axial":
        return volume.shape[2]
    raise ValueError(f"Unsupported view: {view}")


def display_spacing(volume: LoadedVolume, view: str) -> tuple[float, float]:
    """Return column and row spacing for the 2D slice produced by slice_for_view."""
    x_spacing, y_spacing, z_spacing = volume.voxel_sizes
    if view == "axial":
        return x_spacing, y_spacing
    if view == "coronal":
        return x_spacing, z_spacing
    if view == "sagittal":
        return y_spacing, z_spacing
    raise ValueError(f"Unsupported view: {view}")


def window_to_uint8(slice_2d: np.ndarray, lower: int, upper: int) -> np.ndarray:
    if upper <= lower:
        upper = lower + 1
    clipped = np.clip(slice_2d, lower, upper)
    scaled = (clipped - lower) / float(upper - lower)
    return np.asarray(scaled * 255, dtype=np.uint8)
