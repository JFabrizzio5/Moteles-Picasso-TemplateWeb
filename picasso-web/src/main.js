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

// La app se instala como PWA. En desarrollo no: un service worker en
// localhost sirve versiones viejas y confunde al probar.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
