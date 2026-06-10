import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const hedgemateTarget = env.VITE_HEDGEMATE_API_URL || 'http://127.0.0.1:8766'

  return {
    plugins: [react()],
    build: {
      minify: true,
      cssMinify: true
    },
    server: {
      proxy: {
        '/api': {
          target: hedgemateTarget,
          changeOrigin: true,
        }
      }
    }
  }
})
