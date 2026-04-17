/**
 * Build PWA + favicon PNGs from vector art matching LandingPage / Layout:
 * purple→violet gradient squircle + Lucide Scale icon (same paths as `Scale` in the header).
 * Run: cd src/frontend && node scripts/generate-icons.mjs
 */
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.join(__dirname, '..');
const publicDir = path.join(frontendRoot, 'public');

/** Lucide `scale` v0.555 iconNode — must stay in sync with lucide-react `Scale` in the app shell. */
const LUCIDE_SCALE_PATHS = [
  'M12 3v18',
  'm19 8 3 8a5 5 0 0 1-6 0zV7',
  'M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1',
  'm5 8 3 8a5 5 0 0 1-6 0zV7',
  'M7 21h10',
];

/** Tailwind purple-600 → violet-600, `rounded-xl` on a 40px mark → rx = 12/40 of size. */
function buildSVG(size) {
  const r = Math.round((size * 12) / 40);
  const s = size / 48;
  const paths = LUCIDE_SCALE_PATHS.map(
    (d) => `<path d="${d}"/>`
  ).join('\n    ');

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <defs>
    <linearGradient id="lexGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#9333ea"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
  </defs>
  <rect width="${size}" height="${size}" rx="${r}" ry="${r}" fill="url(#lexGrad)"/>
  <g fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
     transform="translate(${size / 2} ${size / 2}) scale(${s}) translate(-12 -12)">
    ${paths}
  </g>
</svg>`;
}

const outputs = [
  ['favicon.png', 32],
  ['favicon-16.png', 16],
  ['apple-touch-icon.png', 180],
  ['pwa-192x192.png', 192],
  ['pwa-512x512.png', 512],
];

async function main() {
  fs.mkdirSync(publicDir, { recursive: true });

  const faviconSvg = buildSVG(64);
  fs.writeFileSync(path.join(publicDir, 'favicon.svg'), faviconSvg, 'utf8');
  console.log('✓ Wrote favicon.svg');

  const masterSvg = buildSVG(512);
  fs.writeFileSync(path.join(publicDir, 'icon-master.svg'), masterSvg, 'utf8');
  console.log('✓ Wrote icon-master.svg');

  for (const [filename, size] of outputs) {
    const svg = Buffer.from(buildSVG(size));
    await sharp(svg).png().toFile(path.join(publicDir, filename));
    console.log(`✓ Wrote ${filename} (${size}×${size})`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
