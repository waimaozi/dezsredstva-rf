// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig(async () => {
  const integrations = [];

  try {
    const { default: sitemap } = await import('@astrojs/sitemap');
    integrations.push(sitemap());
  } catch {
    console.warn('[astro.config] @astrojs/sitemap не установлен.');
  }

  return {
    site: 'https://дезинфицирующиесредства.рф',
    integrations,
  };
});
