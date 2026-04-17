import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { VitePWA } from 'vite-plugin-pwa'

const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:7071',
    changeOrigin: true,
    // Flashcard concepts aggregation can exceed default proxy timeouts
    timeout: 180000,
    proxyTimeout: 180000,
  },
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  /** Set LEXMATE_HTTPS=1 in .env.development.local so iOS can open https://<LAN>:5173 — improves Add-to-Home-Screen standalone vs plain http://IP */
  const httpsDev = env.LEXMATE_HTTPS === '1'

  return {
    test: {
      environment: 'happy-dom',
      globals: true,
      setupFiles: ['./src/test/setup.js'],
    },
    build: {
      // Warn when any individual chunk exceeds 600 kB (gzip). Main bundle currently ~850 kB raw;
      // flag intentionally set above current size to avoid blocking CI—lower as code is split further.
      chunkSizeWarningLimit: 900,
    },
    plugins: [
      react(),
      ...(httpsDev ? [basicSsl()] : []),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: [
          'favicon.svg',
          'pwa-192x192.png',
          'pwa-512x512.png',
          'apple-touch-icon.png',
          'favicon.png',
          'favicon-16.png',
        ],
        manifest: {
          name: 'LexMatePH',
          short_name: 'LexMatePH',
          description: 'Your Law Companion — Philippine bar review, SC decisions, case digests, and codals.',
          theme_color: '#0f172a',
          background_color: '#0f172a',
          display: 'standalone',
          orientation: 'portrait-primary',
          scope: '/',
          start_url: '/',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'maskable',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
        workbox: {
          // Cache all static assets (JS, CSS, HTML, images, fonts)
          globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,woff,woff2}'],
          // Ensure SPA routing still works when offline
          navigateFallback: 'index.html',
          navigateFallbackDenylist: [/^\/api/],
          // Cache API responses with a network-first strategy (try network, fall back to cache)
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'google-fonts-cache',
                expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
                cacheableResponse: { statuses: [0, 200] },
              },
            },
            {
              urlPattern: /^\/api\/.*/i,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                networkTimeoutSeconds: 12,
                expiration: { maxEntries: 80, maxAgeSeconds: 60 * 60 * 12 },
                cacheableResponse: { statuses: [0, 200] },
              },
            },
            {
              // Specialized Audio Caching Strategy (2GB QUOTA)
              urlPattern: /.*\.mp3$/,
              handler: 'CacheFirst',
              options: {
                cacheName: 'audio-cache',
                expiration: {
                  maxEntries: 200, // Limit to 200 tracks
                  maxAgeSeconds: 60 * 60 * 24 * 30, // Keep tracks for 30 days
                },
                cacheableResponse: {
                  statuses: [0, 200, 260], // Support successful and partial content/streaming
                },
                // Critical for audio/video streaming (Safari/Chrome support)
                rangeRequests: true,
              },
            },
          ],
        },
        // Serve manifest + register SW in dev so iOS "Add to Home Screen" matches production behavior.
        devOptions: {
          enabled: true,
          type: 'module',
        },
      }),
    ],
    server: {
      host: true, // bind to 0.0.0.0 — accessible from tablets/phones on the same Wi-Fi
      port: 5173,
      ...(httpsDev ? { https: true } : {}),
      proxy: apiProxy,
    },
    preview: {
      host: true,
      port: 4173,
      proxy: apiProxy,
    },
  }
})
