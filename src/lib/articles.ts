import type { CollectionEntry } from "astro:content";

export type ArticleEntry = CollectionEntry<"articles">;

export type NormalizedTag = {
  label: string;
  slug: string;
};

export type TagWithCount = NormalizedTag & {
  count: number;
};

const SITE_URL = "https://дезинфицирующиесредства.рф";

export function sortArticlesByDate(articles: ArticleEntry[]) {
  return [...articles].sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}

export function slugifyTag(tag: string) {
  return tag.trim().toLowerCase().replace(/\s+/g, "-");
}

export function unslugifyTag(slug: string) {
  return slug.trim().toLowerCase();
}

export function normalizeTag(tag: string): NormalizedTag {
  const label = tag.trim();

  return {
    label,
    slug: slugifyTag(label)
  };
}

export function getUniqueTags(articles: ArticleEntry[]): TagWithCount[] {
  const tags = new Map<string, TagWithCount>();

  for (const article of articles) {
    for (const tag of article.data.tags) {
      const normalized = normalizeTag(tag);
      const key = normalized.label.toLowerCase();
      const existing = tags.get(key);

      if (existing) {
        existing.count += 1;
        continue;
      }

      tags.set(key, { ...normalized, count: 1 });
    }
  }

  return [...tags.values()].sort((a, b) => {
    if (b.count !== a.count) {
      return b.count - a.count;
    }

    return a.label.localeCompare(b.label, "ru");
  });
}

export function getArticlesByTag(articles: ArticleEntry[], tagSlug: string) {
  const normalizedSlug = unslugifyTag(tagSlug);

  return sortArticlesByDate(
    articles.filter((article) =>
      article.data.tags.some((tag) => tag.trim().toLowerCase() === normalizedSlug)
    )
  );
}

export function getRelatedArticles(article: ArticleEntry, articles: ArticleEntry[], limit = 3) {
  const currentTags = new Set(article.data.tags.map((tag) => tag.trim().toLowerCase()));
  const candidates = articles.filter((entry) => entry.id !== article.id);

  const ranked = candidates
    .map((entry) => {
      const overlap = entry.data.tags.reduce((count, tag) => {
        return count + (currentTags.has(tag.trim().toLowerCase()) ? 1 : 0);
      }, 0);

      return { entry, overlap };
    })
    .sort((a, b) => {
      if (b.overlap !== a.overlap) {
        return b.overlap - a.overlap;
      }

      return b.entry.data.date.getTime() - a.entry.data.date.getTime();
    });

  const withOverlap = ranked.filter((item) => item.overlap > 0).slice(0, limit);
  if (withOverlap.length === limit) {
    return withOverlap.map((item) => item.entry);
  }

  const fallbackIds = new Set(withOverlap.map((item) => item.entry.id));
  const latest = sortArticlesByDate(candidates)
    .filter((entry) => !fallbackIds.has(entry.id))
    .slice(0, limit - withOverlap.length);

  return [...withOverlap.map((item) => item.entry), ...latest].slice(0, limit);
}

export function getArticleUrl(article: ArticleEntry) {
  return `/articles/${article.id}/`;
}

export function getArticleAbsoluteUrl(article: ArticleEntry) {
  return new URL(getArticleUrl(article), SITE_URL).toString();
}
