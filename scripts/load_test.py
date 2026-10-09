#!/usr/bin/env python3
"""Нагрузочный тест: «класс из N учеников».

Сценарий (как на реальном уроке):
  1. регистрируется учитель и создаёт класс (получаем код);
  2. N учеников ОДНОВРЕМЕННО регистрируются по коду класса;
  3. каждый ученик ОДНОВРЕМЕННО отправляет верное решение задачи №1.

Печатает: успех/ошибки, время ответа (медиана / p95 / максимум).

Использование:
    python3 scripts/load_test.py [BASE_URL] [-n 30]
    docker compose up -d && python3 scripts/load_test.py http://127.0.0.1:8080
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SOLUTION = 'def hello(name):\n    return f"Привет, {name}!"\n'
PASSWORD = "loadtest123"


def call(base, method, path, payload=None, token=None, timeout=60):
    """HTTP-запрос -> (status, тело-bytes, секунды). Ошибки не бросают исключений."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), time.perf_counter() - started
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.perf_counter() - started
    except Exception as e:  # noqa: BLE001 — вернём как «нет ответа»
        return 0, str(e).encode("utf-8"), time.perf_counter() - started


def _stats(times):
    if not times:
        return "—"
    times = sorted(times)
    p95 = times[min(len(times) - 1, int(round(0.95 * len(times))) - 1)]
    return (f"медиана {statistics.median(times) * 1000:.0f} мс · "
            f"p95 {p95 * 1000:.0f} мс · макс {times[-1] * 1000:.0f} мс")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://127.0.0.1:8000")
    ap.add_argument("-n", "--students", type=int, default=30, help="число учеников")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    stamp = int(time.time())

    print(f"Сервер: {base} | учеников: {args.students}")

    # 1. Учитель
    status, body, _ = call(base, "POST", "/api/auth/register", {
        "email": f"load-{stamp}@test.ru", "username": f"Нагрузка-{stamp}",
        "password": PASSWORD})
    if status != 200:
        print(f"❌ регистрация учителя: {status} {body[:200].decode(errors='replace')}")
        return 1
    teacher = json.loads(body)["access_token"]

    # 2. Класс
    status, body, _ = call(base, "POST", "/api/classes",
                           {"name": f"Нагрузка {stamp}"}, teacher)
    if status != 200:
        print(f"❌ создание класса: {status} {body[:200].decode(errors='replace')}")
        return 1
    class_code = json.loads(body)["code"]
    print(f"Класс создан, код {class_code}")

    # 3. Ученики — одновременно
    def register(i):
        return call(base, "POST", "/api/auth/register-class", {
            "code": class_code, "username": f"Наг{i}-{stamp}", "password": PASSWORD})

    with ThreadPoolExecutor(max_workers=args.students) as ex:
        reg = list(ex.map(register, range(args.students)))

    tokens, reg_errors = [], 0
    for status, body, _ in reg:
        if status == 200:
            tokens.append(json.loads(body)["access_token"])
        else:
            reg_errors += 1
    print(f"Регистрация: успешно {len(tokens)}/{args.students}, ошибок {reg_errors}")
    if not tokens:
        return 1

    # 4. Отправка решений — одновременно
    def submit(token):
        return call(base, "POST", "/api/tasks/1/submit", {"code": SOLUTION}, token)

    with ThreadPoolExecutor(max_workers=len(tokens)) as ex:
        results = list(ex.map(submit, tokens))

    accepted, times, errors = 0, [], 0
    for status, body, secs in results:
        times.append(secs)
        if status == 200 and b'"accepted"' in body:
            accepted += 1
        else:
            errors += 1
            if errors == 1:
                print(f"  пример ошибки: {status} {body[:160].decode(errors='replace')}")

    print(f"Проверка кода: принято {accepted}/{len(tokens)}, ошибок {errors}")
    print(f"Время ответа: {_stats(times)}")

    ok = accepted == len(tokens) and reg_errors == 0
    print("✅ Нагрузку выдержали" if ok else "⚠️  Есть ошибки — смотри выше")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
