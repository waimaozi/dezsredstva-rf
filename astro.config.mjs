// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig(async () => {
  const integrations = [];

  try {
    const { default: sitemap } = await import('@astrojs/sitemap');
    integrations.push(sitemap());
  } catch {
    console.warn('[astro.config] @astrojs/sitemap не установлен. Sitemap будет доступен после `npm install`.');
  }

  return {
    site: 'https://дезинфицирующиесредства.рф',
    integrations,
    vite: {
      plugins: [tailwindcss()]
    }
  };
});
