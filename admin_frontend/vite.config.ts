import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            const k = process.env.VITE_ADMIN_API_KEY
            if (k) {
              proxyReq.setHeader('X-Admin-API-Key', k)
            }
          })
        },
      },
      '/api': 'http://localhost:8000',
    },
  },
})
