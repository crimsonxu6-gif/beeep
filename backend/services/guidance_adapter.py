from __future__ import annotations

from dataclasses import dataclass

from schemas import (
    AdjustAngleAction,
    AdjustDistanceAction,
    AnalyzeRequest,
    CompositionRecommendation,
    FramingHintAction,
    GuidanceAction,
    GuidanceOutput,
    GuidanceProblem,
    HoldAction,
    MoveCameraAction,
    PoseRecommendation,
    SubjectPreflightResult,
    TargetPoseKeypoint,
    VisionFeatures,
)
from services.shuttermuse_client import ModelCompositionResult


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _action_confidence(model_confidence: float, score: float) -> float:
    return round(_clamp(model_confidence * (0.7 + 0.3 * score)), 3)


@dataclass(frozen=True)
class ActionCandidate:
    action: GuidanceAction
    score: float
    dimension: str
    problem: GuidanceProblem
    priority: str


class GuidanceAdapter:
    """Converts model geometry into stable, deterministic product actions."""

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

    def subject_missing(self, frame_id: int) -> GuidanceOutput:
        return self.from_subject_preflight(
            SubjectPreflightResult(
                state="missing",
                detected=False,
                allow_shuttermuse=False,
                confidence=0,
                face_detected=False,
                reason="暂时没有找到人物",
                reason_code="no_face",
            ),
            frame_id,
        )

    def from_subject_preflight(
        self,
        preflight: SubjectPreflightResult,
        frame_id: int,
    ) -> GuidanceOutput:
        messages = {
            "no_face": "把人物放进画面再试试",
            "face_low_confidence": "保持一下，让人物更清楚",
            "subject_too_small": "让人物再靠近一些",
            "recent_subject": "正在确认人物位置",
            "confirming_subject": "正在确认人物位置",
            "face_confirmed": "正在确认人物位置",
        }
        descriptions = {
            "no_face": "暂时没有找到人物",
            "face_low_confidence": "人物还不够清晰",
            "subject_too_small": "人物在画面中太小",
            "recent_subject": "人物检测暂时波动",
            "confirming_subject": "正在确认人物位置",
            "face_confirmed": "正在确认人物位置",
        }
        message = messages[preflight.reason_code]
        description = descriptions[preflight.reason_code]
        action = FramingHintAction(type="framing_hint", message=message, confidence=0.7)
        return GuidanceOutput(
            frameId=frame_id,
            priority="subject",
            problem=GuidanceProblem(type=f"subject_{preflight.state}", description=description),
            actions=[action],
            message=action.message,
            reason=f"MediaPipe preflight: {preflight.reason_code}",
            summary=description,
            confidence=0.7,
        )

    def from_model_composition(
        self,
        result: ModelCompositionResult,
        frame_id: int,
    ) -> GuidanceOutput:
        confidence = result.confidence if result.confidence is not None else 0.65
        if result.status != "success":
            action = FramingHintAction(
                type="framing_hint",
                message="稍微换个角度再试",
                confidence=0.4,
            )
            return GuidanceOutput(
                frameId=frame_id,
                priority="composition",
                problem=GuidanceProblem(type="invalid_model_output", description="这次没看懂画面"),
                actions=[action],
                message=action.message,
                reason="ShutterMuse 未返回合法构图框",
                summary="这次没看懂画面",
                confidence=0.4,
            )
        if result.decision == "reject":
            action = FramingHintAction(
                type="framing_hint",
                message="换个角度再试试",
                confidence=confidence,
            )
            return GuidanceOutput(
                frameId=frame_id,
                priority="composition",
                problem=GuidanceProblem(type="framing_rejected", description="当前取景不理想"),
                actions=[action],
                message=action.message,
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
            action = HoldAction(
                type="hold",
                message="这个构图不错，可以拍了",
                confidence=confidence,
            )
            return GuidanceOutput(
                frameId=frame_id,
                priority="hold",
                problem=GuidanceProblem(type="none", description="当前构图自然稳定"),
                actions=[action],
                message=action.message,
                reason="ShutterMuse 建议保留当前构图",
                summary="当前构图自然稳定",
                confidence=confidence,
                composition=composition,
            )

        candidates = self._composition_candidates(bbox, confidence)
        selected = self._select_candidates(candidates)
        if not selected:
            action = FramingHintAction(
                type="framing_hint",
                message="构图稍微调整一下",
                confidence=confidence,
            )
            selected = [
                ActionCandidate(
                    action=action,
                    score=0.25,
                    dimension="framing",
                    problem=GuidanceProblem(type="crop_refine", description="构图可以稍微调整"),
                    priority="composition",
                )
            ]

        primary = selected[0]
        actions = [candidate.action for candidate in selected]
        return GuidanceOutput(
            frameId=frame_id,
            priority=primary.priority,
            problem=primary.problem,
            actions=actions,
            message=actions[0].message,
            reason="根据 ShutterMuse 推荐构图框生成动作",
            summary=primary.problem.description,
            confidence=confidence,
            composition=composition,
        )

    def _composition_candidates(
        self,
        bbox: tuple[float, float, float, float],
        confidence: float,
    ) -> list[ActionCandidate]:
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        area = (x2 - x1) * (y2 - y1)
        candidates: list[ActionCandidate] = []

        if center_x < 0.43:
            score = _clamp(0.25 + ((0.43 - center_x) / 0.43) * 0.75)
            candidates.append(
                ActionCandidate(
                    action=MoveCameraAction(
                        type="move_camera",
                        direction="left",
                        message="镜头稍微往左移",
                        confidence=_action_confidence(confidence, score),
                    ),
                    score=score,
                    dimension="horizontal",
                    problem=GuidanceProblem(type="crop_left", description="推荐构图区域偏左"),
                    priority="composition",
                )
            )
        elif center_x > 0.57:
            score = _clamp(0.25 + ((center_x - 0.57) / 0.43) * 0.75)
            candidates.append(
                ActionCandidate(
                    action=MoveCameraAction(
                        type="move_camera",
                        direction="right",
                        message="镜头稍微往右移",
                        confidence=_action_confidence(confidence, score),
                    ),
                    score=score,
                    dimension="horizontal",
                    problem=GuidanceProblem(type="crop_right", description="推荐构图区域偏右"),
                    priority="composition",
                )
            )

        if center_y < 0.38:
            score = _clamp(0.25 + ((0.38 - center_y) / 0.38) * 0.7)
            candidates.append(
                ActionCandidate(
                    action=AdjustAngleAction(
                        type="adjust_angle",
                        direction="raise",
                        message="取景稍微往上移",
                        confidence=_action_confidence(confidence, score),
                    ),
                    score=score,
                    dimension="vertical",
                    problem=GuidanceProblem(type="crop_top", description="推荐构图区域偏上"),
                    priority="angle",
                )
            )
        elif center_y > 0.62:
            score = _clamp(0.25 + ((center_y - 0.62) / 0.38) * 0.7)
            candidates.append(
                ActionCandidate(
                    action=AdjustAngleAction(
                        type="adjust_angle",
                        direction="lower",
                        message="取景稍微往下移",
                        confidence=_action_confidence(confidence, score),
                    ),
                    score=score,
                    dimension="vertical",
                    problem=GuidanceProblem(type="crop_bottom", description="推荐构图区域偏下"),
                    priority="angle",
                )
            )

        if area < 0.62:
            score = _clamp(0.25 + ((0.62 - area) / 0.62) * 0.55)
            candidates.append(
                ActionCandidate(
                    action=AdjustDistanceAction(
                        type="adjust_distance",
                        direction="closer",
                        message="让人物再大一些",
                        confidence=_action_confidence(confidence, score),
                    ),
                    score=score,
                    dimension="distance",
                    problem=GuidanceProblem(type="crop_tighter", description="推荐构图区域更紧凑"),
                    priority="distance",
                )
            )
        return candidates

    @staticmethod
    def _select_candidates(candidates: list[ActionCandidate]) -> list[ActionCandidate]:
        ranked = sorted(candidates, key=lambda candidate: candidate.score, reverse=True)
        if not ranked or ranked[0].score < 0.25:
            return []
        selected = [ranked[0]]
        for candidate in ranked[1:]:
            if candidate.score < 0.40:
                continue
            if candidate.dimension == selected[0].dimension:
                continue
            selected.append(candidate)
            break
        return selected

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
