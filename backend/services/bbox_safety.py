from __future__ import annotations

from schemas import BBoxSafetyResult, SubjectPreflightResult, VisionFeatures

TARGET_RATIOS = {
    "1:1": 1.0,
    "3:4": 3 / 4,
    "4:3": 4 / 3,
    "9:16": 9 / 16,
    "16:9": 16 / 9,
}


def _intersection_ratio(
    container: tuple[float, float, float, float],
    subject: tuple[float, float, float, float],
) -> float:
    cx1, cy1, cx2, cy2 = container
    sx1, sy1, sx2, sy2 = subject
    subject_area = max(0.0, sx2 - sx1) * max(0.0, sy2 - sy1)
    if subject_area <= 0:
        return 0.0
    width = max(0.0, min(cx2, sx2) - max(cx1, sx1))
    height = max(0.0, min(cy2, sy2) - max(cy1, sy1))
    return (width * height) / subject_area


def validate_composition_bbox(
    bbox_norm: tuple[float, float, float, float],
    subject_preflight: SubjectPreflightResult | None,
    vision_features: VisionFeatures | None,
    composition_mode: str,
    *,
    target_ratio: str,
    image_width: int,
    image_height: int,
    minimum_area: float = 0.12,
    ratio_tolerance: float = 0.20,
) -> BBoxSafetyResult:
    """Validate a model bbox without repairing or replacing it."""
    x1, y1, x2, y2 = bbox_norm
    reasons: list[str] = []
    area = (x2 - x1) * (y2 - y1)
    if area < minimum_area:
        reasons.append("bbox_too_small")

    expected_ratio = TARGET_RATIOS[target_ratio]
    actual_ratio = ((x2 - x1) * image_width) / ((y2 - y1) * image_height)
    ratio_error = abs(actual_ratio - expected_ratio) / expected_ratio
    if ratio_error > ratio_tolerance:
        reasons.append("target_ratio_mismatch")

    subject_bbox = subject_preflight.bbox_norm if subject_preflight else None
    if subject_bbox is None and vision_features and vision_features.people:
        px, py, width, height = vision_features.people[0].bbox
        subject_bbox = (px, py, px + width, py + height)

    preservation_ratio: float | None = None
    if subject_bbox is not None:
        preservation_ratio = _intersection_ratio(bbox_norm, subject_bbox)
        minimum_preservation = 0.92 if composition_mode == "full_body" else 0.75
        if preservation_ratio < minimum_preservation:
            reasons.append(
                "full_body_not_preserved"
                if composition_mode == "full_body"
                else "subject_not_preserved"
            )
        # A detected face/subject top touching the crop is a head-cut risk.
        subject_top = subject_bbox[1]
        subject_height = subject_bbox[3] - subject_bbox[1]
        if x1 < subject_bbox[2] and x2 > subject_bbox[0]:
            if y1 > subject_top + max(0.01, subject_height * 0.08):
                reasons.append("head_cut_risk")

    return BBoxSafetyResult(
        passed=not reasons,
        displayable=not reasons,
        rejection_reasons=reasons,
        subject_preservation_ratio=(
            round(preservation_ratio, 4) if preservation_ratio is not None else None
        ),
        target_ratio_error=round(ratio_error, 4),
    )
