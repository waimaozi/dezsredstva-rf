import test from 'node:test';
import assert from 'node:assert/strict';
import { getArticlesByTag, getRelatedArticles } from '../src/lib/articles.ts';
import { getArticleSchema } from '../src/lib/article-schema.ts';
import type { ArticleEntry } from '../src/lib/articles.ts';
const entry = (id: string, tags: string[], translation?: object): ArticleEntry => ({
  id, data: { title: id, description: id, date: new Date('2026-10-17'), tags,
    source: 'https://example.org/research', ...(translation ? { translation } : {}) }
} as ArticleEntry);

test('multiword and mixed-case tags link to populated collections', () => {
  const a = entry('a', [' Пищевая   безопасность ']);
  assert.deepEqual(getArticlesByTag([a], 'пищевая-безопасность').map(x => x.id), ['a']);
  assert.deepEqual(getArticlesByTag([a], 'другая-тема'), []);
});
test('translation recommendations use subject tags and retain translation scope', () => {
  const current = entry('current', ['перевод', 'Listeria'], {});
  const unrelated = entry('unrelated', ['перевод'], {});
  const relevant = entry('relevant', ['listeria'], {});
  const digest = entry('digest', ['Listeria']);
  assert.deepEqual(getRelatedArticles(current, [current, unrelated, digest, relevant], 2).map(x=>x.id), ['relevant','unrelated']);
});
test('research authors, source date and translator are distinct', () => {
  const originalAuthors = [{type:'Person',name:'Researcher A'},{type:'Organization',name:'Institute B'}];
  const a = entry('translation', [], { originalAuthors, originalTitle:'Source paper', originalPublished:'2020-09', originalType:'ScholarlyArticle', doi:'10.1234/example', licenseUrl:'https://creativecommons.org/licenses/by/4.0/' });
  const schema = getArticleSchema(a, 'https://example.org/translation/');
  assert(Array.isArray(schema.author));
  assert.deepEqual(schema.author.map(x=>x.name), ['Researcher A','Institute B']);
  assert.equal(schema.translator?.name, 'Дезинфицирующиесредства.рф');
  assert.equal(schema.translationOfWork?.datePublished, '2020-09');
  assert.equal(schema.datePublished, '2026-10-17T00:00:00.000Z');
  assert.equal(schema.translationOfWork?.identifier?.value, '10.1234/example');
  assert.equal(schema.citation, 'https://doi.org/10.1234/example');
});
test('missing source authors do not turn the publisher into the researcher', () => {
  const schema = getArticleSchema(entry('translation', [], {originalTitle:'Source'}), 'https://example.org/a/');
  assert.equal(schema.author, undefined);
  assert.equal(schema.translator?.['@type'], 'Organization');
});
