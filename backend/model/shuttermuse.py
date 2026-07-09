from __future__ import annotations

from schemas import (
    AdjustPoseAction,
    FramingHintAction,
    GuidanceAction,
    GuidanceOutput,
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


def _move(direction: str, message: str, confidence: float) -> MoveCameraAction:
    return MoveCameraAction(
        type="move_camera",
        direction=direction,
        message=message,
        confidence=confidence,
    )


class ShutterMuseGuidanceEngine:
    def infer(self, features: VisionFeatures) -> GuidanceOutput:
        actions: list[GuidanceAction] = []
        priority = "composition"
        summary = "画面稳定"
        confidence = 0.78

        subject = features.people[0] if features.people else None
        if subject is None:
            return GuidanceOutput(
                frameId=features.frameId,
                priority="subject",
                actions=[
                    FramingHintAction(
                        type="framing_hint",
                        message="寻找主体",
                        confidence=0.58,
                    )
                ],
                summary="未检测到主体",
                confidence=0.58,
            )

        if features.scene.brightness == "backlight":
            return GuidanceOutput(
                frameId=features.frameId,
                priority="lighting",
                actions=[
                    LightingHintAction(
                        type="lighting_hint",
                        message="转向光源",
                        confidence=0.86,
                    )
                ],
                summary="人物逆光",
                confidence=0.86,
            )

        if features.scene.brightness == "low_light":
            return GuidanceOutput(
                frameId=features.frameId,
                priority="lighting",
                actions=[
                    LightingHintAction(
                        type="lighting_hint",
                        message="提高曝光",
                        confidence=0.78,
                    )
                ],
                summary="画面偏暗",
                confidence=0.78,
            )

        x, y, width, height = subject.bbox
        center_x = (x + width / 2) / max(features.imageSize.width, 1)
        center_y = (y + height / 2) / max(features.imageSize.height, 1)

        if center_x < 0.43:
            actions.append(_move("left", "往左一点", 0.82))
            summary = "主体偏左"
        elif center_x > 0.57:
            actions.append(_move("right", "往右一点", 0.82))
            summary = "主体偏右"

        if not actions and center_y < 0.34:
            actions.append(_move("up", "抬高一点", 0.74))
            summary = "下方空间多"
        elif not actions and center_y > 0.7:
            actions.append(_move("down", "压低一点", 0.74))
            summary = "主体偏低"

        if len(actions) < 2 and features.face.size == "small":
            actions.append(_move("forward", "靠近一点", 0.76))
            summary = "人物太小"
        elif len(actions) < 2 and features.face.size == "large":
            actions.append(_move("back", "后退一点", 0.72))
            summary = "距离太近"

        if actions:
            return GuidanceOutput(
                frameId=features.frameId,
                priority=priority,
                actions=actions[:2],
                summary=summary,
                confidence=max(action.confidence or 0.7 for action in actions[:2]),
            )

        left_shoulder = _keypoint(features, "left_shoulder")
        right_shoulder = _keypoint(features, "right_shoulder")
        nose = _keypoint(features, "nose")
        if left_shoulder and right_shoulder:
            shoulder_delta = abs(left_shoulder.y - right_shoulder.y)
            if shoulder_delta > features.imageSize.height * 0.035:
                return GuidanceOutput(
                    frameId=features.frameId,
                    priority="pose",
                    actions=[
                        AdjustPoseAction(
                            type="adjust_pose",
                            message="肩膀放松",
                            confidence=0.72,
                        )
                    ],
                    summary="肩膀不平",
                    confidence=0.72,
                )

            if nose:
                shoulder_center = (left_shoulder.x + right_shoulder.x) / 2
                head_offset = (nose.x - shoulder_center) / max(features.imageSize.width, 1)
                if head_offset > 0.06:
                    return GuidanceOutput(
                        frameId=features.frameId,
                        priority="pose",
                        actions=[
                            AdjustPoseAction(
                                type="adjust_pose",
                                message="头左一点",
                                confidence=0.7,
                            )
                        ],
                        summary="头部偏右",
                        confidence=0.7,
                    )
                if head_offset < -0.06:
                    return GuidanceOutput(
                        frameId=features.frameId,
                        priority="pose",
                        actions=[
                            AdjustPoseAction(
                                type="adjust_pose",
                                message="头右一点",
                                confidence=0.7,
                            )
                        ],
                        summary="头部偏左",
                        confidence=0.7,
                    )

        if features.scene.clutter == "high":
            return GuidanceOutput(
                frameId=features.frameId,
                priority="composition",
                actions=[
                    FramingHintAction(
                        type="framing_hint",
                        message="背景简洁",
                        confidence=0.68,
                    )
                ],
                summary="背景干扰",
                confidence=0.68,
            )

        return GuidanceOutput(
            frameId=features.frameId,
            priority="hold",
            actions=[
                HoldAction(
                    type="hold",
                    message="保持角度",
                    confidence=0.84,
                )
            ],
            summary="画面稳定",
            confidence=0.84,
        )
