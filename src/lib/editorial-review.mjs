// Individual editorial decisions after checking the cited references.
// Keep the original URLs accessible; do not promote untraceable summaries as research.
export const editorialReviews = {
  'khlornye-vs-beskhlornye-dezinfektanty-chto-govorit-nauka': {
    reason: 'В этой архивной заметке не указаны конкретные исследования: ссылка ведёт на главную страницу PubMed. Проверить изложенные выводы по первоисточникам пока нельзя.',
  },
  'ustoychivost-patogenov-na-bolnichnykh-poverkhnostyakh-obzor-2025': {
    reason: 'В этой архивной заметке не указаны конкретные исследования: ссылка ведёт на главную страницу PubMed. Проверить изложенные выводы по первоисточникам пока нельзя.',
  },
  'vliyanie-organicheskoy-nagruzki-na-effektivnost-dezinfitsiruyushchikh-sredstv': {
    reason: 'В этой архивной заметке не указаны конкретные исследования: ссылка ведёт на главную страницу PubMed. Проверить изложенные выводы по первоисточникам пока нельзя.',
  },
};

export function getEditorialReview(id) {
  return editorialReviews[id];
}

export function isIndexableArticle(article) {
  return !getEditorialReview(article.id);
}

export function isReviewPath(pathname) {
  const match = decodeURI(pathname).match(/^\/articles\/([^/]+)\/?$/);
  return Boolean(match && getEditorialReview(match[1]));
}
