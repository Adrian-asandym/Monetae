#!/usr/bin/env bash
# Synthetic, isolated real-server session/CSRF probe; no browser required.
set -euo pipefail
repo_root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$repo_root"
if [[ -e .env ]]; then
  echo 'Se requiere un worktree sin .env; no se sobrescribe configuración existente.' >&2
  exit 1
fi
if [[ ! -f apps/web/build/web/index.html ]]; then
  echo 'Ejecutar primero: cd apps/web && flutter build web --release' >&2
  exit 1
fi
export COMPOSE_PROJECT_NAME=monetae-t503
export MONETAE_DB_PORT=5444 MONETAE_API_PORT=8001 MONETAE_WEB_PORT=8081
probe_dir=$(mktemp -d)
compose=(docker compose -f infra/docker-compose.yml)
cleanup() {
  "${compose[@]}" down -v
  rm -f .env
  rm -rf "$probe_dir"
}
cp .env.example .env
trap cleanup EXIT
sed -i 's/^MONETAE_COOKIE_SECURE=true$/MONETAE_COOKIE_SECURE=false/' .env
"${compose[@]}" up -d --build db api web
for attempt in {1..60}; do
  if curl --silent --fail http://localhost:8081/api/v1/health > "$probe_dir/health.json"; then break; fi
  sleep 1
done
curl --silent --show-error --fail http://localhost:8081/api/v1/health > "$probe_dir/health.json"
"${compose[@]}" exec -T api alembic upgrade head
printf '%s\n' 'Synthetic-T503-password' | "${compose[@]}" exec -T api python -m monetae.cli create-user --email t503@example.test --password-stdin
origin=http://localhost:8081
request() {
  local expected=$1 name=$2
  shift 2
  local status
  status=$(curl --silent --show-error --output "$probe_dir/response.json" --write-out '%{http_code}' "$@")
  echo "$name: $status (esperado $expected)"
  [[ "$status" == "$expected" ]]
}
request 200 index "$origin/"
# Profile 401 obtains the pre-login CSRF cookie exactly as the Flutter bootstrap.
request 401 bootstrap --cookie-jar "$probe_dir/cookies" "$origin/api/v1/users/me"
csrf=$(awk '$6 == "monetae_csrf" {print $7}' "$probe_dir/cookies")
request 200 login --cookie "$probe_dir/cookies" --cookie-jar "$probe_dir/cookies" \
  -H "Origin: $origin" -H "X-CSRF-Token: $csrf" -H 'Content-Type: application/json' \
  --data '{"method":"password","email":"t503@example.test","password":"Synthetic-T503-password"}' "$origin/api/v1/auth/login"
request 200 profile --cookie "$probe_dir/cookies" "$origin/api/v1/users/me"
csrf=$(awk '$6 == "monetae_csrf" {print $7}' "$probe_dir/cookies")
prefs='{"preferences":{"theme":"dark","accent_color":"#BA7DBD","home_widgets":["accounts","transactions"],"transaction_card":{"show_date":false,"show_time":true,"show_note":false,"show_tags":false,"show_account":true,"show_actions":true}}}'
request 200 patch --cookie "$probe_dir/cookies" -X PATCH -H "Origin: $origin" \
  -H "X-CSRF-Token: $csrf" -H 'Content-Type: application/json' --data "$prefs" "$origin/api/v1/users/me"
python3 - "$probe_dir/response.json" <<'PY'
import json, sys
profile = json.load(open(sys.argv[1]))
prefs = profile['preferences']
assert prefs['theme'] == 'dark'
assert prefs['accent_color'] == '#BA7DBD'
assert prefs['home_widgets'] == ['accounts', 'transactions']
assert prefs['transaction_card'] == dict(show_date=False, show_time=True, show_note=False, show_tags=False, show_account=True, show_actions=True)
print('Preferencias completas: conservadas')
PY
request 403 patch-without-csrf --cookie "$probe_dir/cookies" -X PATCH -H "Origin: $origin" \
  -H 'Content-Type: application/json' --data "$prefs" "$origin/api/v1/users/me"
request 403 patch-wrong-origin --cookie "$probe_dir/cookies" -X PATCH -H 'Origin: http://localhost:8082' \
  -H "X-CSRF-Token: $csrf" -H 'Content-Type: application/json' --data "$prefs" "$origin/api/v1/users/me"
request 200 logout --cookie "$probe_dir/cookies" --cookie-jar "$probe_dir/cookies" -X POST \
  -H "Origin: $origin" -H "X-CSRF-Token: $csrf" "$origin/api/v1/auth/logout"
request 401 profile-after-logout --cookie "$probe_dir/cookies" "$origin/api/v1/users/me"
