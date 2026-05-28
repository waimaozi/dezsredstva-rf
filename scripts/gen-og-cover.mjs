import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import sharp from 'sharp';

const svg = `<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0c4a6e"/>
      <stop offset="1" stop-color="#0369a1"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="90" y="84" width="104" height="104" rx="26" fill="#ffffff"/>
  <text x="142" y="153" font-family="DejaVu Sans" font-weight="bold" font-size="46" fill="#0369a1" text-anchor="middle">ДС</text>
  <text x="214" y="150" font-family="DejaVu Sans" font-weight="bold" font-size="29" fill="#e0f2fe">дезинфицирующиесредства.рф</text>
  <text x="90" y="332" font-family="DejaVu Sans" font-weight="bold" font-size="72" fill="#ffffff">Научные дайджесты</text>
  <text x="90" y="414" font-family="DejaVu Sans" font-weight="bold" font-size="72" fill="#ffffff">о дезинфекции</text>
  <text x="92" y="478" font-family="DejaVu Sans" font-size="29" fill="#bae6fd">Переводы PubMed · обзоры практик · калькулятор разведения</text>
  <rect x="90" y="548" width="1020" height="2" fill="#38bdf8" opacity="0.5"/>
  <text x="90" y="590" font-family="DejaVu Sans" font-size="23" fill="#7dd3fc">Независимый просветительский проект</text>
  <text x="1110" y="590" font-family="DejaVu Sans" font-size="23" fill="#bae6fd" text-anchor="end">При поддержке chemitech.ru</text>
</svg>
`;

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'gen-og-cover-'));
const svgPath = path.join(tempDir, 'og-cover.svg');
const pngPath = path.join(tempDir, 'og-cover.png');
const outputPath = path.resolve(process.cwd(), 'public/og-cover.jpg');

try {
  fs.writeFileSync(svgPath, svg, 'utf8');

  try {
    execFileSync('/usr/bin/rsvg-convert', ['-w', '1200', '-h', '630', svgPath, '-o', pngPath], {
      stdio: 'pipe',
    });
  } catch (error) {
    const details = error instanceof Error ? error.message : String(error);
    console.error(`Failed to render SVG with rsvg-convert: ${details}`);
    process.exit(1);
  }

  if (!fs.existsSync(pngPath)) {
    console.error(`Failed to render SVG with rsvg-convert: output PNG was not created at ${pngPath}`);
    process.exit(1);
  }

  await sharp(pngPath).jpeg({ quality: 88, mozjpeg: true }).toFile(outputPath);
  console.log(outputPath);
} finally {
  fs.rmSync(tempDir, { recursive: true, force: true });
}
