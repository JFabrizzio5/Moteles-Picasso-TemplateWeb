<script setup>
// Barras horizontales para comparar sucursales o categorías. Una o dos series
// (ingresos y gastos) en el mismo eje de pesos; el valor va escrito al final.
import { computed } from 'vue'

import { pesos } from '@/lib/formato.js'

const props = defineProps({
  /** [{ etiqueta, valores: { ingresos?, gastos? } }] */
  filas: { type: Array, required: true },
  /** [{ clave, texto, color }] */
  series: { type: Array, required: true },
})

const tope = computed(() => Math.max(1, ...props.filas.flatMap((f) => props.series.map((s) => Number(f.valores[s.clave] ?? 0)))))
const ancho = (v) => `${(Number(v ?? 0) / tope.value) * 100}%`
</script>

<template>
  <figure class="m-0">
    <figcaption v-if="series.length > 1" class="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-[var(--texto-2)]">
      <span v-for="s in series" :key="s.clave" class="inline-flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-[3px]" :style="{ background: s.color }" />{{ s.texto }}
      </span>
    </figcaption>
    <ul class="space-y-3">
      <li v-for="f in filas" :key="f.etiqueta">
        <p class="mb-1 text-[13.5px] font-semibold">{{ f.etiqueta }}</p>
        <div v-for="s in series" :key="s.clave" class="flex items-center gap-2" :title="`${s.texto}: ${pesos(f.valores[s.clave] ?? 0)}`">
          <span class="h-3 flex-1 overflow-hidden rounded-[3px] bg-[var(--superficie-2)]">
            <span class="block h-full rounded-[3px]" :style="{ width: ancho(f.valores[s.clave]), background: s.color }" />
          </span>
          <span class="w-[92px] shrink-0 text-right text-[12.5px] tabular-nums text-[var(--texto-2)]">{{ pesos(f.valores[s.clave] ?? 0, true) }}</span>
        </div>
      </li>
    </ul>
  </figure>
</template>
