import { getCollection } from "astro:content";
import type { APIRoute } from "astro";

export const GET: APIRoute = async () => {
  const articles = await getCollection("articles");
  const site = "https://дезинфицирующиесредства.рф";
  
  const pages = [
    { loc: "/", priority: "1.0", changefreq: "weekly" },
    { loc: "/about/", priority: "0.8", changefreq: "monthly" },
    { loc: "/articles/", priority: "0.9", changefreq: "daily" },
    { loc: "/guides/", priority: "0.8", changefreq: "weekly" },
    { loc: "/tags/", priority: "0.7", changefreq: "weekly" },
    { loc: "/tools/", priority: "0.7", changefreq: "monthly" },
    ...articles.map((article) => ({
      loc: `/articles/${article.id}/`,
      priority: "0.8",
      changefreq: "monthly" as const,
      lastmod: article.data.date.toISOString().split("T")[0]
    }))
  ];

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${pages.map((page) => `  <url>
    <loc>${site}${page.loc}</loc>
    ${page.lastmod ? `<lastmod>${page.lastmod}</lastmod>` : ""}
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`).join("\n")}
</urlset>`;

  return new Response(sitemap, {
    status: 200,
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "max-age=3600, s-maxage=86400"
    }
  });
};
