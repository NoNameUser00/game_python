#!/usr/bin/env bash
# Быстрая проверка работоспособности (после изменений / перед деплоем).
# Использование: ./scripts/smoke.sh [BASE_URL]
#   локально:  ./scripts/smoke.sh                (сервер должен быть запущен)
#   прод:      ./scripts/smoke.sh https://my.domain
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
EMAIL="smoke-$(date +%s)@test.ru"
PASS="smoke123"
ok()   { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; exit 1; }

echo "1. health"
curl -sf "$BASE/api/health" | grep -q '"ok"' && ok "сервер отвечает" || fail "health"

echo "2. регистрация"
TOKEN=$(curl -sf -X POST "$BASE/api/auth/register" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"username\":\"Смок\",\"password\":\"$PASS\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
[ -n "$TOKEN" ] && ok "токен получен" || fail "регистрация"
AUTH="Authorization: Bearer $TOKEN"

echo "3. карта тем"
N=$(curl -sf "$BASE/api/topics" -H "$AUTH" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))')
[ "$N" -ge 6 ] && ok "тем: $N" || fail "тем太少: $N"

echo "4. решение задачи"
RESP=$(curl -sf -X POST "$BASE/api/tasks/1/submit" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"code":"def hello(name):\n    return f\"Привет, {name}!\""}')
echo "$RESP" | grep -q '"accepted"' && ok "код принят" || fail "проверка кода: $RESP"
echo "$RESP" | grep -q '"xp_gained":[1-9]' && ok "XP начислены" || fail "XP не начислены"

echo "5. прогресс"
curl -sf "$BASE/api/me/progress" -H "$AUTH" | grep -q '"xp"' && ok="ok" || fail "прогресс"
ok "прогресс доступен"

echo ""
echo "Все проверки пройдены 🎉"
