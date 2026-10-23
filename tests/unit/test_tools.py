from tools.local.calculator import estimate_runtime


def test_estimate_runtime_tool() -> None:
    assert estimate_runtime(8, 1.5) == 12
