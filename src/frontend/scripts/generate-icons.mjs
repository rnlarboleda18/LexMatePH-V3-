/**
 * Rasterize src/frontend/logo/*.png into public/ favicon + PWA sizes.
 * Run from repo: cd src/frontend && node scripts/generate-icons.mjs
 */
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.join(__dirname, '..');
const logoDir = path.join(frontendRoot, 'logo');
const publicDir = path.join(frontendRoot, 'public');

const SOURCE_NAME = 'Screenshot 2026-04-02 074345.png';
const srcPath = path.join(logoDir, SOURCE_NAME);

if (!fs.existsSync(srcPath)) {
  console.error(`Missing source: ${srcPath}`);
  process.exit(1);
}

const outputs = [
  ['favicon.png', 32],
  ['favicon-16.png', 16],
  ['apple-touch-icon.png', 180],
  ['pwa-192x192.png', 192],
  ['pwa-512x512.png', 512],
];

async function main() {
  for (const [filename, size] of outputs) {
    await sharp(srcPath)
      .resize(size, size, { fit: 'cover', position: 'centre' })
      .png()
      .toFile(path.join(publicDir, filename));
    console.log(`Wrote ${filename} (${size}x${size})`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
