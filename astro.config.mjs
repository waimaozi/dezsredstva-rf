// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai',
  integrations: [sitemap({
    filter: (page) => {
      const path = new URL(page).pathname;
      return !(path.startsWith('/tags/') && path !== '/tags/')
        && !path.startsWith('/downloads/') && !/^\/404(?:\.html|\/)?$/.test(path);
    },
  })],
  vite: {
    plugins: [tailwindcss()],
  },
});
