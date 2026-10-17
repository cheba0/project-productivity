import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true,
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/gitlab': 'http://127.0.0.1:8001',
      '/redmine': 'http://127.0.0.1:8002',
      '/analytics': 'http://127.0.0.1:8003',
    },
  },
})