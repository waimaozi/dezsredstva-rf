"""Bounded HTTP calls and private operational evidence. Never log credentials."""
import datetime as dt
import json
import os
import time
from pathlib import Path
import urllib.error
import urllib.request


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def secret(name):
    if os.environ.get(name):
        return os.environ[name].strip()
    if os.environ.get(name + '_FILE'):
        return Path(os.environ[name + '_FILE']).read_text().strip()
    raise RuntimeError('Missing credential: ' + name)


def fetch(url, body=None, headers=None, timeout=45):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'DezsredstvaTranslations/1.0',
        **({'Content-Type': 'application/json'} if data else {}), **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise RuntimeError('Response exceeds 8 MB')
            return raw
    except urllib.error.HTTPError as error:
        # Upstream bodies can contain sensitive request details; do not log them.
        raise RuntimeError(f'Upstream HTTP {error.code}') from None


def json_fetch(url, body=None, headers=None, timeout=45):
    return json.loads(fetch(url, body, headers, timeout))


def chat(prompt, output, max_tokens=14000):
    model = os.environ.get('KIE_MODEL', 'gemini-4-argon-openai')
    if model != 'gemini-4-argon-openai':
        raise RuntimeError('Model change requires the acceptance tests to be rerun')
    payload = {
        'model': model, 'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0, 'max_tokens': max_tokens, 'stream': False,
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': 'publisher_output', 'strict': True, 'schema': {'type': 'object'}}},
    }
    for attempt in range(3):
        try:
            result = json_fetch(f'https://api.kie.ai/{model}/v1/chat/completions', payload,
                {'Authorization': 'Bearer ' + secret('KIE_API_KEY')}, timeout=180)
            break
        except RuntimeError as error:
            if str(error) not in {'Upstream HTTP 429', 'Upstream HTTP 502', 'Upstream HTTP 503', 'Upstream HTTP 504'} or attempt == 2:
                raise
            time.sleep((10, 30)[attempt])
    if not isinstance(result, dict) or not result.get('choices'):
        code = result.get('code', 'missing_choices') if isinstance(result, dict) else 'invalid_json'
        raise RuntimeError(f'Provider returned no completion (code={code})')
    choice = result['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise RuntimeError('Provider completion was truncated or refused')
    content = choice['message']['content'].strip()
    save(output.with_suffix('.provider.json'), {
        'model': model, 'checked_at': now(), 'usage': result.get('usage'),
        'finish_reason': choice.get('finish_reason'), 'content': content})
    if content.startswith('```'):
        content = content.split('\n', 1)[1].rsplit('```', 1)[0]
    parsed = json.loads(content)
    save(output, {'model': model, 'checked_at': now(), 'usage': result.get('usage'), 'result': parsed})
    return parsed
