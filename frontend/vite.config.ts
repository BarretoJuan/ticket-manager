import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Browser calls relative /api/... paths on the Vite origin; they are
      // forwarded to the backend. In Docker VITE_BACKEND_PROXY points at the
      // compose "backend" service; locally it defaults to localhost:8000.
      '/api': process.env.VITE_BACKEND_PROXY ?? 'http://localhost:8000',
    },
  },
})
