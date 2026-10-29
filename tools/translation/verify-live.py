"""Wait for the real Pages deployment, then notify IndexNow."""
import json
import hashlib
import html
from pathlib import Path
import sys
import time
from common import fetch, now, save

path = Path(sys.argv[1]) / 'last-run.json'
status = json.loads(path.read_text())
url = status.get('published')
if not url:
    print('No new release awaiting verification')
    raise SystemExit(0)
for attempt in range(20):
    try:
        raw = fetch(url, timeout=20).decode()
        if status['question'] not in html.unescape(raw):
            raise RuntimeError('Article title missing')
        if status.get('source_doi') and status['source_doi'] not in raw:
            raise RuntimeError('Source attribution missing')
        for asset in status.get('assets', []):
            if hashlib.sha256(fetch(asset['url'], timeout=30)).hexdigest() != asset['sha256']:
                raise RuntimeError('Deployed download hash differs from approved package')
        if status.get('assets'):
            hub = fetch('https://xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai/perevody/', timeout=20).decode()
            if url.split('/articles/', 1)[1].strip('/') not in hub:
                raise RuntimeError('Translation missing from discovery hub')
        break
    except (RuntimeError, OSError):
        pass
    time.sleep(30)
else:
    raise SystemExit('Pages deployment did not become available within 10 minutes')
status['live_verified_at'] = now()
status['status'] = 'live_verified'
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
if status.get('mode') == 'reviewed_research':
    save(path.parent / 'last-publication.json', status)
print(json.dumps(status, ensure_ascii=False))
