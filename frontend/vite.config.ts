import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true,
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
      '/gitlab': 'http://127.0.0.1:8001',
      '/redmine': 'http://127.0.0.1:8002',
      '/analytics': {
        target: 'https://tpu-metrics.duckdns.org',
        changeOrigin: true,
      },
    },
  },
})