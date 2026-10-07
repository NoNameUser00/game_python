"""Тесты движка проверки кода (песочницы)."""
from app.runner.local import LocalRunner

runner = LocalRunner()

TESTS = [{"input": [5], "expected": 15}]


def test_correct_code_accepted():
    outcome = runner.run("def total(n):\n    return sum(range(1, n + 1))", "total", TESTS)
    assert outcome.status == "accepted"
    assert outcome.tests[0].passed


def test_wrong_answer_failed():
    outcome = runner.run("def total(n):\n    return n", "total", TESTS)
    assert outcome.status == "failed"
    assert not outcome.tests[0].passed
    assert "Ожидалось 15" in outcome.tests[0].message


def test_syntax_error_is_error_status():
    outcome = runner.run("def total(n)\n    return 1", "total", TESTS)
    assert outcome.status == "error"
    assert outcome.tests == []
    assert "синтаксиса" in outcome.message.lower()


def test_infinite_loop_times_out(monkeypatch):
    import app.runner.local as local
    monkeypatch.setattr(local, "RUNNER_TIMEOUT_SECONDS", 0.5)
    outcome = runner.run("def total(n):\n    while True:\n        pass", "total", TESTS)
    assert outcome.status == "failed"
    assert "время выполнения" in outcome.tests[0].message


def test_exception_in_code_reported():
    code = "def total(n):\n    return 1 / 0"
    outcome = runner.run(code, "total", TESTS)
    assert outcome.status == "failed"
    assert "ZeroDivisionError" in outcome.tests[0].message


def test_return_type_mismatch():
    # строка "15" не равна числу 15 — типы важны
    outcome = runner.run('def total(n):\n    return "15"', "total", TESTS)
    assert outcome.status == "failed"


def test_input_calls_blocked():
    code = "def total(n):\n    return input()"
    outcome = runner.run(code, "total", TESTS)
    assert outcome.status == "failed"


def test_sys_exit_reported():
    code = "import sys\ndef total(n):\n    sys.exit(0)"
    outcome = runner.run(code, "total", TESTS)
    assert outcome.status == "failed"


def test_list_task():
    tests = [{"input": [[1, 5, 3]], "expected": 5}]
    outcome = runner.run("def find_max(items):\n    return max(items)", "find_max", tests)
    assert outcome.status == "accepted"
