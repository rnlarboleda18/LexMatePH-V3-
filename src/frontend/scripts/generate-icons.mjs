/**
 * Build PWA + favicon PNGs from vector art matching LandingPage / Layout:
 * purple→violet gradient squircle + white Scale icon (Lucide-style).
 * Run: cd src/frontend && node scripts/generate-icons.mjs
 */
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.join(__dirname, '..');
const publicDir = path.join(frontendRoot, 'public');

/** Tailwind purple-600 → violet-600, bg-gradient-to-br (matches header mark). */
function buildSVG(size) {
  const r = Math.round((size * 12) / 40);
  const strokeW = Math.max(2, Math.round((size * 2) / 40));
  const pad = size * 0.18;
  const w = size - pad * 2;
  const cx = size / 2;

  const postTop = pad + w * 0.08;
  const postBottom = pad + w * 0.85;
  const baseHalfW = w * 0.28;
  const beamY = postTop + w * 0.05;
  const beamHalfW = w * 0.36;
  const leftPivotX = cx - beamHalfW;
  const rightPivotX = cx + beamHalfW;
  const panCenterY = beamY + w * 0.26;
  const panRadius = w * 0.15;
  const chainHalfW = w * 0.12;

  const llx = leftPivotX - chainHalfW;
  const lrx = leftPivotX + chainHalfW;
  const rlx = rightPivotX - chainHalfW;
  const rrx = rightPivotX + chainHalfW;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <defs>
    <linearGradient id="lexGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#9333ea"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
  </defs>
  <rect width="${size}" height="${size}" rx="${r}" ry="${r}" fill="url(#lexGrad)"/>
  <g stroke="#ffffff" stroke-width="${strokeW}" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <line x1="${cx}" y1="${postTop}" x2="${cx}" y2="${postBottom}"/>
    <line x1="${cx - baseHalfW}" y1="${postBottom}" x2="${cx + baseHalfW}" y2="${postBottom}"/>
    <line x1="${leftPivotX}" y1="${beamY}" x2="${rightPivotX}" y2="${beamY}"/>
    <polyline points="${leftPivotX},${beamY} ${llx},${panCenterY} ${lrx},${panCenterY}"/>
    <path d="M ${llx} ${panCenterY} A ${panRadius} ${panRadius} 0 0 0 ${lrx} ${panCenterY}"/>
    <polyline points="${rightPivotX},${beamY} ${rlx},${panCenterY} ${rrx},${panCenterY}"/>
    <path d="M ${rlx} ${panCenterY} A ${panRadius} ${panRadius} 0 0 0 ${rrx} ${panCenterY}"/>
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
