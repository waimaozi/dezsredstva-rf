/**
 * Post-build CSS fix for Tailwind CSS v4.
 * 1. Replace @theme default{ with :root{
 * 2. Replace @theme default inline reference{ with :root{
 * 3. Replace --theme(--var, fallback) with var(--var, fallback)
 * 4. Remove unprocessed @apply directives (replace with empty)
 */
import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const dir = join(import.meta.dirname, '..', 'dist', '_astro');

try {
  const files = await readdir(dir);
  for (const file of files) {
    if (!file.endsWith('.css')) continue;
    const path = join(dir, file);
    let css = await readFile(path, 'utf-8');
    let changed = false;

    // 1. Replace all @theme variants with :root
    if (css.includes('@theme')) {
      css = css.replace(/@theme\s+default\s+inline\s+reference\s*\{/g, ':root{');
      css = css.replace(/@theme\s+default\s*\{/g, ':root{');
      css = css.replace(/@theme\s*\{/g, ':root{');
      changed = true;
    }

    // 2. Replace --theme() function calls with var()
    // --theme(--var, fallback) → var(--var, fallback)
    // --theme(--var--sub, fallback) → var(--var--sub, fallback)
    if (css.includes('--theme(')) {
      css = css.replace(/--theme\(/g, 'var(');
      changed = true;
    }

    // 3. Remove @apply directives that weren't processed
    if (css.includes('@apply')) {
      // Replace whole declarations containing @apply with nothing
      // These are custom utility classes that should have been compiled
      css = css.replace(/@apply\s+[^;]+;/g, '/* @apply removed */');
      changed = true;
    }

    if (changed) {
      await writeFile(path, css);
      console.log(`Fixed CSS in ${file} (${css.length} bytes)`);
    }
  }
} catch (e) {
  console.error('CSS fix error:', e.message);
}
