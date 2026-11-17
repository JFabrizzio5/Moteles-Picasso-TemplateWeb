<script setup>
// Un punto del checklist en modo "solo lo que está mal": se toca el renglón
// únicamente si algo falla, y queda marcado con un tache rojo. Lo que no se
// toca queda bien al terminar.
import { mdiCloseThick } from '@mdi/js'

import Icono from '@/components/Icono.vue'

defineProps({
  punto: { type: Object, required: true },
  soloLectura: { type: Boolean, default: false },
})
const emit = defineEmits(['tocar'])
</script>

<template>
  <button
    type="button"
    class="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors duration-300 active:bg-[var(--superficie-2)] disabled:cursor-default"
    :class="punto.resultado === 'falla' ? 'bg-[#e5372f]/[0.07]' : ''"
    :disabled="soloLectura"
    @click="emit('tocar')"
  >
    <span class="min-w-0 flex-1">
      <span
        class="block text-[15.5px] leading-snug font-semibold"
        :class="punto.resultado === 'falla' ? 'text-[#d92d24]' : punto.resultado === 'no_aplica' ? 'text-[var(--texto-3)] line-through' : ''"
      >
        {{ punto.titulo }}
      </span>
      <span v-if="punto.resultado === 'falla'" class="mt-0.5 block text-[13.5px] leading-snug text-[#d92d24]">
        {{ punto.observacion }}
        <span v-if="punto.folio" class="folio-codigo ml-1 !text-[11px]">{{ punto.folio }}</span>
        <span v-if="punto.evidencias.length" class="ml-1 text-[var(--texto-3)]">· 📷 {{ punto.evidencias.length }}</span>
      </span>
      <span v-else-if="punto.resultado === 'no_aplica'" class="mt-0.5 block text-[12.5px] text-[var(--na)]">No aplica · {{ punto.motivo_no_aplica }}</span>
      <span v-else class="mt-0.5 line-clamp-1 text-[13px] leading-snug text-[var(--texto-3)]">{{ punto.texto }}</span>
    </span>

    <!-- Tache: gris y discreto mientras está bien; rojo y lleno cuando está mal -->
    <span
      class="grid h-11 w-11 shrink-0 place-items-center rounded-full border-2 transition-all duration-300"
      :class="
        punto.resultado === 'falla'
          ? 'pop border-transparent bg-[#e5372f] text-white shadow-[0_6px_16px_-6px_rgb(229_55_47/0.7)]'
          : 'border-[var(--linea-fuerte)] text-[var(--linea-fuerte)]'
      "
      :aria-label="punto.resultado === 'falla' ? 'Marcado mal' : 'Marcar mal'"
    >
      <Icono :path="mdiCloseThick" :size="punto.resultado === 'falla' ? 24 : 20" />
    </span>
  </button>
</template>
