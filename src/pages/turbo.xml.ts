import { getCollection, render } from "astro:content";
import { experimental_AstroContainer as AstroContainer } from "astro/container";
import type { APIContext } from "astro";

const SITE_URL = "https://дезинфицирующиесредства.рф";
const ANALYTICS_ID = "107711899";

function sortByDateDesc<T extends { data: { date: Date } }>(entries: T[]) {
  return [...entries].sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}

function escapeXml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function buildTurboDocument({
  title,
  description,
  publishedAt,
  source,
  bodyHtml
}: {
  title: string;
  description: string;
  publishedAt: string;
  source?: string;
  bodyHtml: string;
}) {
  const sourceBlock = source
    ? `<p><a href="${escapeXml(source)}">Оригинальная публикация</a></p>`
    : "";

  return [
    "<header>",
    `<h1>${escapeXml(title)}</h1>`,
    `<p>${escapeXml(description)}</p>`,
    "</header>",
    `<p>Дата публикации: ${escapeXml(publishedAt)}</p>`,
    sourceBlock,
    bodyHtml
  ]
    .filter(Boolean)
    .join("");
}

export async function GET(_context: APIContext) {
  const articles = sortByDateDesc(await getCollection("articles"));
  const container = await AstroContainer.create();

  const items = await Promise.all(
    articles.map(async (article) => {
      const { Content } = await render(article);
      const bodyHtml = await container.renderToString(Content);
      const link = new URL(`/articles/${article.id}/`, SITE_URL).toString();

      const turboContent = buildTurboDocument({
        title: article.data.title,
        description: article.data.description,
        publishedAt: new Intl.DateTimeFormat("ru-RU", {
          day: "numeric",
          month: "long",
          year: "numeric"
        }).format(article.data.date),
        source: article.data.source,
        bodyHtml
      });

      return [
        '<item turbo="true">',
        `<title>${escapeXml(article.data.title)}</title>`,
        `<link>${escapeXml(link)}</link>`,
        `<pubDate>${article.data.date.toUTCString()}</pubDate>`,
        `<turbo:content><![CDATA[${turboContent}]]></turbo:content>`,
        "</item>"
      ].join("");
    })
  );

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss xmlns:yandex="http://news.yandex.ru/schemas/turbo/context.xsd" xmlns:media="http://search.yahoo.com/mrss/" xmlns:turbo="http://turbo.yandex.ru" version="2.0">',
    "<channel>",
    "<title>Дезинфицирующиесредства.рф</title>",
    `<link>${SITE_URL}</link>`,
    "<description>Турбо-лента со статьями о дезинфекции</description>",
    `<turbo:analytics type="Yandex" id="${ANALYTICS_ID}"/>`,
    ...items,
    "</channel>",
    "</rss>"
  ].join("");

  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8"
    }
  });
}
