// Run after the preview build. Uses parse5 already present in Astro's dependency tree.
import { readFile, writeFile } from 'node:fs/promises';
import { parse, serialize, serializeOuter } from 'parse5';

const issue = '2026-10';
const slugs = ['zagryaznennyj-sterilnyj-gel', 'voda-i-inzhektor-kt', 'bioplenki-myasopererabotka-fsa']
  .map((slug) => `2026-10-13-${slug}`);
const attr = (node, key) => node.attrs?.find((a) => a.name === key)?.value;
const find = (node, predicate) => {
  if (predicate(node)) return node;
  for (const child of node.childNodes || []) {
    const match = find(child, predicate);
    if (match) return match;
  }
};
const hasClass = (node, name) => attr(node, 'class')?.split(' ').includes(name);
const text = (node) => node.nodeName === '#text' ? node.value : (node.childNodes || []).map(text).join('');
const escape = (value) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
async function localize(node) {
  for (const child of node.childNodes || []) await localize(child);
  for (const a of node.attrs || []) {
    if (a.name === 'src' && a.value.startsWith('/images/')) {
      const data = await readFile(`public${a.value}`);
      a.value = `data:image/jpeg;base64,${data.toString('base64')}`;
      const loading = node.attrs.find((value) => value.name === 'loading');
      if (loading) loading.value = 'eager';
    }
    if (a.name === 'href' && a.value.startsWith(`/downloads/${issue}/`) && a.value.endsWith('-original.pdf')) {
      const filename = a.value.split('/').at(-1);
      const data = await readFile(`public${a.value}`);
      node.attrs.push({ name: 'download', value: filename });
      node.attrs.push({ name: 'data-original-url', value: `https://дезинфицирующиесредства.рф${a.value}` });
      a.value = `data:application/pdf;base64,${data.toString('base64')}`;
    }
    if (a.name === 'href' && a.value.startsWith('/')) a.value = `https://дезинфицирующиесредства.рф${a.value}`;
  }
}
const articles = [];
for (const slug of slugs) {
  const doc = parse(await readFile(`dist/articles/${slug}/index.html`, 'utf8'));
  const title = text(find(doc, (n) => n.tagName === 'h1'));
  const source = find(doc, (n) => hasClass(n, 'translation-source'));
  const actions = find(source, (n) => hasClass(n, 'reading-actions'));
  source.childNodes = source.childNodes.filter((n) => n !== actions);
  const details = find(source, (n) => n.tagName === 'details');
  details.attrs.push({ name: 'open', value: '' });
  const body = find(doc, (n) => hasClass(n, 'prose-article'));
  await localize(body);
  articles.push({ slug, title, content: serializeOuter(source) + serialize(body) });
}
const css = await readFile('scripts/translation-packet.css', 'utf8');
const html = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow"><title>Зарубежная практика по-русски — выпуск 01</title><style>${css}</style></head><body>
<main><header id="contents"><p class="eyebrow">Дезинфицирующиесредства.рф · Выпуск 01 · 13 октября 2026</p><h1>Зарубежная практика<br>по-русски</h1><p class="lead">Три перевода о загрязнении, очистке оборудования и биоплёнках.</p><p>Тексты, рисунок и PDF первоисточников встроены в этот файл. Переводы можно читать без интернета. Для сохранения оригинала нажмите ссылку «локальная копия PDF» в конце соответствующего материала.</p><ol>${articles.map((a) => `<li><a href="#${a.slug}">${escape(a.title)}</a></li>`).join('')}</ol><p class="note">Объём перевода указан у каждого материала. Редакционные пояснения выделены отдельно. Перевод подготовлен и сопоставлен с оригиналами с помощью ИИ; независимая профильная рецензия не проводилась.</p></header>
${articles.map((a, i) => `<article id="${a.slug}"><p class="eyebrow">Материал 0${i + 1}</p><h1>${escape(a.title)}</h1>${a.content}<p class="back"><a href="#contents">↑ К содержанию</a></p></article>`).join('\n')}
<footer><p>При поддержке <a href="https://chemitech.ru">chemitech.ru</a>.</p><p>Оригиналы: Emerging Infectious Diseases / CDC (общественное достояние) и FSA Research and Evidence (CC BY 4.0). Переводы не одобрены авторами или издателями. Подробная атрибуция — у каждого материала.</p></footer></main></body></html>`;
await writeFile(`public/downloads/${issue}/vypusk.html`, html);
console.log(`Exported ${articles.length} articles; ${(Buffer.byteLength(html) / 1024 / 1024).toFixed(1)} MiB, including original PDFs.`);
