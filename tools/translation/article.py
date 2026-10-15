import datetime as dt
import html
import json
from pathlib import Path
from .sources import render

LICENSE = 'https://www.cdc.gov/other/agencymaterials.html'
NOTICE = ('Источник: CDC. Оригинал бесплатно доступен на сайте CDC. '
          'Этот русский перевод не является официальным переводом CDC. '
          'Публикация и ссылки не означают одобрения этого сайта, его услуг или продуктов '
          'со стороны CDC, HHS или правительства США.')
STYLE = '''body{max-width:820px;margin:32px auto;padding:0 20px;font:18px/1.65 system-ui,sans-serif;color:#172b3a}
table{display:block;overflow-x:auto;max-width:100%;border-collapse:collapse;font-size:16px}td,th{border:1px solid #b8cbd5;padding:10px;vertical-align:top;min-width:140px}
a{color:#036b9a}aside{background:#edf6fa;padding:16px;border-radius:8px}h1{line-height:1.2}li{margin:8px 0}
@media print{body{font-size:11pt;margin:0;max-width:none}a{color:inherit}table{display:table;font-size:9pt;width:100%}td,th{min-width:0}tr{break-inside:avoid}}
'''


def prepare(repo, item, source, target, demand):
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    slug = date + '-' + item['id']
    folder = '/downloads/questions/' + item['id']
    dest = repo / 'public' / folder.lstrip('/')
    dest.mkdir(parents=True, exist_ok=True)
    translated = render(source['tree'], target)
    english = render(source['tree'], source['segments'])
    attribution = (f'<p>{html.escape(NOTICE)} <a href="{item["url"]}" target="_blank" rel="noopener">Оригинал</a>; '
                   f'<a href="{LICENSE}">условия использования</a>.</p>')
    scope = html.escape(item['scope'])
    lead = ('<aside><strong>Коротко по вопросу · редакционное пояснение</strong><p>'
            + html.escape(item['lead']) + '</p></aside>') if item.get('lead') else ''
    def document(body, lang, title):
        return (f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><meta name="viewport" '
                f'content="width=device-width"><title>{html.escape(title)}</title><style>{STYLE}</style>'
                f'<body><h1>{html.escape(title)}</h1><aside><p>{scope}</p>'
                f'<p>Источник: {item["original_title"]}. Дата страницы источника: {item["original_date"]}.</p>'
                f'<p>{html.escape(item["context"])}</p>'
                '<p>Русский перевод и сопоставление с оригиналом выполнены с помощью ИИ. '
                'Независимая профильная рецензия не проводилась.</p>'
                f'</aside>{lead if lang == "ru" else ""}{body}{attribution}</body></html>')
    (dest / 'translation.html').write_text(document(translated, 'ru', item['title']))
    (dest / 'original.html').write_text(document(english, 'en', item['original_title']))
    metadata = {
        'title': item['title'], 'description': item['description'], 'date': date,
        'category': 'методы', 'tags': item['tags'], 'source': item['url'],
        'translationId': item['id'],
        'translation': {'publisher': 'CDC', 'originalTitle': item['original_title'],
                        'authors': 'CDC / NCEZID', 'originalDate': item['original_date'],
                        'scope': item['scope'], 'license': 'Условия использования материалов CDC',
                        'licenseUrl': LICENSE, 'originalHtml': folder + '/original.html',
                        'offlineHtml': folder + '/translation.html'},
    }
    # JSON strings are valid YAML scalars; dates remain unquoted for z.date().
    front = '\n'.join(f'{k}: {v if k == "date" else json.dumps(v, ensure_ascii=False)}' for k, v in metadata.items())
    body = (f'---\n{front}\n---\n\n{lead}\n\n**Контекст источника.** {item["context"]}\n\n'
            f'{translated}\n\n{attribution}\n')
    article = repo / 'src/content/articles' / (slug + '.md')
    article.write_text(body)
    return slug, [article, dest / 'translation.html', dest / 'original.html']
