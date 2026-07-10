from __future__ import annotations

from schemas import (
    AdjustAngleAction,
    AdjustDistanceAction,
    AnalyzeRequest,
    CompositionRecommendation,
    FramingHintAction,
    GuidanceOutput,
    GuidanceProblem,
    HoldAction,
    MoveCameraAction,
    PoseRecommendation,
    TargetPoseKeypoint,
    VisionFeatures,
)
from services.shuttermuse_client import ModelCompositionResult


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

    def from_model_composition(
        self,
        result: ModelCompositionResult,
        frame_id: int,
    ) -> GuidanceOutput:
        confidence = result.confidence if result.confidence is not None else 0.65
        if result.status != "success":
            return GuidanceOutput(
                frameId=frame_id,
                priority="composition",
                problem=GuidanceProblem(type="invalid_model_output", description="构图结果不稳定"),
                actions=[FramingHintAction(type="framing_hint", message="重新取景", confidence=0.4)],
                message="重新取景",
                reason="ShutterMuse 未返回合法构图框",
                summary="构图结果不稳定",
                confidence=0.4,
            )
        if result.decision == "reject":
            return GuidanceOutput(
                frameId=frame_id,
                priority="composition",
                problem=GuidanceProblem(type="framing_rejected", description="当前取景不理想"),
                actions=[FramingHintAction(type="framing_hint", message="重新取景", confidence=confidence)],
                message="重新取景",
                reason="ShutterMuse 建议放弃当前取景",
                summary="当前取景不理想",
                confidence=confidence,
            )
        bbox = result.bbox_norm
        if bbox is None:
            return self.from_model_composition(
                result.model_copy(update={"status": "low_confidence"}),
                frame_id,
            )
        composition = CompositionRecommendation(decision=result.decision or "refine", bbox_norm=bbox)
        if result.decision == "keep":
            return GuidanceOutput(
                frameId=frame_id,
                priority="hold",
                problem=GuidanceProblem(type="none", description="画面稳定"),
                actions=[HoldAction(type="hold", message="保持角度", confidence=confidence)],
                message="保持角度",
                reason="ShutterMuse 建议保留当前构图",
                summary="画面稳定",
                confidence=confidence,
                composition=composition,
            )

        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        area = (x2 - x1) * (y2 - y1)
        if center_x < 0.43:
            action = MoveCameraAction(
                type="move_camera", direction="left", message="往左一点", confidence=confidence
            )
            problem = GuidanceProblem(type="crop_left", description="推荐区域偏左")
            priority = "composition"
        elif center_x > 0.57:
            action = MoveCameraAction(
                type="move_camera", direction="right", message="往右一点", confidence=confidence
            )
            problem = GuidanceProblem(type="crop_right", description="推荐区域偏右")
            priority = "composition"
        elif center_y < 0.38:
            action = AdjustAngleAction(
                type="adjust_angle", direction="raise", message="手机高一点", confidence=confidence
            )
            problem = GuidanceProblem(type="crop_top", description="推荐区域偏上")
            priority = "angle"
        elif center_y > 0.62:
            action = AdjustAngleAction(
                type="adjust_angle", direction="lower", message="手机低一点", confidence=confidence
            )
            problem = GuidanceProblem(type="crop_bottom", description="推荐区域偏下")
            priority = "angle"
        elif area < 0.62:
            action = AdjustDistanceAction(
                type="adjust_distance", direction="closer", message="靠近一点", confidence=confidence
            )
            problem = GuidanceProblem(type="crop_tighter", description="推荐区域更紧凑")
            priority = "distance"
        else:
            action = FramingHintAction(type="framing_hint", message="微调构图", confidence=confidence)
            problem = GuidanceProblem(type="crop_refine", description="构图可以微调")
            priority = "composition"
        return GuidanceOutput(
            frameId=frame_id,
            priority=priority,
            problem=problem,
            actions=[action],
            message=action.message,
            reason="根据 ShutterMuse 推荐构图框生成动作",
            summary=problem.description,
            confidence=confidence,
            composition=composition,
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
