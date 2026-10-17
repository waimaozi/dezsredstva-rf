import type { ArticleEntry } from "./articles";

const site = "https://дезинфицирующиесредства.рф/";
const publisher = {
  "@type": "Organization",
  "@id": new URL("about/#publisher", site).href,
  name: "Дезинфицирующиесредства.рф",
  url: new URL("about/", site).href
};

export function getArticleSchema(article: ArticleEntry, articleUrl: string) {
  const t = article.data.translation;
  const authors = t?.originalAuthors?.map(({ name, type }) => ({ "@type": type, name }));
  const original = t ? {
    "@type": t.originalType ?? "CreativeWork",
    "@id": article.data.source,
    name: t.originalTitle,
    url: article.data.source,
    inLanguage: "en",
    ...(authors?.length && { author: authors }),
    ...(t.originalPublished && { datePublished: t.originalPublished }),
    ...(t.doi && { identifier: { "@type": "PropertyValue", propertyID: "DOI", value: t.doi } }),
    license: t.licenseUrl
  } : undefined;

  return {
    "@context": "https://schema.org",
    "@type": "Article",
    "@id": `${articleUrl}#article`,
    url: articleUrl,
    headline: article.data.title,
    description: article.data.description,
    datePublished: article.data.date.toISOString(),
    dateModified: article.data.date.toISOString(),
    inLanguage: "ru",
    ...(t ? (authors?.length ? { author: authors } : {}) : { author: publisher }),
    publisher,
    mainEntityOfPage: { "@type": "WebPage", "@id": articleUrl },
    keywords: article.data.tags,
    ...(t && {
      translator: publisher,
      isBasedOn: article.data.source,
      translationOfWork: original,
      citation: t.doi ? `https://doi.org/${t.doi}` : article.data.source
    })
  };
}
