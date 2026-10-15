#!/usr/bin/env python3
"""At most one source-backed translation per run; all evidence stays in state_dir."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from translation.article import prepare
from translation.common import now, save
from translation.demand import collect, evidence_for
from translation.quality import translate, review, validate
from translation.sources import read_source

REPO = Path(__file__).resolve().parent.parent
HOST = 'xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, text=True).strip()


def already_published(item):
    return any(f'translationId: "{item["id"]}"' in p.read_text()
               for p in (REPO / 'src/content/articles').glob('*.md'))


def commit(files, message):
    paths = [str(p.relative_to(REPO)) for p in files]
    git('add', '--', *paths)
    if git('diff', '--cached', '--name-only'):
        git('commit', '-m', message)
    # Retryable: a failed push leaves the commit for the wrapper to push next time.
    git('push', 'origin', 'HEAD:main')
    return git('rev-parse', 'HEAD')


def run(args):
    state = Path(args.state_dir).resolve()
    state.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence_dir = state / 'runs' / stamp
    evidence_dir.mkdir(parents=True)
    status = {'checked_at': now(), 'status': 'running', 'cadence': 'weekly',
              'schedule': 'Tuesday 09:00 Europe/Moscow', 'published': None}
    save(state / 'last-run.json', status)
    try:
        if args.publish and git('status', '--porcelain'):
            raise RuntimeError('Operational checkout has uncommitted files; refusing to publish')
        # A manual retry must not create a second article in the same ISO week.
        if args.publish:
            current_week = dt.datetime.now(dt.timezone.utc).date().isocalendar()[:2]
            for path in (REPO / 'src/content/articles').glob('*.md'):
                if 'translationId: ' not in path.read_text():
                    continue
                try:
                    published_week = dt.date.fromisoformat(path.name[:10]).isocalendar()[:2]
                except ValueError:
                    continue
                if published_week == current_week:
                    previous = REPO / 'public/publisher-status.json'
                    if previous.exists():
                        save(state / 'last-run.json', json.loads(previous.read_text()))
                    print('A translation is already published this ISO week; no duplicate run')
                    return 0
        demand = collect(state / 'demand.json', args.refresh_demand)
        save(evidence_dir / 'demand.json', demand)
        catalog = json.loads((REPO / 'tools/translation/catalog.json').read_text())
        candidates = []
        for item in catalog:
            evidence = evidence_for(item, demand)
            if evidence and not already_published(item):
                candidates.append((item, evidence))
        mapped = {q.casefold() for item in catalog for q in item['queries']}
        unmatched = [dict(result, provider=row['provider'], seed=row['seed'])
                     for row in demand['rows'] for result in row['response'].get('results', [])
                     if result['phrase'].casefold() not in mapped]
        save(state / 'queue.json', {'checked_at': now(), 'candidates': [
            {'id': i['id'], 'question': i['title'], 'evidence': e} for i, e in candidates],
            'unmatched_searches': unmatched, 'note': 'New source mappings require editorial verification.'})
        status['eligible_questions'] = len(candidates)
        status['demand_providers'] = sorted({r['provider'] for r in demand['rows']})
        if not candidates:
            status['status'] = 'needs_sources' if all(already_published(i) for i in catalog) else 'no_matching_demand'
        else:
            # Catalog order reflects question specificity, not largest volume.
            item, evidence = candidates[0]
            status['question'] = item['title']
            source = read_source(item)
            save(evidence_dir / 'source.json', source)
            save(evidence_dir / 'selection.json', {'item': item, 'demand': evidence})
            if getattr(args, 'prepared', None):
                prepared = json.loads(Path(args.prepared).read_text())
                if prepared['item'] != item or prepared['source']['sha256'] != source['sha256']:
                    raise RuntimeError('Prepared translation does not match the selected current source')
                target = prepared['target']
                validate(source['segments'], target)
                save(evidence_dir / 'prepared.json', prepared)
            else:
                target = translate(source['segments'], evidence_dir)
            review(source['segments'], target, evidence_dir)
            if not args.publish:
                status['status'] = 'validated_preview'
                save(evidence_dir / 'preview.json', {'item': item, 'source': source, 'target': target, 'demand': evidence})
            else:
                slug, files = prepare(REPO, item, source, target, evidence)
                status.update(status='published', published=f'https://{HOST}/articles/{slug}/',
                              demand=evidence, source_sha256=source['sha256'],
                              source_retrieval=source.get('retrieval'),
                              source_checked_at=source.get('checked_at', now()))
                save(REPO / 'public/publisher-status.json', status)
                files.append(REPO / 'public/publisher-status.json')
                subprocess.run(['npm', 'run', 'build'], cwd=REPO, check=True,
                               stdout=(evidence_dir / 'build.log').open('w'), stderr=subprocess.STDOUT)
                status['commit'] = commit(files, f'content: translate {item["id"]} from verified source')
        if args.publish and not status['published']:
            save(REPO / 'public/publisher-status.json', status)
            status['commit'] = commit([REPO / 'public/publisher-status.json'], 'chore: report translation queue status')
        save(state / 'last-run.json', status)
        save(evidence_dir / 'status.json', status)
        print(json.dumps(status, ensure_ascii=False))
        return 0 if status['status'] in ('published', 'validated_preview') else 2
    except Exception as error:
        status.update(status='failed', error=f'{type(error).__name__}: {str(error)[:200]}')
        save(state / 'last-run.json', status)
        save(evidence_dir / 'status.json', status)
        print(json.dumps(status, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--publish', action='store_true', help='Build, commit and push one translation')
    parser.add_argument('--refresh-demand', action='store_true')
    parser.add_argument('--prepared', help='Promote a preview after matching its source and rerunning fidelity review')
    sys.exit(run(parser.parse_args()))
