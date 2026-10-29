"""Publish only immutable, editorially approved research packages. No generation."""
import datetime as dt
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET

HOST = 'xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai'
LICENSES = {'https://creativecommons.org/licenses/by/2.0/',
            'https://creativecommons.org/licenses/by/4.0/'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(root, relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts or '\\' in relative:
        raise ValueError('Invalid package path')
    path = root / relative
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError('Symlinks are not allowed in release paths')
        cursor = cursor.parent
    if root.resolve() not in path.resolve().parents:
        raise ValueError('Path escapes package')
    return path


def packages(repo):
    root = repo / 'tools/research/packages'
    result = []
    for path in sorted(root.glob('*/manifest.json')):
        m = json.loads(path.read_text())
        if m.get('status') != 'approved':
            continue
        if m.get('schema') != 1 or not re.fullmatch('[a-z0-9-]+', m.get('id', '')):
            raise ValueError('Invalid release identity')
        if path.parent.name != m['id']:
            raise ValueError('Package directory and identity differ')
        review = m.get('review', {})
        if not review.get('reviewer') or not review.get('checked_at') or not review.get('scope'):
            raise ValueError('Missing editorial review')
        source = m.get('source', {})
        if source.get('license_url') not in LICENSES or not source.get('doi'):
            raise ValueError('Source rights require a supported explicit licence')
        slug = m['slug']
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-[a-z0-9-]+', slug):
            raise ValueError('Invalid article slug')
        if dt.date.fromisoformat(m['not_before']) < dt.date.fromisoformat(slug[:10]):
            raise ValueError('Release cannot precede article date')
        records = m['files']
        paths = [row['path'] for row in records]
        if len(paths) != len(set(paths)):
            raise ValueError('Duplicate destination')
        article = f'src/content/articles/{slug}.md'
        asset = f'public/downloads/research/{m["id"]}/'
        required = {article, *(asset + name for name in
                    ('original.pdf', 'original.html', 'translation.pdf', 'translation.html'))}
        if not required.issubset(paths):
            raise ValueError('Incomplete article/offline package')
        for row in records:
            name = row['path']
            if name != article and not name.startswith(asset):
                raise ValueError('Package can only add its article and downloads')
            src = contained(path.parent / 'files', name)
            if not src.is_file() or digest(src) != row['sha256']:
                raise ValueError('Package hash mismatch: ' + name)
            dst = contained(repo, name)
            if dst.exists() and digest(dst) != row['sha256']:
                raise ValueError('Refusing to overwrite existing content: ' + name)
        for row in m['evidence']:
            src = contained(path.parent, row['path'])
            if not src.is_file() or digest(src) != row['sha256']:
                raise ValueError('Evidence hash mismatch')
        evidence = {x['path']: x['sha256'] for x in m['evidence']}
        if evidence.get('evidence/source.xml') != source.get('sha256'):
            raise ValueError('Source evidence is not bound to the release')
        xml = ET.parse(path.parent / 'evidence/source.xml').getroot()
        doi = xml.find('.//article-meta/article-id[@pub-id-type="doi"]')
        rights = xml.find('.//article-meta/permissions')
        if doi is None or doi.text.lower() != source['doi'].lower() or rights is None:
            raise ValueError('Source metadata mismatch')
        rights_text = ET.tostring(rights, encoding='unicode').replace('http:', 'https:')
        if source['license_url'].rstrip('/') not in rights_text:
            raise ValueError('Licence is not present in the source')
        body = contained(path.parent / 'files', article).read_text()
        if f'translationId: "{m["id"]}"' not in body or source['doi'] not in body:
            raise ValueError('Article provenance differs from manifest')
        if not re.search(r'^date: "?' + re.escape(slug[:10]) + r'"?$', body, re.M):
            raise ValueError('Article date differs from release slug')
        result.append((path.parent, m))
    return result


def installed(repo, manifest):
    exists = [(repo / row['path']).exists() for row in manifest['files']]
    if any(exists) and not all(exists):
        raise ValueError('Partial package installation requires inspection')
    return all(exists)


def published_this_week(repo, today):
    for path in (repo / 'src/content/articles').glob('*.md'):
        body = path.read_text()
        if 'translationId:' not in body:
            continue
        match = re.search(r'^date: ["\']?(\d{4}-\d{2}-\d{2})', body, re.M)
        if match and dt.date.fromisoformat(match[1]).isocalendar()[:2] == today.isocalendar()[:2]:
            return True
    return False


def select(repo, today):
    ready = [(p, m) for p, m in packages(repo) if not installed(repo, m)]
    if published_this_week(repo, today):
        return None, 'cadence_wait', len(ready)
    eligible = [(p, m) for p, m in ready if dt.date.fromisoformat(m['not_before']) <= today]
    if eligible:
        return eligible[0], 'ready', len(ready)
    return None, 'scheduled' if ready else 'needs_translation', len(ready)


def install_and_build(repo, package, manifest, build):
    """Rollback only files created by this invocation if validation/build fails."""
    created = []
    try:
        for row in manifest['files']:
            dst = contained(repo, row['path'])
            if dst.exists():
                raise ValueError('Destination already exists')
            dst.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive create avoids clobbering a concurrent writer.
            with dst.open('xb') as stream:
                stream.write(contained(package / 'files', row['path']).read_bytes())
            created.append((dst, row['sha256']))
        build()
    except Exception:
        for dst, sha in created:
            if dst.is_file() and digest(dst) == sha:
                dst.unlink()
        raise
    return [p for p, _ in created]


def publication(manifest):
    return {
        'id': manifest['id'], 'question': manifest['title'],
        'published': f'https://{HOST}/articles/{manifest["slug"]}/',
        'source_doi': manifest['source']['doi'],
        'source_sha256': manifest['source']['sha256'],
        'assets': [{'url': f'https://{HOST}/' + x['path'][len('public/'):],
                    'sha256': x['sha256']} for x in manifest['files'] if x['path'].startswith('public/')],
    }
