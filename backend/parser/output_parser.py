from __future__ import annotations

from schemas import GuidanceOutput


def _dump_model(value: GuidanceOutput) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def parse_guidance_output(value: GuidanceOutput | dict) -> GuidanceOutput:
    raw = _dump_model(value) if isinstance(value, GuidanceOutput) else value
    output = GuidanceOutput(**raw)
    output.actions = output.actions[:3]
    output.summary = output.summary[:80]
    output.confidence = max(0, min(1, output.confidence))
    return output
