#!/usr/bin/env bash

set -uo pipefail

REPO=/home/openclaw/dezsredstva-rf
LOG=/home/openclaw/logs/dezsredstva-run-daily.log
INDEXNOW_KEY=16698f6cf34e44099895947d8dab1ac2
HOST=xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai

utc_ts() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  printf '[%s] %s\n' "$(utc_ts)" "$*"
}

json_quote() {
  python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$1"
}

mkdir -p "$(dirname "$LOG")"
exec >> "$LOG" 2>&1

log "run-daily start"

if ! cd "$REPO"; then
  log "error: failed to cd to $REPO"
  exit 1
fi

if [[ -f "$REPO/.env" ]]; then
  set -a
  . ./.env
  source_rc=$?
  set +a

  if [[ "$source_rc" -ne 0 ]]; then
    log "error: failed to load $REPO/.env"
    exit 1
  fi
fi

if [[ -z "${KIE_API_KEY:-}" ]]; then
  log "error: KIE_API_KEY is not set"
  exit 1
fi

if ! git pull --rebase --autostash origin main; then
  log "warning: git pull --rebase --autostash origin main failed"
fi

before="$(git rev-parse HEAD 2>/dev/null)"
before_rc=$?
if [[ "$before_rc" -ne 0 || -z "$before" ]]; then
  log "error: failed to resolve HEAD before autopublish"
  exit 1
fi

python3 tools/autopublish.py --count 1
autopublish_rc=$?
if [[ "$autopublish_rc" -ne 0 ]]; then
  log "error: autopublish exited with code $autopublish_rc; not notifying IndexNow"
  exit 1
fi

after="$(git rev-parse HEAD 2>/dev/null)"
after_rc=$?
if [[ "$after_rc" -ne 0 || -z "$after" ]]; then
  log "error: failed to resolve HEAD after autopublish"
  exit 1
fi

if [[ "$before" == "$after" ]]; then
  log "no new article published"
  exit 0
fi

mapfile -t added_files < <(
  git show --pretty="" --name-only --diff-filter=A "$after" | grep -E '^src/content/articles/.+\.md$' || true
)

if [[ "${#added_files[@]}" -eq 0 ]]; then
  log "no added article files found in commit $after"
  exit 0
fi

urls=()
for f in "${added_files[@]}"; do
  slug="$(basename -- "$f" .md)"
  urls+=("https://$HOST/articles/$slug/")
done

log "urls to notify:"
printf '  %s\n' "${urls[@]}"

sleep 120

url_json_entries=()
for url in "${urls[@]}"; do
  url_json_entries+=("$(json_quote "$url")")
done

url_list_json=""
for ((i = 0; i < ${#url_json_entries[@]}; i++)); do
  if [[ "$i" -gt 0 ]]; then
    url_list_json+=","
  fi
  url_list_json+="${url_json_entries[$i]}"
done

key_location="https://$HOST/$INDEXNOW_KEY.txt"
body='{"host":'"$(json_quote "$HOST")"',"key":'"$(json_quote "$INDEXNOW_KEY")"',"keyLocation":'"$(json_quote "$key_location")"',"urlList":['"$url_list_json"']}'

http_code="$(
  curl -sS \
    --max-time 30 \
    -o /dev/null \
    -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d "$body" \
    'https://api.indexnow.org/indexnow' || true
)"
http_code="${http_code:-000}"
log "IndexNow HTTP status: $http_code"

log "done"
