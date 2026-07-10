from fastapi import APIRouter

from model.guidance_engine import GuidanceEngineService
from parser.output_parser import parse_guidance_output
from schemas import GuidanceOutput, GuidanceRequest, VisionFeatureRequest, VisionFeatures
from vision.mediapipe_processor import MediaPipeVisionProcessor

router = APIRouter()
vision_processor = MediaPipeVisionProcessor()
guidance_engine = GuidanceEngineService()


@router.post("/vision/features", response_model=VisionFeatures, response_model_exclude_none=True)
def vision_features(request: VisionFeatureRequest) -> VisionFeatures:
    return vision_processor.extract_features(request)


@router.post("/guidance", response_model=GuidanceOutput, response_model_exclude_none=True)
def guidance(request: GuidanceRequest) -> GuidanceOutput:
    features = request.vision_features
    if features is None:
        features = vision_processor.extract_features(
            VisionFeatureRequest(
                frame_id=request.frame_id,
                timestamp=request.timestamp,
                image=request.image,
            )
        )

    return parse_guidance_output(guidance_engine.infer(request, features))


@router.get("/guidance/status")
def guidance_status() -> dict[str, object]:
    return guidance_engine.status()
