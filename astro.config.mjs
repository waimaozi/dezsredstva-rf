// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';
import { isReviewPath } from './src/lib/editorial-review.mjs';

// https://astro.build/config
export default defineConfig({
  site: 'https://xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai',
  integrations: [sitemap({
    filter: (page) => {
      const path = new URL(page).pathname;
      return !(path.startsWith('/tags/') && path !== '/tags/')
        && !isReviewPath(path)
        && !path.startsWith('/downloads/') && !/^\/404(?:\.html|\/)?$/.test(path);
    },
  })],
  vite: {
    plugins: [tailwindcss()],
  },
});
