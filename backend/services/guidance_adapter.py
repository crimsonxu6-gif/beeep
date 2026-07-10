from __future__ import annotations

from schemas import (
    AnalyzeRequest,
    CompositionRecommendation,
    GuidanceOutput,
    PoseRecommendation,
    TargetPoseKeypoint,
    VisionFeatures,
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class GuidanceAdapter:
    """Normalizes all app-facing geometry to 0..1 coordinates."""

    def adapt(
        self,
        output: GuidanceOutput,
        request: AnalyzeRequest,
        features: VisionFeatures,
    ) -> GuidanceOutput:
        if output.composition is not None:
            return output

        subject = features.people[0] if features.people else None
        if subject is None:
            box = (0.05, 0.05, 0.95, 0.95)
            decision = "reject"
        else:
            x, y, width, height = subject.bbox
            targets = {"thirds_left": 0.33, "thirds_right": 0.67, "center": 0.50}
            target_x = targets.get(request.composition_mode, x + width / 2)
            x1 = _clamp(target_x - width / 2 - 0.06)
            y1 = _clamp(y - 0.06)
            x2 = _clamp(target_x + width / 2 + 0.06)
            y2 = _clamp(y + height + 0.06)
            box = (x1, y1, max(x1, x2), max(y1, y2))
            decision = "keep" if output.actions and output.actions[0].type == "hold" else "refine"

        return output.model_copy(
            update={"composition": CompositionRecommendation(decision=decision, bbox_norm=box)}
        )

    def parse_pose(self, keypoints: list[dict[str, object]], visibility: list[object]) -> PoseRecommendation:
        if len(keypoints) != 17 or len(visibility) != 17:
            raise ValueError("invalid_model_output: expected exactly 17 keypoints and visibility values")
        parsed: list[TargetPoseKeypoint] = []
        for point, visible in zip(keypoints, visibility, strict=True):
            try:
                parsed.append(
                    TargetPoseKeypoint(
                        name=str(point["name"]),
                        x=float(point["x"]),
                        y=float(point["y"]),
                        visibility=float(visible),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid_model_output: malformed pose keypoint") from exc
        return PoseRecommendation(keypoints=parsed, keypoint_count=17)
