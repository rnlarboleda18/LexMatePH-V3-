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
      sourcemap: false,
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks(id) {
            // Clerk — large 3rd-party auth lib, changes independently of app code
            if (id.includes('@clerk')) return 'vendor-clerk';
            // React core — stable, long-lived cache
            if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) return 'vendor-react';
            // React Router
            if (id.includes('react-router')) return 'vendor-router';
            // Lucide icons — large tree; split so unused routes don’t pull it all in
            if (id.includes('lucide-react')) return 'vendor-lucide';
            // Fuse.js fuzzy search
            if (id.includes('fuse.js') || id.includes('fuse/')) return 'vendor-fuse';
          },
        },
      },
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
          // Same-origin relative id/scope/start_url — survives apex vs www as long as the page and manifest share one origin.
          id: '/',
          name: 'LexMatePH',
          short_name: 'LexMatePH',
          description: 'Your Law Companion — Philippine bar review, SC decisions, case digests, and codals.',
          theme_color: '#0f172a',
          background_color: '#0f172a',
          display: 'standalone',
          // Helps Android tablets (mobile + landscape) pass installability; portrait-only blocked some Chrome paths.
          orientation: 'any',
          prefer_related_applications: false,
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
          navigateFallbackDenylist: [/^\/api/, /^\/robots\.txt$/, /^\/sitemap\.xml$/],
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
            // Live RSS bundle: never serve a stale/empty cache on slow mobile (NetworkFirst timeout used to miss first load).
            {
              urlPattern: /\/api\/sc_judiciary_feed/i,
              handler: 'NetworkOnly',
            },
            {
              urlPattern: /^\/api\/.*/i,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                networkTimeoutSeconds: 30,
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
