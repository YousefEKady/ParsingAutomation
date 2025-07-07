import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/upload': 'http://localhost:8080',
      '/search': 'http://localhost:8080',
      '/worker-status': 'http://localhost:8080',
    },
  },
})
