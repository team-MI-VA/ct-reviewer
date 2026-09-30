from __future__ import annotations

import csv
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CHECKLIST_FIELDNAMES = [
    "table_removed",
    "abdomen_pelvis_cropped_coverage",
    "lps_orientation",
    "artifacts_or_problems",
]
VOLUME_FIELDNAMES = ["orientation", "slice_thickness", "dim_x", "dim_y", "dim_z"]
FIELDNAMES = [
    "file_name",
    "file_path",
    "status",
    "comment",
    "z_slices",
    *CHECKLIST_FIELDNAMES,
    *VOLUME_FIELDNAMES,
    "reviewed_at",
]


@dataclass
class SecondReviewRecord:
    file_name: str
    file_path: str
    status: str
    comment: str
    z_slices: int
    reviewed_at: str
    table_removed: str = ""
    abdomen_pelvis_cropped_coverage: str = ""
    lps_orientation: str = ""
    artifacts_or_problems: str = ""
    orientation: str = ""
    slice_thickness: str = ""
    dim_x: str = ""
    dim_y: str = ""
    dim_z: str = ""


class SecondReportStore:
    def __init__(self, report_path: Path) -> None:
        self.report_path = Path(report_path)
        self.records: OrderedDict[str, SecondReviewRecord] = OrderedDict()
        if self.report_path.exists():
            self._load()

    def _load(self) -> None:
        with self.report_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                file_name = row.get("file_name", "").strip()
                if not file_name:
                    continue
                try:
                    z_slices = int(row.get("z_slices") or 0)
                except ValueError:
                    z_slices = 0
                values = {field: row.get(field, "") for field in CHECKLIST_FIELDNAMES + VOLUME_FIELDNAMES}
                self.records[file_name] = SecondReviewRecord(
                    file_name=file_name,
                    file_path=row.get("file_path", ""),
                    status=row.get("status", ""),
                    comment=row.get("comment", ""),
                    z_slices=z_slices,
                    reviewed_at=row.get("reviewed_at", ""),
                    **values,
                )

    def get_status(self, file_name: str) -> str:
        record = self.records.get(file_name)
        return record.status if record else ""

    def get_record(self, file_name: str) -> SecondReviewRecord | None:
        return self.records.get(file_name)

    def upsert(
        self,
        *,
        file_name: str,
        relative_path: str,
        status: str,
        comment: str,
        z_slices: int,
        checklist: dict[str, str] | None = None,
        volume_info: dict[str, str] | None = None,
    ) -> None:
        checklist = checklist or {}
        volume_info = volume_info or {}
        self.records[file_name] = SecondReviewRecord(
            file_name=file_name,
            file_path=relative_path,
            status=status,
            comment=comment,
            z_slices=z_slices,
            table_removed=checklist.get("table_removed", ""),
            abdomen_pelvis_cropped_coverage=checklist.get("abdomen_pelvis_cropped_coverage", ""),
            lps_orientation=checklist.get("lps_orientation", ""),
            artifacts_or_problems=checklist.get("artifacts_or_problems", ""),
            orientation=volume_info.get("orientation", ""),
            slice_thickness=volume_info.get("slice_thickness", ""),
            dim_x=volume_info.get("dim_x", ""),
            dim_y=volume_info.get("dim_y", ""),
            dim_z=volume_info.get("dim_z", ""),
            reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self.save()

    def save(self) -> None:
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        with self.report_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            for record in self.records.values():
                writer.writerow({field: getattr(record, field) for field in FIELDNAMES})
