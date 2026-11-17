import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// Para probar en un teléfono por un túnel HTTPS, la app compilada y la API
// salen por un solo origen: `npm run movil` sirve el build en :9811 y manda
// /api y /storage a la API (:9800). Así no hay CORS ni una segunda dirección
// que el teléfono tenga que alcanzar. En desarrollo normal (:9810) el front
// sigue hablando directo con :9800, como lo genera jfast.
const API = 'http://127.0.0.1:9800'
const unOrigen = {
  '/api': { target: API, changeOrigin: true, rewrite: (ruta) => ruta.replace(/^\/api/, '') },
  '/storage': { target: API, changeOrigin: true },
}

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 9810,
  },
  preview: {
    port: 9811,
    strictPort: true,
    proxy: unOrigen,
    // Las direcciones de prueba del túnel cambian cada vez.
    allowedHosts: ['.trycloudflare.com', 'localhost'],
  },
})
