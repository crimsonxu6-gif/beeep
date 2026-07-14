from concurrent.futures import Future

from fastapi.testclient import TestClient

import app as app_module
from config import ModelSettings
from engine import GenerationResult, InferenceResult
from output_parser import ParsedComposition


def result() -> InferenceResult:
    return InferenceResult(
        parsed=ParsedComposition(
            status="success",
            decision="refine",
            bbox_norm=(0.1, 0.1, 0.9, 0.9),
            confidence=0.8,
            coordinate_source="official_1000_pairs",
        ),
        generation=GenerationResult(
            raw_output="(100,100),(900,900)",
            generated_token_count=14,
            reached_max_new_tokens=False,
            stopped_by_structure=True,
        ),
        inference_ms=900,
        parser_comparison="both_success",
    )


def request_payload() -> dict:
    return {
        "request_id": "req_eval",
        "frame_id": 1,
        "image_base64": "unused",
        "mime_type": "image/jpeg",
        "target_ratio": "3:4",
        "composition_mode": "auto",
        "prompt_mode": "official",
    }


def configure(monkeypatch, *, capture_raw: bool) -> TestClient:
    future: Future = Future()
    future.set_result(result())
    monkeypatch.setattr(app_module.executor, "submit", lambda _fn: future)
    monkeypatch.setattr(app_module.engine, "state", "ready")
    monkeypatch.setattr(
        app_module,
        "settings",
        ModelSettings(
            eval_capture_raw_output=capture_raw,
            max_new_tokens=48,
            attention_implementation="sdpa",
            autoload=False,
        ),
    )
    monkeypatch.setattr(app_module.engine, "settings", app_module.settings)
    return TestClient(app_module.app)


def test_raw_output_is_hidden_by_default(monkeypatch) -> None:
    body = configure(monkeypatch, capture_raw=False).post(
        "/v1/photographer/analyze", json=request_payload()
    ).json()
    assert "raw_output" not in body
    assert "raw_output_length" not in body
    assert body["generated_token_count"] == 14


def test_raw_output_is_returned_only_for_evaluation(monkeypatch) -> None:
    body = configure(monkeypatch, capture_raw=True).post(
        "/v1/photographer/analyze", json=request_payload()
    ).json()
    assert body["raw_output"] == "(100,100),(900,900)"
    assert body["raw_output_length"] == 19
    assert body["generation_config"] == {
        "do_sample": False,
        "num_beams": 1,
        "max_new_tokens": 48,
        "attention_implementation": "sdpa",
    }
