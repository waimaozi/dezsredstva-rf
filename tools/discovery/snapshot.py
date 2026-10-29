#!/usr/bin/env python3
"""Scheduled read-only snapshot with atomic history and explicit failure health."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def assess(data):
    failures = []
    for name in ('totals', 'search_engines', 'landing_pages', 'returning_visitors', 'reader_goals', 'reader_responses'):
        result = data.get('metrika', {}).get(name, {})
        if result.get('status') != 200 or 'totals' not in result.get('data', {}):
            failures.append('metrika:' + name)
    search = data.get('yandex_search', {})
    if search.get('status') != 200 or 'documents' not in search:
        failures.append('yandex_search')
    elif search.get('search_error_code') not in (None, '15'):
        failures.append('yandex_search:' + search['search_error_code'])
    if webmaster_state(data) == 'unavailable':
        failures.append('webmaster')
    return failures


def webmaster_state(data):
    if 'webmaster_access' not in data:
        return 'not_requested'
    if data['webmaster_access'].get('status') != 200:
        return 'unavailable'
    if not (data.get('webmaster_target_host') or {}).get('verified'):
        return 'unavailable'
    summary = data.get('webmaster_summary', {})
    if summary.get('status') == 200 and isinstance(summary.get('data'), dict):
        return 'available'
    if summary.get('status') == 404 and summary.get('api_error_code') == 'HOST_NOT_LOADED':
        return 'pending_data'
    return 'unavailable'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--oauth-file', required=True)
    parser.add_argument('--search-key-file', required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--webmaster', action='store_true')
    args = parser.parse_args()
    state = args.state_dir
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime('%Y%m%dT%H%M%SZ')
    pending = state / ('pending-' + stamp + '.json')
    health = {'checked_at': now.isoformat(), 'status': 'failed', 'failures': []}
    try:
        command = [sys.executable, str(Path(__file__).with_name('measure.py')),
                   '--oauth-file', args.oauth_file, '--search-key-file', args.search_key_file,
                   '--out', str(pending)]
        if args.webmaster:
            command.append('--webmaster')
        result = subprocess.run(command, capture_output=True, text=True, timeout=150)
        if result.returncode:
            raise RuntimeError('snapshot_transport_or_credentials')
        data = json.loads(pending.read_text())
        failures = assess(data)
        history = state / (stamp + '.json')
        pending.replace(history)
        health.update(status='ok' if not failures else 'partial', failures=failures,
                      snapshot=history.name, period=data['period'],
                      webmaster=webmaster_state(data))
        atomic_json(state / 'latest.json', data)
        if not failures:
            atomic_json(state / 'last-success.json', {'checked_at': now.isoformat(), 'snapshot': history.name})
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        # Never emit process stderr or credential-bearing exceptions.
        health['failures'] = [type(error).__name__]
    finally:
        pending.unlink(missing_ok=True)
        atomic_json(state / 'health.json', health)
    print(json.dumps(health))
    return 0 if health['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
