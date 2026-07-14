from __future__ import annotations

import sys
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from PIL import Image

from config import ModelSettings
from engine import ShutterMuseEngine, is_structured_output_complete


class FakeTokenRow(list):
    def __getitem__(self, index):
        value = super().__getitem__(index)
        return FakeTokenRow(value) if isinstance(index, slice) else value

    @property
    def shape(self):
        return (len(self),)


class FakeInputIds:
    def __init__(self, rows: list[FakeTokenRow]) -> None:
        self.rows = rows
        self.shape = (len(rows), len(rows[0]))

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, index):
        return self.rows[index]


class FakeInputs(dict):
    def __init__(self) -> None:
        input_ids = FakeInputIds([FakeTokenRow([10, 11])])
        super().__init__({"input_ids": input_ids})
        self.input_ids = input_ids

    def to(self, _device: str):
        return self


class FakeProcessor:
    def apply_chat_template(self, *_args, **_kwargs) -> str:
        return "prompt"

    def __call__(self, **_kwargs) -> FakeInputs:
        return FakeInputs()

    def decode(self, _tokens, **_kwargs) -> str:
        return "(100,100),(900,900)"

    def batch_decode(self, _tokens, **_kwargs) -> list[str]:
        return ["(100,100),(900,900)"]


class FakeModel:
    def __init__(self) -> None:
        self.kwargs = None

    def generate(self, **kwargs):
        self.kwargs = kwargs
        generated = [FakeTokenRow([10, 11, 20, 21, 22])]
        assert kwargs["stopping_criteria"][0](generated, None) is True
        return generated


def test_generation_is_explicitly_greedy_and_counts_tokens(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "qwen_vl_utils",
        SimpleNamespace(process_vision_info=lambda _messages: ([object()], [])),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(inference_mode=lambda: nullcontext()),
    )
    engine = ShutterMuseEngine(
        ModelSettings(
            repo_path="repo",
            model_path="model",
            device="cpu",
            max_new_tokens=48,
            autoload=False,
        )
    )
    engine.processor = FakeProcessor()
    engine.model = FakeModel()
    result = engine._generate(Image.new("RGB", (32, 32)), "prompt", "official")
    assert engine.model.kwargs["do_sample"] is False
    assert engine.model.kwargs["num_beams"] == 1
    assert engine.model.kwargs["max_new_tokens"] == 48
    assert result.generated_token_count == 3
    assert result.reached_max_new_tokens is False
    assert result.stopped_by_structure is True


@pytest.mark.parametrize(
    ("text", "mode", "expected"),
    [
        ("(100,100)", "official", False),
        ("(100,100),(900,900)", "official", True),
        ('{"bbox":[100,100,900,900]}', "official", True),
        ('{"bbox":[100,100,900,900]', "official", False),
        ('{"decision":"keep"', "beeep_json", False),
        ('{"decision":"keep"}', "beeep_json", True),
        ("说明（人物）还没有坐标", "official", False),
    ],
)
def test_structured_stop_conditions(text: str, mode: str, expected: bool) -> None:
    assert is_structured_output_complete(text, mode) is expected


def test_attention_kwargs_only_pass_non_default_values() -> None:
    default = ShutterMuseEngine(ModelSettings(attention_implementation="default", autoload=False))
    sdpa = ShutterMuseEngine(ModelSettings(attention_implementation="sdpa", autoload=False))
    assert default._attention_model_kwargs() == {}
    assert sdpa._attention_model_kwargs() == {"attn_implementation": "sdpa"}


def test_warmup_uses_same_prompt_mode_and_generation_settings(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "warmup.jpg"
    Image.new("RGB", (16, 16)).save(image_path)
    settings = ModelSettings(
        prompt_mode="official",
        warmup_image=str(image_path),
        max_new_tokens=48,
        attention_implementation="sdpa",
        autoload=False,
    )
    engine = ShutterMuseEngine(settings)
    calls: list[tuple[str, str]] = []

    def fake_generate(_image, prompt: str, prompt_mode: str):
        calls.append((prompt, prompt_mode))
        return SimpleNamespace(
            raw_output="(0,0),(1000,1000)",
            reached_max_new_tokens=False,
        )

    monkeypatch.setattr(engine, "_generate", fake_generate)
    engine._warmup()
    assert calls and calls[0][1] == "official"
    assert engine.generation_config() == {
        "do_sample": False,
        "num_beams": 1,
        "max_new_tokens": 48,
        "attention_implementation": "sdpa",
    }
