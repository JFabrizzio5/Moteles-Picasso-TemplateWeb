<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { setTheme, useThemeValue } from '@/composables/useTemaPicasso.js'
import MaterialProyecto from '@/components/MaterialProyecto.vue'
import QrCelular from '@/components/QrCelular.vue'
import { DEMO } from '@/lib/demo.js'
import { HAY_MATERIAL } from '@/lib/proyecto.js'
import { ROLES } from '@/lib/formato.js'
import { useAuthStore } from '@/stores/auth.store.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const auth = useAuthStore()
const perfil = usePerfilStore()
const router = useRouter()
const tema = useThemeValue()

// Instalar como app: Chrome/Android avisa con beforeinstallprompt; iPhone no
// tiene ese aviso y se instala desde Compartir → Agregar a inicio.
const aviso = ref(window.__avisoInstalar ?? null)
const instalada = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone
const esIOS = /iphone|ipad|ipod/i.test(navigator.userAgent)
onMounted(() => {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    aviso.value = e
  })
  perfil.cargar().catch(() => {})
})
async function instalar() {
  aviso.value?.prompt()
  aviso.value = null
}

const sucursal = computed(() => perfil.miSucursal?.nombre ?? (perfil.veTodas ? 'Las seis sucursales' : '—'))

async function salir() {
  await auth.logout()
  perfil.limpiar()
  router.replace('/login')
}
</script>

<template>
  <div class="contenedor max-w-2xl pt-8">
    <p class="etiqueta etiqueta-vino mb-3">Perfil</p>
    <h1 class="titulo-pagina">{{ perfil.perfil?.nombre }}</h1>
    <p class="subtitulo mt-2">{{ ROLES[perfil.rol] }} · {{ sucursal }}</p>
    <p class="mt-1 text-sm text-[var(--texto-3)]">{{ auth.user?.email }}</p>

    <section class="tarjeta mt-8 divide-y divide-[var(--linea)]">
      <div class="flex items-center justify-between gap-4 p-5">
        <div><p class="font-semibold">Apariencia</p><p class="text-sm text-[var(--texto-2)]">Clara para el día, oscura para la noche.</p></div>
        <div class="flex gap-1.5">
          <button v-for="t in [['light', 'Clara'], ['dark', 'Oscura']]" :key="t[0]" class="chip !h-9" :aria-pressed="tema === t[0]" @click="setTheme(t[0])">{{ t[1] }}</button>
        </div>
      </div>
      <div class="p-5">
        <p class="font-semibold">Instalar en el teléfono</p>
        <p v-if="instalada" class="mt-1 text-sm text-[var(--texto-2)]">Ya la estás usando como app.</p>
        <template v-else-if="aviso">
          <p class="mt-1 text-sm text-[var(--texto-2)]">Queda en la pantalla de inicio y abre sin barra del navegador.</p>
          <button class="boton boton-vino boton-chico mt-3" @click="instalar">Instalar Picasso</button>
        </template>
        <p v-else-if="esIOS" class="mt-1 text-sm text-[var(--texto-2)]">En Safari: botón Compartir → «Agregar a inicio».</p>
        <p v-else class="mt-1 text-sm text-[var(--texto-2)]">En Chrome: menú ⋮ → «Instalar app» o «Agregar a la pantalla principal».</p>
      </div>
    </section>

    <QrCelular class="mt-3 hidden md:flex" />
    <MaterialProyecto v-if="HAY_MATERIAL" class="mt-6" />

    <button class="boton mt-6 w-full" :class="DEMO ? 'boton-primario' : 'boton-borde'" @click="salir">
      {{ DEMO ? 'Cambiar de cuenta (demo)' : 'Cerrar sesión' }}
    </button>
  </div>
</template>
