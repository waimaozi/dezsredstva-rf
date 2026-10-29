#!/usr/bin/env bash
# Compatibility entrypoint; the systemd timer runs weekly in UTC.
set -euo pipefail
export PATH=/usr/local/bin:/usr/bin:/bin
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${DEZSREDSTVA_CONFIG:-/home/openclaw/.config/dezsredstva-publisher/runtime.env}"
set -a
source "$CONFIG"
set +a
mkdir -p "$DEZSREDSTVA_STATE"
exec 9>"$DEZSREDSTVA_STATE/run.lock"
flock -n 9 || { echo 'Another publisher run is active'; exit 1; }
cd "$REPO"
trap 'python3 tools/translation/record-failure.py "$DEZSREDSTVA_STATE" "$?"' ERR
test -z "$(git status --porcelain)" || { echo 'Operational checkout is dirty; inspect before retry'; false; }
git fetch origin main
# A prior push may have failed after a valid content commit. Never discard it.
git merge --ff-only origin/main
if [[ "$(git rev-list --count origin/main..HEAD)" != 0 ]]; then
  git push origin HEAD:main
fi
python3 tools/publish-research.py --state-dir "$DEZSREDSTVA_STATE" --publish
python3 tools/translation/verify-live.py "$DEZSREDSTVA_STATE"
