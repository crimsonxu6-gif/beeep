from __future__ import annotations

from schemas import SubjectPreflightResult
from services.bbox_safety import validate_composition_bbox


def subject(bbox=(0.25, 0.1, 0.75, 0.9)) -> SubjectPreflightResult:
    return SubjectPreflightResult(
        state="confirmed",
        detected=True,
        allow_shuttermuse=True,
        confidence=0.9,
        bbox_norm=bbox,
        face_detected=True,
        detection_source="face",
        face_confidence=0.9,
        reason_code="face_confirmed",
    )


def test_safe_bbox_preserves_subject_and_target_ratio() -> None:
    result = validate_composition_bbox(
        (0.0, 0.0, 1.0, 1.0),
        subject(),
        None,
        "auto",
        target_ratio="3:4",
        image_width=750,
        image_height=1000,
    )
    assert result.passed is True
    assert result.displayable is True


def test_head_cut_bbox_is_rejected_without_repair() -> None:
    result = validate_composition_bbox(
        (0.2, 0.3, 0.8, 0.9),
        subject(),
        None,
        "auto",
        target_ratio="3:4",
        image_width=750,
        image_height=1000,
        ratio_tolerance=1,
    )
    assert result.passed is False
    assert "head_cut_risk" in result.rejection_reasons


def test_full_body_mode_requires_more_subject_preservation() -> None:
    result = validate_composition_bbox(
        (0.2, 0.08, 0.8, 0.82),
        subject(),
        None,
        "full_body",
        target_ratio="3:4",
        image_width=750,
        image_height=1000,
        ratio_tolerance=1,
    )
    assert "full_body_not_preserved" in result.rejection_reasons
