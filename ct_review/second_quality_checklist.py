from __future__ import annotations

from .quality_checklist import QualityChecklist


SECOND_REVIEW_ITEMS = [
    ("table_removed", "Table removed", True),
    ("abdomen_pelvis_cropped_coverage", "Abdomen/pelvis cropped coverage", True),
    ("lps_orientation", "LPS orientation", True),
    ("artifacts_or_problems", "Artifacts/problems", False),
]

SECOND_REVIEW_DEFAULTS = {
    "table_removed": "yes",
    "abdomen_pelvis_cropped_coverage": "yes",
    "lps_orientation": "yes",
    "artifacts_or_problems": "no",
}


class SecondQualityChecklist(QualityChecklist):
    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            items=SECOND_REVIEW_ITEMS,
            default_flags=SECOND_REVIEW_DEFAULTS,
        )

    def accept_blocking_criteria(self) -> list[str]:
        return self.bad_criteria()

    def reject_supporting_criteria(self) -> list[str]:
        return self.bad_criteria()
