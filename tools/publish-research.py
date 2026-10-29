#!/usr/bin/env python3
"""Weekly release of one reviewed research translation, with restartable verification."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
from research.queue import install_and_build, installed, packages, publication, select
from translation.common import now, save

REPO = Path(__file__).resolve().parent.parent


def run(args):
    state = Path(args.state_dir).resolve()
    state.mkdir(parents=True, exist_ok=True)
    status = {'checked_at': now(), 'cadence': 'weekly',
              'schedule': 'Tuesday 09:00 Europe/Moscow', 'mode': 'reviewed_research',
              'published': None}
    def git(*cmd):
        return subprocess.check_output(['git', *cmd], cwd=REPO, text=True).strip()
    try:
        if args.publish and git('status', '--porcelain'):
            raise RuntimeError('Operational checkout has uncommitted changes')
        all_packages = packages(REPO)
        pending = state / 'last-publication.json'
        if args.publish and pending.exists():
            previous = json.loads(pending.read_text())
            if not previous.get('live_verified_at') or previous.get('indexnow') != 'accepted':
                match = next((m for _, m in all_packages if m['id'] == previous['id']), None)
                if match and installed(REPO, match):
                    # Wrapper has already pushed any retained local commit.
                    save(state / 'last-run.json', previous)
                    print('Resuming live verification of the previous release')
                    return 0
        chosen, reason, count = select(REPO, dt.datetime.now(dt.timezone.utc).date())
        candidates = json.loads((REPO / 'tools/research/candidates.json').read_text())
        status.update(status=reason, approved_remaining=count,
                      verified_sources=sum(c['status'] == 'verified_source' for c in candidates))
        if chosen:
            package, m = chosen
            status.update(publication(m))
            if args.publish:
                evidence = state / 'research-runs' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                evidence.mkdir(parents=True, exist_ok=True)
                def build():
                    with (evidence / 'build.log').open('w') as log:
                        subprocess.run(['npm', 'run', 'build'], cwd=REPO, check=True,
                                       stdout=log, stderr=subprocess.STDOUT)
                        subprocess.run(['node', 'scripts/check-discovery.mjs'], cwd=REPO, check=True,
                                       stdout=log, stderr=subprocess.STDOUT)
                files = install_and_build(REPO, package, m, build)
                status.update(status='awaiting_deployment', approved_remaining=count - 1)
                # Preserve the verification job before commit/push, including push failures.
                save(pending, status)
                save(evidence / 'release.json', status)
                save(REPO / 'public/publisher-status.json', status)
                files.append(REPO / 'public/publisher-status.json')
                git('add', '--', *(str(p.relative_to(REPO)) for p in files))
                git('commit', '-m', 'content: publish reviewed research ' + m['id'])
                status['commit'] = git('rev-parse', 'HEAD')
                save(pending, status)
                save(state / 'last-run.json', status)
                git('push', 'origin', 'HEAD:main')
            else:
                status.update(status='validated_preview', published=None)
        elif args.publish and reason != 'cadence_wait':
            # Empty queue is an editorial need, not a runtime crash.
            save(REPO / 'public/publisher-status.json', status)
            git('add', '--', 'public/publisher-status.json')
            if git('diff', '--cached', '--name-only'):
                git('commit', '-m', 'chore: report reviewed research queue status')
                git('push', 'origin', 'HEAD:main')
        save(state / 'last-run.json', status)
        print(json.dumps(status, ensure_ascii=False))
        return 0
    except Exception as error:
        status.update(status='failed', error=f'{type(error).__name__}: {str(error)[:200]}')
        save(state / 'last-run.json', status)
        print(json.dumps(status, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--publish', action='store_true')
    sys.exit(run(parser.parse_args()))
