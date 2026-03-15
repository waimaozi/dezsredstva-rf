/**
 * Post-build CSS fix: replace @theme default{ with :root{
 * Tailwind CSS v4 outputs @theme which browsers don't support yet.
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
    if (css.includes('@theme')) {
      css = css.replace(/@theme\s+default\s*\{/g, ':root{');
      await writeFile(path, css);
      console.log(`Fixed @theme in ${file}`);
    }
  }
} catch (e) {
  console.error('CSS fix error:', e.message);
}
