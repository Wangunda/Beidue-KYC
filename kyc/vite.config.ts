import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // default Vite port
    proxy: {
      // Proxy API requests to Django dev server
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false, // ensures HTTP is used even if your frontend is on HTTPS
      },
    },
  },
})

