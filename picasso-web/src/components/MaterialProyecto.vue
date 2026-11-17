<script setup>
// Accesos al material del proyecto: video promocional, documentación y manual.
// `oscuro` es para la entrada (sobre las fotos); sin él usa los colores del tema.
import { ref } from 'vue'
import { mdiBookOpenPageVariantOutline, mdiFileDocumentMultipleOutline, mdiOpenInNew, mdiPlay } from '@mdi/js'

import Icono from '@/components/Icono.vue'
import VideoPromo from '@/components/VideoPromo.vue'
import { MATERIAL } from '@/lib/proyecto.js'

defineProps({ oscuro: { type: Boolean, default: false } })
const verVideo = ref(false)

const LIGAS = [
  { texto: 'Documentación', ayuda: 'Técnica, de producto y PDF', href: MATERIAL.documentacion, icono: mdiFileDocumentMultipleOutline },
  { texto: 'Manual de usuario', ayuda: 'Paso a paso por puesto', href: MATERIAL.manual, icono: mdiBookOpenPageVariantOutline },
]
</script>

<template>
  <section
    :class="
      oscuro
        ? 'rounded-[16px] border border-white/12 bg-black/70 p-5 text-[#f5f7fa] backdrop-blur-xl md:p-6'
        : 'tarjeta p-5'
    "
  >
    <p class="etiqueta" :class="oscuro ? '!text-[#f5f7fa]/60' : 'etiqueta-vino'">Conoce el proyecto</p>

    <button
      type="button"
      class="group mt-3 flex w-full items-center gap-3 rounded-[12px] px-4 py-3.5 text-left transition active:scale-[0.99]"
      :class="oscuro ? 'bg-[#fe7877] text-black hover:bg-[#ff8d8c]' : 'bg-[var(--vino)] text-white hover:opacity-90'"
      @click="verVideo = true"
    >
      <span class="grid h-10 w-10 shrink-0 place-items-center rounded-full" :class="oscuro ? 'bg-black/85 text-[#fe7877]' : 'bg-white/20'">
        <Icono :path="mdiPlay" :size="24" />
      </span>
      <span class="min-w-0 flex-1">
        <span class="block text-[15px] font-semibold">Ver el video promocional</span>
        <span class="block text-[12.5px] opacity-75">La app en menos de dos minutos</span>
      </span>
    </button>

    <div class="mt-2 grid grid-cols-2 gap-2">
      <a
        v-for="l in LIGAS"
        :key="l.href"
        :href="l.href"
        target="_blank"
        rel="noopener"
        class="flex flex-col gap-1 rounded-[12px] border px-3.5 py-3 transition"
        :class="
          oscuro
            ? 'border-white/12 bg-white/[0.06] hover:border-[#fe7877]/60'
            : 'border-[var(--linea)] hover:border-[var(--vino)]'
        "
      >
        <span class="flex items-center justify-between">
          <Icono :path="l.icono" :size="20" :class="oscuro ? 'text-[#fe7877]' : 'text-[var(--vino)]'" />
          <Icono :path="mdiOpenInNew" :size="14" class="opacity-50" />
        </span>
        <span class="text-[14px] font-semibold leading-tight">{{ l.texto }}</span>
        <span class="text-[12px] leading-snug opacity-60">{{ l.ayuda }}</span>
      </a>
    </div>

    <!-- Al body: el backdrop-blur de la tarjeta encerraría al fixed dentro de ella. -->
    <Teleport to="body">
      <VideoPromo v-if="verVideo" @cerrar="verVideo = false" />
    </Teleport>
  </section>
</template>
