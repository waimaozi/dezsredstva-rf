import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import type { APIContext } from "astro";

export async function GET(context: APIContext) {
  const articles = await getCollection("articles");
  const sorted = articles.sort(
    (a, b) => new Date(b.data.date).getTime() - new Date(a.data.date).getTime()
  );

  const site = context.site?.toString() ?? "https://xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai";

  return rss({
    title: "Дезинфицирующиесредства.рф — блог о дезинфекции",
    description:
      "Переводы научных исследований, обзоры практик дезинфекции и полезные инструменты для специалистов.",
    site,
    items: sorted.map((article) => ({
      title: article.data.title,
      description: article.data.description,
      pubDate: new Date(article.data.date),
      link: `/articles/${article.id}/`,
    })),
    customData: `<language>ru-ru</language>`,
  });
}
