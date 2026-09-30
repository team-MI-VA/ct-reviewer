from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from .models import CaseInfo
from .review_screen import ReviewScreen
from .second_quality_checklist import SecondQualityChecklist
from .second_report_store import SecondReportStore


class SecondReviewScreen(ReviewScreen):
    report_store_class = SecondReportStore

    def __init__(self, parent=None) -> None:
        super().__init__(parent, checklist=SecondQualityChecklist())

    def start_review(self, folder: str, report_path: str, min_slices: int, outcome_json: str = "") -> bool:
        del min_slices
        return super().start_review(folder, report_path, 0, outcome_json)

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
                "table_removed": record.table_removed,
                "abdomen_pelvis_cropped_coverage": record.abdomen_pelvis_cropped_coverage,
                "lps_orientation": record.lps_orientation,
                "artifacts_or_problems": record.artifacts_or_problems,
            }
        )

    def _validate_quality_decision(self, status: str) -> bool:
        if not self.checklist.is_complete():
            QMessageBox.warning(
                self,
                "Incomplete checklist",
                "Please complete the second-review checklist before accepting or rejecting.",
            )
            return False

        bad_criteria = self.checklist.bad_criteria()
        if status == "accepted" and bad_criteria:
            QMessageBox.warning(
                self,
                "Accept blocked",
                "This CT can be accepted only when all criteria match their expected values.\n\n"
                + "\n".join(f"- {criterion}" for criterion in bad_criteria),
            )
            return False
        if status == "rejected" and not bad_criteria:
            QMessageBox.warning(
                self,
                "Reject blocked",
                "This CT can be rejected only when at least one criterion differs from its expected value.",
            )
            return False
        return True
