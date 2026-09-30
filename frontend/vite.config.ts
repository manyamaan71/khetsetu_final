import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'KhetSetu - Smart Farming Assistant',
        short_name: 'KhetSetu',
        description: 'Smart Crop Health & Market Assistant for Farmers',
        theme_color: '#16a34a',
        background_color: '#f0fdf4',
        display: 'standalone',
        start_url: '/',
        lang: 'en',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
        ]
      },
      workbox: {
        // App shell, JS/CSS, translations and the bundled crop/disease info are precached => the UI opens offline.
        globPatterns: ['**/*.{js,css,html,svg,png,ico,json}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        // Deliberately NO runtime caching of /api/market-prices or /api/predict:
        // stale prices must never be shown as live, and cloud predictions cannot work offline.
        // (The last scan result and history are kept in localStorage by the app itself.)
      }
    })
  ],
  server: {
    fs: { allow: ['..'] },            // lets the app import ../data/crops.json (shared with the backend)
    proxy: {
      // 127.0.0.1 instead of "localhost": on Windows, localhost can resolve to IPv6 (::1) and miss uvicorn.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})
