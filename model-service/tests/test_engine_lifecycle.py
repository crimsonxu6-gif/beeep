import pytest

from config import ModelSettings
from engine import ModelServiceError, ShutterMuseEngine


class FakeEngine(ShutterMuseEngine):
    def _validate_configuration(self) -> None:
        pass

    def _load_once(self) -> None:
        if self.model is None:
            self.model = object()
            self.processor = object()
            self.load_count += 1

    def _warmup(self) -> None:
        self.warmup_completed = True


def test_initialize_twice_loads_model_and_processor_once() -> None:
    engine = FakeEngine(ModelSettings(repo_path="repo", model_path="model", autoload=False))
    engine.initialize()
    engine.initialize()
    assert engine.state == "ready"
    assert engine.load_count == 1
    assert engine.model is not None
    assert engine.processor is not None
    assert engine.warmup_completed is True


def test_missing_repository_is_reported_in_readiness() -> None:
    engine = ShutterMuseEngine(
        ModelSettings(repo_path="", model_path="ShutterMuse/ShutterMuse", autoload=False)
    )
    with pytest.raises(ModelServiceError, match="SHUTTERMUSE_REPO_PATH"):
        engine.initialize()
    state = engine.readiness(False, 0)
    assert state["status"] == "error"
    assert state["error_code"] == "REPOSITORY_NOT_CONFIGURED"


def test_cuda_oom_is_classified() -> None:
    assert (
        ShutterMuseEngine._classify_exception(RuntimeError("CUDA out of memory"), "FAILED")
        == "CUDA_OUT_OF_MEMORY"
    )


def test_invalid_attention_configuration_is_rejected() -> None:
    engine = ShutterMuseEngine(
        ModelSettings(
            repo_path="repo",
            model_path="model",
            attention_implementation="invalid",
            autoload=False,
        )
    )
    with pytest.raises(ModelServiceError) as error:
        engine._validate_configuration()
    assert error.value.code == "INVALID_CONFIGURATION"
