from __future__ import annotations

from schemas import (
    AdjustAngleAction,
    AdjustDistanceAction,
    AdjustPoseAction,
    CompositionMode,
    FramingHintAction,
    GuidanceAction,
    GuidanceOutput,
    GuidanceProblem,
    HoldAction,
    LightingHintAction,
    MoveCameraAction,
    PoseKeypoint,
    VisionFeatures,
)


def _keypoint(features: VisionFeatures, name: str) -> PoseKeypoint | None:
    if not features.people:
        return None

    for keypoint in features.people[0].keypoints:
        if keypoint.name == name:
            return keypoint
    return None


def _problem(problem_type: str, description: str) -> GuidanceProblem:
    return GuidanceProblem(type=problem_type, description=description)


def _move(direction: str, message: str, confidence: float) -> MoveCameraAction:
    return MoveCameraAction(
        type="move_camera",
        direction=direction,
        message=message,
        confidence=confidence,
    )


class ShutterMuseGuidanceEngine:
    def infer(self, features: VisionFeatures, composition_mode: CompositionMode = "auto") -> GuidanceOutput:
        actions: list[GuidanceAction] = []
        priority = "composition"
        problem = _problem("none", "画面稳定")
        reason = "没有明显构图或光线问题"
        summary = "画面稳定"

        subject = features.people[0] if features.people else None
        if subject is None:
            return GuidanceOutput(
                frameId=features.frameId,
                priority="subject",
                problem=_problem("subject_missing", "未检测到主体"),
                actions=[
                    FramingHintAction(
                        type="framing_hint",
                        message="寻找主体",
                        confidence=0.58,
                    )
                ],
                message="寻找主体",
                reason="画面中没有稳定的人物或主体框",
                summary="未检测到主体",
                confidence=0.58,
            )

        if features.scene.brightness == "backlight":
            return GuidanceOutput(
                frameId=features.frameId,
                priority="lighting",
                problem=_problem("backlight", "人物逆光"),
                actions=[
                    LightingHintAction(
                        type="lighting_hint",
                        message="转向光源",
                        confidence=0.86,
                    )
                ],
                message="转向光源",
                reason="背景亮度明显高于主体区域",
                summary="人物逆光",
                confidence=0.86,
            )

        if features.scene.brightness == "low_light":
            return GuidanceOutput(
                frameId=features.frameId,
                priority="lighting",
                problem=_problem("low_light", "画面偏暗"),
                actions=[
                    LightingHintAction(
                        type="lighting_hint",
                        message="提高曝光",
                        confidence=0.78,
                    )
                ],
                message="提高曝光",
                reason="画面平均亮度偏低",
                summary="画面偏暗",
                confidence=0.78,
            )

        x, y, width, height = subject.bbox
        center_x = x + width / 2
        center_y = y + height / 2
        targets = {
            "center": 0.50,
            "thirds_left": 0.33,
            "thirds_right": 0.67,
            "portrait_closeup": 0.50,
            "full_body": 0.50,
        }
        if composition_mode == "auto":
            target_x = min((0.33, 0.50, 0.67), key=lambda target: abs(center_x - target))
        else:
            target_x = targets.get(composition_mode, 0.50)

        if center_x < target_x - 0.08:
            actions.append(_move("left", "往左一点", 0.82))
            problem = _problem("subject_position", "主体偏左")
            reason = "主体中心位于画面左侧"
            summary = "主体偏左"
        elif center_x > target_x + 0.08:
            actions.append(_move("right", "往右一点", 0.82))
            problem = _problem("subject_position", "主体偏右")
            reason = "主体中心位于画面右侧"
            summary = "主体偏右"

        if not actions and center_y < 0.34:
            actions.append(
                AdjustAngleAction(
                    type="adjust_angle", direction="raise", message="手机高一点", confidence=0.74
                )
            )
            priority = "angle"
            problem = _problem("camera_angle", "下方空间多")
            reason = "主体位置偏上，下方留白过多"
            summary = "下方空间多"
        elif not actions and center_y > 0.7:
            actions.append(
                AdjustAngleAction(
                    type="adjust_angle", direction="lower", message="手机低一点", confidence=0.74
                )
            )
            priority = "angle"
            problem = _problem("camera_angle", "主体偏低")
            reason = "主体位置偏下，需要降低手机取景"
            summary = "主体偏低"

        if len(actions) < 2 and features.face.size == "small":
            actions.append(
                AdjustDistanceAction(
                    type="adjust_distance", direction="closer", message="靠近一点", confidence=0.76
                )
            )
            priority = "distance" if not actions[:-1] else priority
            problem = _problem("subject_too_small", "人物太小")
            reason = "人脸或主体占画面比例偏小"
            summary = "人物太小"
        elif len(actions) < 2 and features.face.size == "large":
            actions.append(
                AdjustDistanceAction(
                    type="adjust_distance", direction="farther", message="后退一点", confidence=0.72
                )
            )
            priority = "distance" if not actions[:-1] else priority
            problem = _problem("subject_too_large", "距离太近")
            reason = "人脸或主体占画面比例偏大"
            summary = "距离太近"

        if actions:
            return GuidanceOutput(
                frameId=features.frameId,
                priority=priority,
                problem=problem,
                actions=actions[:2],
                message=actions[0].message,
                reason=reason,
                summary=summary,
                confidence=max(action.confidence or 0.7 for action in actions[:2]),
            )

        left_shoulder = _keypoint(features, "left_shoulder")
        right_shoulder = _keypoint(features, "right_shoulder")
        nose = _keypoint(features, "nose")
        if left_shoulder and right_shoulder:
            shoulder_delta = abs(left_shoulder.y - right_shoulder.y)
            if shoulder_delta > 0.035:
                return GuidanceOutput(
                    frameId=features.frameId,
                    priority="pose",
                    problem=_problem("shoulder_tilt", "肩膀不平"),
                    actions=[
                        AdjustPoseAction(
                            type="adjust_pose",
                            message="肩膀放松",
                            confidence=0.72,
                        )
                    ],
                    message="肩膀放松",
                    reason="左右肩膀高度差明显",
                    summary="肩膀不平",
                    confidence=0.72,
                )

            if nose:
                shoulder_center = (left_shoulder.x + right_shoulder.x) / 2
                head_offset = nose.x - shoulder_center
                if head_offset > 0.06:
                    return GuidanceOutput(
                        frameId=features.frameId,
                        priority="pose",
                        problem=_problem("head_direction", "头部偏右"),
                        actions=[
                            AdjustPoseAction(
                                type="adjust_pose",
                                message="头左一点",
                                confidence=0.7,
                            )
                        ],
                        message="头左一点",
                        reason="鼻尖相对肩膀中心偏右",
                        summary="头部偏右",
                        confidence=0.7,
                    )
                if head_offset < -0.06:
                    return GuidanceOutput(
                        frameId=features.frameId,
                        priority="pose",
                        problem=_problem("head_direction", "头部偏左"),
                        actions=[
                            AdjustPoseAction(
                                type="adjust_pose",
                                message="头右一点",
                                confidence=0.7,
                            )
                        ],
                        message="头右一点",
                        reason="鼻尖相对肩膀中心偏左",
                        summary="头部偏左",
                        confidence=0.7,
                    )

        if features.scene.clutter == "high":
            return GuidanceOutput(
                frameId=features.frameId,
                priority="composition",
                problem=_problem("background_clutter", "背景干扰"),
                actions=[
                    FramingHintAction(
                        type="framing_hint",
                        message="背景简洁",
                        confidence=0.68,
                    )
                ],
                message="背景简洁",
                reason="边缘密度高，背景元素较杂",
                summary="背景干扰",
                confidence=0.68,
            )

        return GuidanceOutput(
            frameId=features.frameId,
            priority="hold",
            problem=problem,
            actions=[
                HoldAction(
                    type="hold",
                    message="保持角度",
                    confidence=0.84,
                )
            ],
            message="保持角度",
            reason=reason,
            summary=summary,
            confidence=0.84,
        )
