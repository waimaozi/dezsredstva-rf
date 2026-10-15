"""Wait for the real Pages deployment, then notify IndexNow."""
import json
from pathlib import Path
import sys
import time
from common import fetch, now, save

path = Path(sys.argv[1]) / 'last-run.json'
status = json.loads(path.read_text())
url = status.get('published')
if not url:
    raise SystemExit('No published article to verify')
for attempt in range(20):
    try:
        raw = fetch(url, timeout=20).decode()
        if status['question'] in raw:
            break
    except (RuntimeError, OSError):
        pass
    time.sleep(30)
else:
    raise SystemExit('Pages deployment did not become available within 10 minutes')
status['live_verified_at'] = now()
save(path, status)
host = 'xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai'
key = '16698f6cf34e44099895947d8dab1ac2'
try:
    fetch('https://api.indexnow.org/indexnow', {
        'host': host, 'key': key, 'keyLocation': f'https://{host}/{key}.txt',
        'urlList': [url, f'https://{host}/perevody/']}, timeout=30)
    status['indexnow'] = 'accepted'
except (RuntimeError, OSError) as error:
    status['indexnow'] = str(error)[:100]
save(path, status)
print(json.dumps(status, ensure_ascii=False))
