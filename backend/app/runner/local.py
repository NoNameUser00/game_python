"""Локальный раннер: запуск кода ученика в изолированном subprocess.

Ограничения на каждый запуск:
- время (wall-clock)  -> RUNNER_TIMEOUT_SECONDS (по умолчанию 3 c)
- CPU                 -> RUNNER_CPU_SECONDS   (по умолчанию 2 c)
- память              -> RUNNER_MEMORY_MB     (по умолчанию 256 МБ)
- размер файлов       -> 1 МБ, core-дампы отключены
- stdin закрыт (input() невозможен), рабочая папка — временная и удаляется
- сеть                -> отключена: если доступен `unshare -n`, код бежит в
  отдельном сетевом namespace (ядро), иначе — Python-заглушка, ломающая
  `socket`/`create_connection` ещё на импорте модуля

Важно: это защита «от школьника», а не от целенаправленной атаки. На публичном
сервере с недоверенным кодом предпочтителен `RUNNER_MODE=docker` (пока не реализован).
"""
import functools
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

from ..config import RUNNER_CPU_SECONDS, RUNNER_MEMORY_MB, RUNNER_TIMEOUT_SECONDS

RESULT_FILE = "__result__.json"

# Заглушка сети, вклеивается ПЕРЕД кодом ученика (не влияет на номера строк:
# для ошибок времени выполнения школьнику показывается только последняя строка
# traceback, а ошибки синтаксиса ловятся отдельным compile()).
_NET_GUARD = '''\
# ===== песочница: сеть отключена =====
def __block_network():
    import socket as __sk

    def __blocked(*a, **k):
        raise OSError("Сеть в песочнице отключена")

    class __BlockedSocket(__sk.socket):
        def __init__(self, *a, **k):
            raise OSError("Сеть в песочнице отключена")

    __sk.socket = __BlockedSocket
    __sk.socketpair = __blocked
    __sk.create_connection = __blocked
    __sk.create_server = __blocked
    try:
        import _socket as __csk
        __csk.socket = __BlockedSocket
    except Exception:
        pass


try:
    __block_network()
except Exception:
    pass
del __block_network
'''


@functools.lru_cache(maxsize=1)
def _unshare_available() -> bool:
    """Можно ли резать сеть ядром: `unshare -n` (нужны права)."""
    exe = shutil.which("unshare")
    if not exe:
        return False
    try:
        probe = subprocess.run([exe, "-n", "true"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=3)
        return probe.returncode == 0
    except Exception:
        return False


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str | None = None


@dataclass
class RunOutcome:
    status: str                      # accepted | failed | error
    tests: list[TestResult] = field(default_factory=list)
    message: str | None = None


def _build_script(code: str, function: str, args_json: str) -> str:
    return f"""\
# -*- coding: utf-8 -*-
{_NET_GUARD}
{code}

# ===== harness (автогенерация, не редактируй) =====
import json as __json, traceback as __tb
__out = {{"ok": False, "error": "харнесс не выполнился"}}
try:
    __args = __json.loads({args_json!r})
    __value = {function}(*__args)
    try:
        __encoded = __json.dumps(__value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        __encoded = __json.dumps(str(__value), ensure_ascii=False)
    __out = {{"ok": True, "value": __encoded}}
except SystemExit as __e:
    __out = {{"ok": False, "error": f"Программа вызвала sys.exit({{__e.code}})"}}
except BaseException:
    __out = {{"ok": False, "error": __tb.format_exc()}}
with open({RESULT_FILE!r}, "w", encoding="utf-8") as __f:
    __json.dump(__out, __f, ensure_ascii=False)
"""


def _limits():
    """Ограничения ресурсов в дочернем процессе (POSIX)."""
    mem = RUNNER_MEMORY_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_CPU, (RUNNER_CPU_SECONDS, RUNNER_CPU_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _friendly_error(traceback_text: str) -> str:
    """Последняя строка traceback -> короткое сообщение для ученика."""
    lines = [ln for ln in traceback_text.strip().splitlines() if ln.strip()]
    if not lines:
        return "Неизвестная ошибка выполнения"
    last = lines[-1].strip()
    return last if len(last) <= 300 else last[:300] + "…"


def _fmt(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return repr(value)


class LocalRunner:
    def run(self, code: str, function: str, tests: list[dict]) -> RunOutcome:
        if not tests:
            return RunOutcome("error", [], "У задачи нет тестов — сообщи учителю")

        try:
            compile(code, "<student_code>", "exec")
        except SyntaxError as e:
            line = f" (строка {e.lineno})" if e.lineno else ""
            return RunOutcome("error", [], f"Ошибка синтаксиса{line}: {e.msg}")
        except (ValueError, MemoryError, RecursionError) as e:
            return RunOutcome("error", [], f"Код не удалось прочитать: {e}")

        results = [self._run_one(code, function, test, index)
                   for index, test in enumerate(tests, start=1)]

        if all(r.passed for r in results):
            return RunOutcome("accepted", results, None)
        return RunOutcome("failed", results, None)

    # ------------------------------------------------------------------
    def _run_one(self, code: str, function: str, test: dict, index: int) -> TestResult:
        args = test.get("input", [])
        expected = test.get("expected")
        name = f"тест {index}: {function}({', '.join(_fmt(a) for a in args)})"

        with tempfile.TemporaryDirectory(prefix="pyrun_") as tmp:
            script_path = os.path.join(tmp, "main.py")
            with open(script_path, "w", encoding="utf-8") as fh:
                fh.write(_build_script(code, function, json.dumps(args, ensure_ascii=False)))

            cmd = [sys.executable, "-I", script_path]
            if _unshare_available():
                # Сеть режется ядром: код бежит в своём сетевом namespace.
                cmd = [shutil.which("unshare"), "-n", *cmd]

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=tmp,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=RUNNER_TIMEOUT_SECONDS,
                    env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"},
                    preexec_fn=_limits,
                    start_new_session=True,
                    text=True,
                    errors="replace",
                )
            except subprocess.TimeoutExpired:
                return TestResult(name, False,
                                  f"Превышено время выполнения ({int(RUNNER_TIMEOUT_SECONDS)} с) — "
                                  "возможно, у тебя бесконечный цикл")

            result_path = os.path.join(tmp, RESULT_FILE)
            payload = None
            if os.path.exists(result_path):
                try:
                    with open(result_path, encoding="utf-8") as fh:
                        payload = json.load(fh)
                except (OSError, json.JSONDecodeError):
                    payload = None

            if payload is None:
                # Код упал до записи результата (ошибка на верхнем уровне, sys.exit, память…)
                return TestResult(name, False, self._crash_message(proc))

            if not payload.get("ok"):
                return TestResult(name, False,
                                  "Ошибка выполнения: " + _friendly_error(payload.get("error", "")))

            try:
                actual = json.loads(payload["value"])
            except (KeyError, json.JSONDecodeError):
                actual = payload.get("value")

            if actual == expected:
                return TestResult(name, True)
            return TestResult(name, False,
                              f"Ожидалось {_fmt(expected)}, получено {_fmt(actual)}")

    @staticmethod
    def _crash_message(proc: subprocess.CompletedProcess) -> str:
        stderr = (proc.stderr or "").strip()
        if "MemoryError" in stderr:
            return "Не хватило памяти — проверь, нет ли бесконечного добавления в список"
        if "EOFError" in stderr or "Программа вызвала sys.exit" in stderr:
            return "Программа завершилась раньше времени (возможно, вызов input() или sys.exit)"
        if proc.returncode == -9:
            return "Процесс был остановлен: слишком много ресурсов"
        if stderr:
            return "Ошибка выполнения: " + _friendly_error(stderr)
        return "Программа завершилась без результата"
