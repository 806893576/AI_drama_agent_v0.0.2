from api.schemas import GenerateRequest
from evaluation.metrics import score_required_artifacts
from memory.memory_manager import MemoryManager
from tools.local.calculator import estimate_runtime, estimate_shot_count
from tools.registry import ToolRegistry


def test_api_generate_request_accepts_user_request() -> None:
    request = GenerateRequest(user_request="都市逆袭短剧，平台抖音，12集，每集2分钟。")

    assert request.user_request.startswith("都市逆袭")


def test_memory_manager_can_remember_project_note(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMA_STORAGE_DIR", str(tmp_path))
    from core.settings import get_settings

    get_settings.cache_clear()
    manager = MemoryManager()
    manager.remember_project_note("tone", "强爽点、快节奏")

    assert manager.long.get("tone") == "强爽点、快节奏"
    assert manager.vector.search("强爽点")
    get_settings.cache_clear()


def test_local_calculator_tools() -> None:
    assert estimate_runtime(12, 2) == 24
    assert estimate_shot_count(3, 2) == 6


def test_tool_registry_registers_decorated_tool() -> None:
    registry = ToolRegistry()
    registry.register_function(estimate_runtime)

    assert registry.get("estimate_runtime").func(10, 1.5) == 15


def test_evaluation_artifact_score() -> None:
    score = score_required_artifacts(
        {"writer_package": "a", "final_package": "b"},
        ["writer_package", "director_package", "final_package"],
    )

    assert score == 0.6667
