// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://xn--80adjkbqfcejjiieo4b.xn--p1ai',
  integrations: [sitemap()],
});
