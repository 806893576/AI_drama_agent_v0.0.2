from evaluation.benchmarks import run_default_benchmark


def test_default_benchmark_runs() -> None:
    results = run_default_benchmark()

    assert results
    assert results[0]["passed"] is True
