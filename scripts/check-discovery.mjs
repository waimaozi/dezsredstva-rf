import { readdir, readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import path from 'node:path';
import { editorialReviews, isReviewPath } from '../src/lib/editorial-review.mjs';
async function files(dir) {
  return (await Promise.all((await readdir(dir,{withFileTypes:true})).map(e=>e.isDirectory()?files(path.join(dir,e.name)):path.join(dir,e.name)))).flat();
}
const all = await files('dist');
const noindex = new Set(); const articlePaths = new Set(); let tagPages=0; let translations=0;
for (const file of all.filter(f=>f.endsWith('/index.html'))) {
  const html=await readFile(file,'utf8');
  const canonical=html.match(/<link\s+rel="canonical"\s+href="([^"]+)"/);
  assert(canonical, `Missing canonical: ${file}`);
  const url=new URL(canonical[1]); const pathname=decodeURI(url.pathname);
  if (/<meta\s+name="robots"\s+content="[^"]*noindex/.test(html)) noindex.add(pathname);
  if (pathname.startsWith('/articles/') && pathname!='/articles/') articlePaths.add(pathname);
  if (pathname.startsWith('/tags/') && pathname!='/tags/') {
    tagPages++; assert(!/Публикаций по теме:\s*0\./.test(html), `Empty tag page: ${pathname}`);
  }
  for (const m of html.matchAll(/<script\s+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)) {
    const value=JSON.parse(m[1]);
    for(const schema of Array.isArray(value)?value:[value]) {
      if(schema.translationOfWork) {
        translations++;
        assert(schema.translator?.name, `Missing translator: ${pathname}`);
        assert(schema.translationOfWork.url, `Missing original: ${pathname}`);
        assert(!/<strong>Авторы:<\/strong>\s*\./.test(html), `Empty visible attribution: ${pathname}`);
        for (const author of schema.translationOfWork.author??[]) assert(html.includes(author.name), `Author not visible: ${pathname}`);
      }
    }
  }
}
const sitemapPaths=new Set();
for(const file of all.filter(f=>/\/sitemap-\d+\.xml$/.test(f))) {
  const xml=await readFile(file,'utf8');
  for(const m of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) sitemapPaths.add(decodeURI(new URL(m[1]).pathname));
}
assert(sitemapPaths.has('/perevody/'),'Translations hub missing from sitemap');
for(const p of noindex) assert(!sitemapPaths.has(p), `Noindex URL in sitemap: ${p}`);
for(const p of articlePaths) {
  assert.equal(sitemapPaths.has(p), !isReviewPath(p), `Unexpected sitemap eligibility: ${p}`);
  assert.equal(noindex.has(p), isReviewPath(p), `Unexpected article robots directive: ${p}`);
}
for(const id of Object.keys(editorialReviews)) {
  const p=`/articles/${id}/`;
  assert(articlePaths.has(p), `Reviewed URL no longer accessible: ${p}`);
  const html=await readFile(`dist${p}index.html`,'utf8');
  assert(html.includes('источники требуют уточнения'), `Missing visible review note: ${p}`);
  for(const feed of ['sitemap.xml','rss.xml','turbo.xml']) {
    assert(!(await readFile(`dist/${feed}`,'utf8')).includes(id), `Reviewed article in ${feed}: ${id}`);
  }
}
console.log(JSON.stringify({articlePages:articlePaths.size,reviewPages:Object.keys(editorialReviews).length,tagPages,translations,sitemapUrls:sitemapPaths.size,noindexUrlsInSitemap:0,emptyTagPages:0}));
