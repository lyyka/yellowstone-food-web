import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

function shareTags(origin: string) {
  const base = origin.replace(/\/$/, '')
  return {
    '%OG_URL%': base || '/',
    '%OG_IMAGE%': base ? `${base}/og.jpg` : '/og.jpg',
  }
}

export default defineConfig(({ mode }) => {
  const env = {
    ...loadEnv(mode, '..', ''),
    ...loadEnv(mode, process.cwd(), ''),
  }
  const origin = env.VITE_PUBLIC_ORIGIN || process.env.VITE_PUBLIC_ORIGIN || ''
  const tags = shareTags(origin)

  return {
    plugins: [
      react(),
      {
        name: 'share-meta',
        transformIndexHtml(html) {
          return Object.entries(tags).reduce(
            (out, [token, value]) => out.replaceAll(token, value),
            html,
          )
        },
      },
    ],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
