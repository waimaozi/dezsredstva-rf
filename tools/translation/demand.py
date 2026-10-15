"""Search evidence, including low-volume phrases; no minimum-volume filter."""
import datetime as dt
import json
import urllib.parse
from .common import json_fetch, now, save, secret

SEEDS = ['люминометр', 'контроль качества уборки', 'приготовление дезрастворов',
         'хранение дезрастворов', 'обработка уборочного инвентаря',
         'дезинфекция салфетками', 'ротация дезсредств', 'биопленки дезинфекция',
         'удаление аллергенов']


def collect(path, refresh=False):
    if path.exists() and not refresh:
        old = json.loads(path.read_text())
        age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(old['checked_at'])
        if age.days < 7:
            return old
    rows, errors = [], []
    for seed in SEEDS:
        try:
            response = json_fetch('https://searchapi.api.cloud.yandex.net/v2/wordstat/topRequests', {
                'folderId': 'b1gkqumi4qjlgrhiuqgl', 'phrase': seed,
                'regions': ['225'], 'devices': ['DEVICE_ALL'], 'numPhrases': '100',
            }, {'Authorization': 'Api-Key ' + secret('YANDEX_API_KEY')}, timeout=25)
            if 'totalCount' not in response:
                raise RuntimeError('Wordstat returned an invalid result')
            rows.append({'seed': seed, 'provider': 'yandex_wordstat', 'period': 'last_30_days',
                         'region': 'Russia', 'match': 'phrase_family', 'response': response})
        except (RuntimeError, ValueError, OSError) as error:
            errors.append({'seed': seed, 'provider': 'yandex_wordstat', 'error': str(error)[:150]})
            url = 'https://suggestqueries.google.com/complete/search?' + urllib.parse.urlencode({
                'client': 'firefox', 'hl': 'ru', 'gl': 'ru', 'q': seed})
            try:
                response = json_fetch(url, timeout=20)
                if not isinstance(response, list) or len(response) < 2:
                    raise RuntimeError('Invalid Google suggestions')
                rows.append({'seed': seed, 'provider': 'google_suggest', 'period': None,
                             'region': 'ru parameter', 'match': 'suggestion_only',
                             'response': {'results': [{'phrase': p, 'count': None} for p in response[1]]}})
            except (RuntimeError, ValueError, OSError) as fallback_error:
                errors.append({'seed': seed, 'provider': 'google_suggest', 'error': str(fallback_error)[:150]})
    if not rows:
        raise RuntimeError('Both Wordstat and Google failed; search demand is unknown')
    result = {'checked_at': now(), 'rows': rows, 'errors': errors}
    save(path, result)
    return result


def evidence_for(item, demand):
    # These are editor-mapped queries, not model-generated evidence. A phrase
    # must actually appear in the provider response; seed totalCount is not enough.
    for query in item['queries']:
        for row in demand['rows']:
            for result in row['response'].get('results', []):
                if result['phrase'].casefold() == query.casefold():
                    if result.get('count') is not None and int(result['count']) <= 0:
                        continue
                    return {'phrase': result['phrase'], 'count': result.get('count'),
                            'provider': row['provider'], 'period': row['period'],
                            'match': row['match'], 'region': row['region'],
                            'checked_at': demand['checked_at']}
    return None
