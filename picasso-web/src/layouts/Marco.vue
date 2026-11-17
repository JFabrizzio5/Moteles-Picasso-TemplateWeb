<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  mdiAccountOutline,
  mdiBedKingOutline,
  mdiCashMultiple,
  mdiChartLine,
  mdiCogOutline,
  mdiFileDocumentAlertOutline,
  mdiViewGridOutline,
} from '@mdi/js'

import Icono from '@/components/Icono.vue'
import Marca from '@/components/Marca.vue'
import { DEMO } from '@/lib/demo.js'
import { corto, ROLES } from '@/lib/formato.js'
import { useAuthStore } from '@/stores/auth.store.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const perfil = usePerfilStore()
const ruta = useRoute()

onMounted(() => {
  if (useAuthStore().isAuthenticated) perfil.cargar().catch(() => {})
})

const menu = computed(() => {
  const rol = perfil.rol
  if (!rol) return []
  const items = []
  if (perfil.veTodas) items.push({ a: '/', texto: 'Panel', icono: mdiViewGridOutline })
  else items.push({ a: '/', texto: 'Cuartos', icono: mdiBedKingOutline })
  items.push({ a: '/folios', texto: 'Folios', icono: mdiFileDocumentAlertOutline })
  if (rol !== 'ama_llaves') items.push({ a: '/finanzas', texto: 'Finanzas', icono: mdiCashMultiple })
  if (rol !== 'ama_llaves') items.push({ a: '/reportes', texto: 'Reportes', icono: mdiChartLine })
  if (rol === 'admin') items.push({ a: '/admin', texto: 'Ajustes', icono: mdiCogOutline })
  items.push({ a: '/perfil', texto: 'Perfil', icono: mdiAccountOutline })
  return items
})

const activo = (a) => (a === '/' ? ruta.path === '/' : ruta.path.startsWith(a))
const inmersiva = computed(() => ruta.meta?.inmersiva)
const lugar = computed(() =>
  perfil.miSucursal ? corto(perfil.miSucursal.nombre) : perfil.veTodas ? 'Seis sucursales' : '',
)
</script>

<template>
  <div class="fondo-app min-h-dvh">
    <header
      v-if="!inmersiva"
      class="sticky top-0 z-40 bg-[var(--barra)] text-[var(--sobre-barra)]"
      style="padding-top: env(safe-area-inset-top)"
    >
      <div class="contenedor flex h-[60px] items-center justify-between gap-4">
        <RouterLink to="/" class="flex items-center gap-3">
          <Marca :alto="38" />
          <span v-if="DEMO" class="rounded-full bg-[#fe7877] px-2 py-0.5 text-[10px] font-bold tracking-wider text-black">DEMO</span>
          <span v-if="lugar" class="etiqueta hidden !text-white/55 sm:inline">{{ lugar }}</span>
        </RouterLink>
        <nav class="hidden items-center gap-1 md:flex">
          <RouterLink
            v-for="item in menu"
            :key="item.a"
            :to="item.a"
            class="boton-mono rounded-[10px] px-4 py-2 transition"
            :class="activo(item.a) ? 'bg-[var(--primario)] text-[var(--sobre-primario)]' : 'text-white/70 hover:text-white'"
          >
            {{ item.texto }}
          </RouterLink>
        </nav>
        <span v-if="perfil.perfil" class="etiqueta !text-white/60 md:hidden">{{ ROLES[perfil.rol] }}</span>
      </div>
    </header>

    <main :class="inmersiva ? '' : 'pb-28 md:pb-16'">
      <RouterView v-slot="{ Component, route: actual }">
        <Transition name="pagina" mode="out-in">
          <component :is="Component" :key="actual.path" />
        </Transition>
      </RouterView>
    </main>

    <!-- Navegación del celular: ícono y nombre siempre visibles -->
    <nav
      v-if="!inmersiva && menu.length"
      class="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-black/95 backdrop-blur md:hidden"
      style="padding-bottom: env(safe-area-inset-bottom)"
    >
      <div class="mx-auto grid max-w-md" :style="{ gridTemplateColumns: `repeat(${menu.length}, minmax(0, 1fr))` }">
        <RouterLink
          v-for="item in menu"
          :key="item.a"
          :to="item.a"
          class="group flex flex-col items-center gap-1 pt-2.5 pb-2 text-[11.5px] font-semibold transition-colors"
          :class="activo(item.a) ? 'text-[#fe7877]' : 'text-white/55'"
        >
          <span
            class="grid h-8 w-14 place-items-center rounded-full transition-all duration-300"
            :class="activo(item.a) ? 'bg-[#fe7877] text-black' : 'group-active:bg-white/10'"
          >
            <Icono :path="item.icono" :size="21" />
          </span>
          {{ item.texto }}
        </RouterLink>
      </div>
    </nav>
  </div>
</template>
