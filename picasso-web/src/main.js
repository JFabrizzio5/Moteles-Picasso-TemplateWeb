import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from '@/App.vue'
import router from '@/router'
import { useAuthStore } from '@/stores/auth.store.js'
import '@/style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
useAuthStore().restore()
app.mount('#app')

// Precarga el código de todas las pantallas en cuanto la app queda quieta: así
// cambiar de módulo no espera a bajar su archivo (antes, la primera vez a Finanzas
// tardaba ~0.8 s solo en eso).
const precargar = () =>
  router.getRoutes().forEach((r) => {
    const c = r.components?.default
    if (typeof c === 'function') c().catch(() => {})
  })
if ('requestIdleCallback' in window) requestIdleCallback(precargar, { timeout: 2500 })
else setTimeout(precargar, 1200)

// La app se instala como PWA. En desarrollo no: un service worker en
// localhost sirve versiones viejas y confunde al probar.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
