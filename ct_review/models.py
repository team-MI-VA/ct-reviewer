from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CaseInfo:
    index: int
    file_name: str
    relative_path: str
    absolute_path: Path


@dataclass
class ReviewRecord:
    file_name: str
    file_path: str
    status: str
    comment: str
    z_slices: int
    reviewed_at: str
    include_abdomen_pelvis: str = ""
    include_head: str = ""
    include_chest: str = ""
    sufficient_z_axis: str = ""
    artifacts_or_technical_issues: str = ""
