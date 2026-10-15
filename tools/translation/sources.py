"""Extract only editor-approved CDC text sections, retaining table structure."""
import hashlib
import html
import json
import datetime as dt
from pathlib import Path
import subprocess
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString
from .common import fetch

ALLOWED = {'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'li', 'table', 'thead',
           'tbody', 'tr', 'th', 'td', 'a', 'br', 'strong', 'em'}


def extract(raw, item):
    soup = BeautifulSoup(raw, 'html.parser')
    section = soup.select_one(item['selector'])
    if section is None:
        raise RuntimeError('Approved section is missing')
    for node in section.select('script, style, img, figure, .onThisPageAnchor'):
        node.decompose()
    for node in section.select('span.text-underline'):
        value = node.get_text(strip=True)
        if value in ('<', '>'):
            node.replace_with('≤' if value == '<' else '≥')
    for node in list(section.find_all(True)):
        if node.name not in ALLOWED:
            node.unwrap()
    segments = {}

    def walk(node):
        if isinstance(node, NavigableString):
            text = ' '.join(str(node).split())
            if not text:
                return None
            key = f's{len(segments):03}'
            segments[key] = text
            return {'id': key}
        children = [x for child in node.children if (x := walk(child)) is not None]
        attrs = {}
        if node.name == 'a' and node.get('href'):
            url = urljoin(item['url'], node['href'])
            if url.startswith('https://'):
                attrs = {'href': url, 'target': '_blank', 'rel': 'noopener'}
        for attr in ('rowspan', 'colspan'):
            if node.name in ('td', 'th') and str(node.get(attr, '')).isdigit():
                attrs[attr] = node[attr]
        return {'tag': node.name if node.name in ALLOWED else 'div', 'attrs': attrs, 'children': children}

    tree = walk(section)
    if not 100 <= len(' '.join(segments.values()).split()) <= 2500:
        raise RuntimeError('Unexpected section length')
    canonical = json.dumps({'tree': tree, 'segments': segments}, ensure_ascii=False, sort_keys=True)
    return {'tree': tree, 'segments': segments, 'sha256': hashlib.sha256(canonical.encode()).hexdigest()}


def read_source(item):
    if not item['url'].startswith('https://www.cdc.gov/healthcare-associated-infections/hcp/cleaning-global/'):
        raise RuntimeError('Source is outside the approved library')
    try:
        try:
            raw = fetch(item['url'])
        except (RuntimeError, OSError):
            # Some CDC edges reject urllib's TLS profile but accept curl.
            result = subprocess.run(['curl', '--fail', '--silent', '--show-error',
                                     '--location', '--max-time', '40', item['url']],
                                    capture_output=True, timeout=45)
            if result.returncode:
                raise RuntimeError('CDC could not be fetched from this server')
            raw = result.stdout
    except (RuntimeError, OSError, subprocess.TimeoutExpired):
        checked = dt.date.fromisoformat(item['source_checked_at'])
        if (dt.datetime.now(dt.timezone.utc).date() - checked).days > 30:
            raise RuntimeError('Source unreachable and checked snapshot is older than 30 days')
        source = json.loads((Path(__file__).parent / 'snapshots' / (item['id'] + '.json')).read_text())
        canonical = json.dumps({'tree': source['tree'], 'segments': source['segments']}, ensure_ascii=False, sort_keys=True)
        source['sha256'] = hashlib.sha256(canonical.encode()).hexdigest()
        source['retrieval'] = 'approved_snapshot'
        source['checked_at'] = item['source_checked_at']
    else:
        # A reachable page with changed structure is not a network failure.
        source = extract(raw, item)
        source['retrieval'] = 'live'
    if source['sha256'] != item['approved_sha256']:
        raise RuntimeError('Source changed: section and rights need editorial recheck')
    return source


def render(tree, texts):
    if 'id' in tree:
        return html.escape(texts[tree['id']])
    tag = tree['tag']
    attrs = ''.join(f' {k}="{html.escape(str(v), quote=True)}"' for k, v in tree['attrs'].items())
    if tag == 'br':
        return '<br>'
    return f'<{tag}{attrs}>' + ' '.join(render(c, texts) for c in tree['children']) + f'</{tag}>'
