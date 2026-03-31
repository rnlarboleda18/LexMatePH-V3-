import sharp from 'sharp';
import { writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// SVG matching the About page Scale icon exactly — dark rounded square + blue scale
function buildSVG(size) {
  const r = Math.round(size * 0.22); // corner radius
  const strokeW = Math.round(size * 0.045);
  const pad = size * 0.18;
  const w = size - pad * 2;
  const cx = size / 2;

  // Key measurements
  const postTop  = pad + w * 0.08;
  const postBottom = pad + w * 0.85;
  const baseHalfW = w * 0.28;
  const beamY = postTop + w * 0.05;
  const beamHalfW = w * 0.36;
  const leftPivotX = cx - beamHalfW;
  const rightPivotX = cx + beamHalfW;
  const panCenterY = beamY + w * 0.26;
  const panRadius = w * 0.15;
  const chainHalfW = w * 0.12;

  // Left pan triangle points
  const llx = leftPivotX - chainHalfW;
  const lrx = leftPivotX + chainHalfW;

  // Right pan triangle points
  const rlx = rightPivotX - chainHalfW;
  const rrx = rightPivotX + chainHalfW;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <!-- Dark rounded background -->
  <rect width="${size}" height="${size}" rx="${r}" ry="${r}" fill="#131c2e"/>
  
  <!-- Scale icon (Lucide Scale style) -->
  <g stroke="#60a5fa" stroke-width="${strokeW}" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <!-- Vertical post -->
    <line x1="${cx}" y1="${postTop}" x2="${cx}" y2="${postBottom}"/>
    <!-- Base line -->
    <line x1="${cx - baseHalfW}" y1="${postBottom}" x2="${cx + baseHalfW}" y2="${postBottom}"/>
    <!-- Crossbeam -->
    <line x1="${leftPivotX}" y1="${beamY}" x2="${rightPivotX}" y2="${beamY}"/>
    <!-- Left chain + pan -->
    <polyline points="${leftPivotX},${beamY} ${llx},${panCenterY} ${lrx},${panCenterY}"/>
    <path d="M ${llx} ${panCenterY} A ${panRadius} ${panRadius} 0 0 0 ${lrx} ${panCenterY}"/>
    <!-- Right chain + pan -->
    <polyline points="${rightPivotX},${beamY} ${rlx},${panCenterY} ${rrx},${panCenterY}"/>
    <path d="M ${rlx} ${panCenterY} A ${panRadius} ${panRadius} 0 0 0 ${rrx} ${panCenterY}"/>
  </g>
</svg>`;
}

const publicDir = resolve(__dirname, 'public');

async function generate(size, filename) {
  const svg = Buffer.from(buildSVG(size));
  await sharp(svg)
    .png()
    .toFile(resolve(publicDir, filename));
  console.log(`✓ Generated ${filename} (${size}x${size})`);
}

// Also save an SVG version for the favicon
writeFileSync(resolve(publicDir, 'favicon.svg'), buildSVG(64));
console.log('✓ Generated favicon.svg');

await generate(512, 'pwa-512x512.png');
await generate(192, 'pwa-192x192.png');
await generate(192, 'apple-touch-icon.png');
await generate(32,  'favicon.png');

console.log('\nAll icons generated successfully!');
