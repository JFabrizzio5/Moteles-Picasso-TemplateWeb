<script setup>
// Lo que ha costado un folio: gastos ligados, registrar uno nuevo desde aquí o
// ligar uno que ya se registró sin folio.
import { computed, onMounted, ref } from 'vue'
import { mdiLinkVariant, mdiLinkVariantOff, mdiPlus } from '@mdi/js'

import GastoHoja from '@/components/GastoHoja.vue'
import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { CATEGORIA_GASTO, dia, mensajeError, pesos } from '@/lib/formato.js'
import * as finanzas from '@/services/finanzas.js'

const props = defineProps({ folio: { type: Object, required: true } })
const avisos = useToast()

const lista = ref([])
const hoja = ref(null) // 'nuevo' | 'ligar' | {gasto}
const sueltos = ref([])
const ocupado = ref(false)
const total = computed(() => lista.value.reduce((s, g) => s + Number(g.importe), 0))
const datosFolio = computed(() => ({
  id: props.folio.id,
  folio: props.folio.folio,
  titulo: props.folio.titulo,
  sucursal_id: props.folio.sucursal_id,
  habitacion_numero: props.folio.habitacion_numero,
}))

async function cargar() {
  try {
    lista.value = await finanzas.gastos({ incidencia_id: props.folio.id })
  } catch {
    lista.value = []
  }
}
async function abrirLigar() {
  hoja.value = 'ligar'
  try {
    // Los de la sucursal que aún no están en este folio (pueden estar en otros).
    const todos = await finanzas.gastos({ sucursal_id: props.folio.sucursal_id })
    sueltos.value = todos.filter((g) => !g.incidencias.some((f) => f.incidencia_id === props.folio.id))
  } catch (e) {
    avisos.error(mensajeError(e))
  }
}
async function ligar(g, ligar) {
  ocupado.value = true
  try {
    if (ligar) await finanzas.ligarFolio(g.id, props.folio.id)
    else await finanzas.desligarFolio(g.id, props.folio.id)
    avisos.success(ligar ? `${g.folio} quedó ligado al folio.` : `${g.folio} ya no está ligado a este folio.`)
    hoja.value = null
    await cargar()
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    ocupado.value = false
  }
}
function guardado() {
  hoja.value = null
  cargar()
}
onMounted(cargar)
</script>

<template>
  <section class="tarjeta p-5">
    <div class="flex items-baseline justify-between gap-3">
      <p class="etiqueta etiqueta-vino">Gastos del folio</p>
      <p v-if="lista.length" class="text-sm">Costo <strong class="tabular-nums">{{ pesos(total) }}</strong></p>
    </div>
    <ul v-if="lista.length" class="mt-3 divide-y divide-[var(--linea)]">
      <li v-for="g in lista" :key="g.id" class="flex items-start justify-between gap-3 py-2.5">
        <button class="min-w-0 text-left" @click="hoja = { gasto: g }">
          <p class="text-[15px] font-semibold">{{ g.concepto }}</p>
          <p class="text-[13px] text-[var(--texto-3)]">
            {{ g.folio }} · {{ dia(g.fecha) }} · {{ g.proveedor }} · {{ CATEGORIA_GASTO[g.categoria] }}
          </p>
          <p class="mt-0.5 text-[12.5px] text-[var(--texto-2)]">
            {{ g.partidas.map((p) => `${p.descripcion} ×${Number(p.cantidad)}`).join(' · ') }}
          </p>
        </button>
        <div class="flex shrink-0 flex-col items-end gap-1">
          <span class="font-semibold tabular-nums">{{ pesos(g.importe) }}</span>
          <button class="inline-flex items-center gap-1 text-[12px] text-[var(--texto-3)]" :disabled="ocupado" @click="ligar(g, false)">
            <Icono :path="mdiLinkVariantOff" :size="14" /> Desligar
          </button>
        </div>
      </li>
    </ul>
    <p v-else class="mt-3 text-sm text-[var(--texto-3)]">Este folio no tiene gastos registrados.</p>
    <div class="mt-4 grid grid-cols-2 gap-2">
      <button class="boton boton-vino boton-chico" @click="hoja = 'nuevo'"><Icono :path="mdiPlus" :size="18" /> Registrar gasto</button>
      <button class="boton boton-borde boton-chico" @click="abrirLigar"><Icono :path="mdiLinkVariant" :size="18" /> Ligar uno</button>
    </div>

    <GastoHoja v-if="hoja === 'nuevo'" :folio="datosFolio" @cerrar="hoja = null" @guardado="guardado" />
    <GastoHoja v-else-if="hoja?.gasto" :gasto="hoja.gasto" @cerrar="hoja = null" @guardado="guardado" />
    <Hoja v-else-if="hoja === 'ligar'" titulo="Ligar un gasto" :etiqueta="folio.folio" @cerrar="hoja = null">
      <p class="mb-3 text-sm text-[var(--texto-2)]">Gastos de la misma sucursal que todavía no están en este folio.</p>
      <ul v-if="sueltos.length" class="divide-y divide-[var(--linea)]">
        <li v-for="g in sueltos" :key="g.id">
          <button class="flex w-full items-center justify-between gap-3 py-3 text-left" :disabled="ocupado" @click="ligar(g, true)">
            <span class="min-w-0">
              <span class="block font-semibold">{{ g.concepto }}</span>
              <span class="block text-[13px] text-[var(--texto-3)]">{{ g.folio }} · {{ dia(g.fecha) }} · {{ g.proveedor }}</span>
            </span>
            <span class="font-semibold tabular-nums">{{ pesos(g.importe) }}</span>
          </button>
        </li>
      </ul>
      <p v-else class="text-sm text-[var(--texto-3)]">No hay más gastos de esta sucursal para ligar.</p>
    </Hoja>
  </section>
</template>
