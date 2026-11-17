<script setup>
// El comercial de la app en pantalla completa: vertical en el celular, horizontal en la computadora.
import { onBeforeUnmount, onMounted } from 'vue'
import { mdiClose } from '@mdi/js'

import Icono from '@/components/Icono.vue'
import { MATERIAL } from '@/lib/proyecto.js'

const emit = defineEmits(['cerrar'])
const ancho = window.matchMedia('(min-width: 768px) and (min-aspect-ratio: 1/1)').matches
const fuente = ancho ? MATERIAL.video.horizontal : MATERIAL.video.vertical
const portada = ancho ? MATERIAL.video.portadaHorizontal : MATERIAL.video.portadaVertical

const tecla = (e) => e.key === 'Escape' && emit('cerrar')
onMounted(() => window.addEventListener('keydown', tecla))
onBeforeUnmount(() => window.removeEventListener('keydown', tecla))
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 backdrop-blur-sm"
    role="dialog"
    aria-modal="true"
    aria-label="Video promocional"
    style="padding-top: max(1rem, env(safe-area-inset-top)); padding-bottom: max(1rem, env(safe-area-inset-bottom))"
    @click.self="emit('cerrar')"
  >
    <button
      type="button"
      class="absolute top-4 right-4 grid h-11 w-11 place-items-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
      style="margin-top: env(safe-area-inset-top)"
      aria-label="Cerrar el video"
      @click="emit('cerrar')"
    >
      <Icono :path="mdiClose" :size="24" />
    </button>
    <video
      :src="fuente"
      :poster="portada"
      class="max-h-full max-w-full rounded-[12px] bg-black shadow-2xl"
      :class="ancho ? 'w-[min(1100px,100%)]' : 'h-[min(86dvh,100%)]'"
      controls
      autoplay
      playsinline
      preload="metadata"
    />
  </div>
</template>
