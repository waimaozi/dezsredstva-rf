// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://xn--80adfaeaaojaaa6d2bcpdslq7b4d3f.xn--p1ai',
  integrations: [sitemap()],
});
