<script setup>
// Ingresos y gastos en el tiempo: barras agrupadas por día, semana o mes, un
// solo eje en pesos. Al pasar el dedo o el mouse, el tramo muestra sus cifras.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { pesos } from '@/lib/formato.js'

const props = defineProps({
  /** [{ inicio, fin, ingresos, gastos }] (de /finanzas/serie). */
  puntos: { type: Array, required: true },
  agrupado: { type: String, default: 'dia' },
  alto: { type: Number, default: 240 },
})

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const corto = (iso) => {
  const [, m, d] = iso.split('-').map(Number)
  return props.agrupado === 'mes' ? MESES[m - 1] : `${d} ${MESES[m - 1]}`
}
const SERIES = [
  { clave: 'ingresos', texto: 'Ingresos', color: 'var(--serie-ingresos)' },
  { clave: 'gastos', texto: 'Gastos', color: 'var(--serie-gastos)' },
]

// El dibujo mide lo mismo que su caja: así los textos no se encogen en el celular.
const caja = ref(null)
const ANCHO = ref(720)
let observador = null
onMounted(() => {
  observador = new ResizeObserver(([e]) => (ANCHO.value = Math.max(280, Math.round(e.contentRect.width))))
  observador.observe(caja.value)
})
onBeforeUnmount(() => observador?.disconnect())
const M = { izq: 52, der: 8, arr: 10, aba: 26 }
const area = computed(() => ({ w: ANCHO.value - M.izq - M.der, h: props.alto - M.arr - M.aba }))
const datos = computed(() => props.puntos.map((p) => ({ ...p, ingresos: Number(p.ingresos), gastos: Number(p.gastos) })))
const tope = computed(() => {
  const max = Math.max(1, ...datos.value.flatMap((p) => [p.ingresos, p.gastos]))
  const paso = 10 ** Math.floor(Math.log10(max))
  return Math.ceil(max / paso) * paso
})
const marcas = computed(() => [0, 0.25, 0.5, 0.75, 1].map((f) => f * tope.value))
const banda = computed(() => area.value.w / Math.max(datos.value.length, 1))
const barra = computed(() => Math.max(2, Math.min(18, (banda.value - 6) / 2 - 1)))
const y = (v) => M.arr + area.value.h - (v / tope.value) * area.value.h
const cada = computed(() => Math.ceil(datos.value.length / Math.max(3, Math.floor(ANCHO.value / 70))))
const miles = (v) => (v >= 1000 ? `$${Math.round(v / 1000).toLocaleString('es-MX')}k` : `$${Math.round(v)}`)

const activo = ref(null)
const totales = computed(() => ({
  ingresos: datos.value.reduce((s, p) => s + p.ingresos, 0),
  gastos: datos.value.reduce((s, p) => s + p.gastos, 0),
}))
</script>

<template>
  <figure class="m-0">
    <figcaption class="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px]">
      <span v-for="s in SERIES" :key="s.clave" class="inline-flex items-center gap-1.5 text-[var(--texto-2)]">
        <span class="h-2.5 w-2.5 rounded-[3px]" :style="{ background: s.color }" />
        {{ s.texto }} <strong class="tabular-nums text-[var(--texto)]">{{ pesos(totales[s.clave], true) }}</strong>
      </span>
      <span class="ml-auto text-[var(--texto-3)]">por {{ agrupado === 'dia' ? 'día' : agrupado }}</span>
    </figcaption>
    <div ref="caja" class="relative">
      <svg :viewBox="`0 0 ${ANCHO} ${alto}`" class="block w-full" role="img" aria-label="Ingresos y gastos en el tiempo" @mouseleave="activo = null">
        <g>
          <template v-for="m in marcas" :key="m">
            <line :x1="M.izq" :x2="ANCHO - M.der" :y1="y(m)" :y2="y(m)" stroke="var(--linea)" stroke-width="1" />
            <text :x="M.izq - 6" :y="y(m) + 3.5" text-anchor="end" font-size="10.5" fill="var(--texto-3)">{{ miles(m) }}</text>
          </template>
        </g>
        <g v-for="(p, i) in datos" :key="p.inicio">
          <rect
            :x="M.izq + i * banda"
            :y="M.arr"
            :width="banda"
            :height="area.h"
            :fill="activo === i ? 'var(--superficie-2)' : 'transparent'"
            @mouseenter="activo = i"
            @touchstart.passive="activo = i"
          />
          <rect
            v-for="(s, k) in SERIES"
            :key="s.clave"
            :x="M.izq + i * banda + banda / 2 - barra - 1 + k * (barra + 2)"
            :y="y(p[s.clave])"
            :width="barra"
            :height="Math.max(0, M.arr + area.h - y(p[s.clave]))"
            :fill="s.color"
            rx="2"
            pointer-events="none"
          />
          <text
            v-if="i % cada === 0"
            :x="M.izq + i * banda + banda / 2"
            :y="alto - 8"
            text-anchor="middle"
            font-size="10.5"
            fill="var(--texto-3)"
          >
            {{ corto(p.inicio) }}
          </text>
        </g>
      </svg>
      <div
        v-if="activo !== null && datos[activo]"
        class="pointer-events-none absolute top-1 rounded-[10px] border border-[var(--linea)] bg-[var(--superficie)] px-3 py-2 text-[12.5px] shadow-lg"
        :style="{ left: `${Math.min(60, Math.max(2, ((M.izq + activo * banda) / ANCHO) * 100))}%` }"
      >
        <p class="font-semibold">{{ corto(datos[activo].inicio) }}<template v-if="datos[activo].fin !== datos[activo].inicio"> – {{ corto(datos[activo].fin) }}</template></p>
        <p v-for="s in SERIES" :key="s.clave" class="flex items-center gap-1.5 tabular-nums">
          <span class="h-2 w-2 rounded-[2px]" :style="{ background: s.color }" />{{ s.texto }} {{ pesos(datos[activo][s.clave]) }}
        </p>
      </div>
    </div>
  </figure>
</template>
