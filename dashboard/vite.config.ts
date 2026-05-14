import { defineConfig } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

export default defineConfig({
  plugins: [
    figmaAssetResolver(),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/papers': 'http://127.0.0.1:8000',
      '/pipeline-runs': 'http://127.0.0.1:8000',
      '/ingest': 'http://127.0.0.1:8000',
      '/reports': 'http://127.0.0.1:8000',
      '/search': 'http://127.0.0.1:8000',
    },
  },
  assetsInclude: ['**/*.svg', '**/*.csv'],
})