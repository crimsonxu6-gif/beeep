from __future__ import annotations

from schemas import (
    AdjustPoseAction,
    FramingHintAction,
    GuidanceOutput,
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


class ShutterMuseGuidanceEngine:
    def infer(self, features: VisionFeatures) -> GuidanceOutput:
        actions: list[MoveCameraAction | AdjustPoseAction | FramingHintAction] = []
        summary = "composition is stable"
        confidence = 0.76

        subject = features.people[0] if features.people else None
        if subject is None:
            actions.append(
                FramingHintAction(
                    type="framing_hint",
                    instruction="find subject",
                    direction="hold",
                    strength="medium",
                )
            )
            return GuidanceOutput(
                frameId=features.frameId,
                actions=actions,
                summary="no subject detected",
                confidence=0.58,
            )

        x, y, width, height = subject.bbox
        center_x = (x + width / 2) / max(features.imageSize.width, 1)
        center_y = (y + height / 2) / max(features.imageSize.height, 1)

        if center_x < 0.43:
            actions.append(MoveCameraAction(type="move_camera", direction="left", strength="medium"))
            summary = "subject is left of center"
        elif center_x > 0.57:
            actions.append(MoveCameraAction(type="move_camera", direction="right", strength="medium"))
            summary = "subject is right of center"

        if center_y < 0.34:
            actions.append(MoveCameraAction(type="move_camera", direction="up", strength="low"))
            summary = "subject has too much lower space"
        elif center_y > 0.7:
            actions.append(MoveCameraAction(type="move_camera", direction="down", strength="low"))
            summary = "subject is too low"

        if features.face.size == "small":
            actions.append(MoveCameraAction(type="move_camera", direction="forward", strength="low"))
        elif features.face.size == "large":
            actions.append(MoveCameraAction(type="move_camera", direction="back", strength="low"))

        left_shoulder = _keypoint(features, "left_shoulder")
        right_shoulder = _keypoint(features, "right_shoulder")
        nose = _keypoint(features, "nose")
        if left_shoulder and right_shoulder:
            shoulder_delta = abs(left_shoulder.y - right_shoulder.y)
            if shoulder_delta > features.imageSize.height * 0.035:
                actions.append(
                    AdjustPoseAction(
                        type="adjust_pose",
                        instruction="relax shoulders",
                        strength="low",
                    )
                )

            if nose:
                shoulder_center = (left_shoulder.x + right_shoulder.x) / 2
                head_offset = (nose.x - shoulder_center) / max(features.imageSize.width, 1)
                if head_offset > 0.06:
                    actions.append(
                        AdjustPoseAction(
                            type="adjust_pose",
                            instruction="turn head slightly left",
                            strength="low",
                        )
                    )
                elif head_offset < -0.06:
                    actions.append(
                        AdjustPoseAction(
                            type="adjust_pose",
                            instruction="turn head slightly right",
                            strength="low",
                        )
                    )

        if features.scene.brightness == "backlight":
            actions.append(
                FramingHintAction(
                    type="framing_hint",
                    instruction="avoid backlight",
                    direction="hold",
                    strength="medium",
                )
            )
        elif features.scene.brightness == "low_light":
            actions.append(
                FramingHintAction(
                    type="framing_hint",
                    instruction="raise exposure",
                    direction="hold",
                    strength="low",
                )
            )

        if features.scene.clutter == "high":
            actions.append(
                FramingHintAction(
                    type="framing_hint",
                    instruction="simplify background",
                    direction="hold",
                    strength="low",
                )
            )

        if not actions:
            actions.append(
                FramingHintAction(
                    type="framing_hint",
                    instruction="hold steady",
                    direction="hold",
                    strength="low",
                )
            )
            confidence = 0.82

        return GuidanceOutput(
            frameId=features.frameId,
            actions=actions[:3],
            summary=summary,
            confidence=confidence,
        )
