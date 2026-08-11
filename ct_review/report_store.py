from __future__ import annotations

import csv
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from .models import ReviewRecord


CHECKLIST_FIELDNAMES = [
    "include_abdomen_pelvis",
    "include_head",
    "include_chest",
    "sufficient_z_axis",
    "artifacts_or_technical_issues",
]
FIELDNAMES = ["file_name", "file_path", "status", "comment", "z_slices", *CHECKLIST_FIELDNAMES, "reviewed_at"]


class ReportStore:
    def __init__(self, report_path: Path) -> None:
        self.report_path = Path(report_path)
        self.records: OrderedDict[str, ReviewRecord] = OrderedDict()
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
                self.records[file_name] = ReviewRecord(
                    file_name=file_name,
                    file_path=row.get("file_path", ""),
                    status=row.get("status", ""),
                    comment=row.get("comment", ""),
                    z_slices=z_slices,
                    include_abdomen_pelvis=_read_abdomen_pelvis(row),
                    include_head=row.get("include_head", ""),
                    include_chest=row.get("include_chest", ""),
                    sufficient_z_axis=row.get("sufficient_z_axis", ""),
                    artifacts_or_technical_issues=row.get("artifacts_or_technical_issues", ""),
                    reviewed_at=row.get("reviewed_at", ""),
                )

    def get_status(self, file_name: str) -> str:
        record = self.records.get(file_name)
        return record.status if record else ""

    def get_record(self, file_name: str) -> ReviewRecord | None:
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
    ) -> None:
        checklist = checklist or {}
        self.records[file_name] = ReviewRecord(
            file_name=file_name,
            file_path=relative_path,
            status=status,
            comment=comment,
            z_slices=z_slices,
            include_abdomen_pelvis=checklist.get("include_abdomen_pelvis", ""),
            include_head=checklist.get("include_head", ""),
            include_chest=checklist.get("include_chest", ""),
            sufficient_z_axis=checklist.get("sufficient_z_axis", ""),
            artifacts_or_technical_issues=checklist.get("artifacts_or_technical_issues", ""),
            reviewed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self.save()

    def save(self) -> None:
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        with self.report_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            for record in self.records.values():
                writer.writerow(
                    {
                        "file_name": record.file_name,
                        "file_path": record.file_path,
                        "status": record.status,
                        "comment": record.comment,
                        "z_slices": record.z_slices,
                        "include_abdomen_pelvis": record.include_abdomen_pelvis,
                        "include_head": record.include_head,
                        "include_chest": record.include_chest,
                        "sufficient_z_axis": record.sufficient_z_axis,
                        "artifacts_or_technical_issues": record.artifacts_or_technical_issues,
                        "reviewed_at": record.reviewed_at,
                    }
                )


def _read_abdomen_pelvis(row: dict[str, str]) -> str:
    combined = row.get("include_abdomen_pelvis", "")
    if combined:
        return combined
    abdomen = row.get("include_abdomen", "")
    pelvis = row.get("include_pelvis", "")
    if abdomen == "yes" and pelvis == "yes":
        return "yes"
    if abdomen == "no" or pelvis == "no":
        return "no"
    return ""
