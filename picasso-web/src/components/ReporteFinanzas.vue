<script setup>
// Finanzas dentro de Reportes: gráficas de ingresos y gastos (todas las
// sucursales juntas, comparadas o una sola) y el PDF de todas o de cada una.
import { computed, onMounted, ref, watch } from 'vue'

import BotonPdf from '@/components/BotonPdf.vue'
import Cargando from '@/components/Cargando.vue'
import GraficaBarras from '@/components/GraficaBarras.vue'
import GraficaSerie from '@/components/GraficaSerie.vue'
import { CATEGORIA_GASTO, corto, dia, mensajeError, pesos } from '@/lib/formato.js'
import * as finanzas from '@/services/finanzas.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const props = defineProps({
  desde: { type: String, required: true },
  hasta: { type: String, required: true },
})
const perfil = usePerfilStore()
const sucursal = ref('')
const cargando = ref(true)
const error = ref('')
const serie = ref(null)
const resumen = ref(null)
const analisis = ref(null)

const INGRESOS = { clave: 'ingresos', texto: 'Ingresos', color: 'var(--serie-ingresos)' }
const GASTOS = { clave: 'gastos', texto: 'Gastos', color: 'var(--serie-gastos)' }

async function cargar() {
  cargando.value = true
  error.value = ''
  const p = { desde: props.desde, hasta: props.hasta, sucursal_id: sucursal.value || undefined }
  try {
    ;[serie.value, resumen.value, analisis.value] = await Promise.all([
      finanzas.serie(p),
      finanzas.resumen(p),
      finanzas.analisisGastos(p),
    ])
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    cargando.value = false
  }
}
watch(() => [props.desde, props.hasta, sucursal.value], cargar)
onMounted(cargar)

const porSucursal = computed(() =>
  (resumen.value?.sucursales ?? []).map((s) => ({ etiqueta: corto(s.nombre), valores: { ingresos: s.ingresos, gastos: s.gastos } })),
)
const porCategoria = computed(() =>
  (analisis.value?.por_categoria ?? []).map((c) => ({ etiqueta: CATEGORIA_GASTO[c.categoria], valores: { gastos: c.total } })),
)
const pdf = (sucursalId) => `/finanzas/reporte.pdf?desde=${props.desde}&hasta=${props.hasta}${sucursalId ? `&sucursal_id=${sucursalId}` : ''}`
</script>

<template>
  <section class="mt-14">
    <p class="etiqueta etiqueta-vino mb-2">Finanzas</p>
    <h2 class="serif text-[40px] leading-none">Ingresos y <em>gastos.</em></h2>
    <p class="mt-2 text-sm text-[var(--texto-2)]">Del {{ dia(desde) }} al {{ dia(hasta) }} · ingresos de Kairos, gastos registrados en Picasso.</p>

    <div class="mt-4 flex flex-wrap items-end gap-3">
      <label v-if="perfil.veTodas" class="text-[13px] font-semibold text-[var(--texto-2)]">
        Graficar
        <select v-model="sucursal" class="campo mt-1 min-w-[230px]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in perfil.sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </label>
      <BotonPdf :ruta="pdf(sucursal)" :nombre="`Finanzas-${sucursal ? 'sucursal-' + sucursal : 'todas'}-${desde}-a-${hasta}.pdf`" :texto="sucursal ? 'PDF de esta sucursal' : 'PDF de todas las sucursales'" />
    </div>

    <Cargando v-if="cargando && !serie" texto="Graficando" />
    <p v-else-if="error" class="mt-4 text-sm text-[var(--falla)]">{{ error }}</p>
    <div v-else-if="serie" class="mt-5 grid gap-4 lg:grid-cols-2" :class="cargando ? 'opacity-60' : ''">
      <div class="tarjeta p-5 lg:col-span-2">
        <p class="etiqueta etiqueta-vino mb-3">En el tiempo</p>
        <GraficaSerie :puntos="serie.puntos" :agrupado="serie.agrupado" />
      </div>
      <div v-if="porSucursal.length > 1" class="tarjeta p-5">
        <p class="etiqueta etiqueta-vino mb-3">Por sucursal</p>
        <GraficaBarras :filas="porSucursal" :series="[INGRESOS, GASTOS]" />
      </div>
      <div class="tarjeta p-5" :class="porSucursal.length > 1 ? '' : 'lg:col-span-2'">
        <p class="etiqueta etiqueta-vino mb-3">Gastos por categoría</p>
        <GraficaBarras v-if="porCategoria.length" :filas="porCategoria" :series="[GASTOS]" />
        <p v-else class="text-sm text-[var(--texto-3)]">Sin gastos en el periodo.</p>
      </div>
    </div>

    <!-- Un PDF por sucursal, para imprimir o mandar a cada gerente. -->
    <div v-if="perfil.veTodas" class="tarjeta mt-4 p-5">
      <p class="etiqueta etiqueta-vino mb-3">PDF por sucursal</p>
      <div class="flex flex-wrap gap-2">
        <BotonPdf :ruta="pdf('')" :nombre="`Finanzas-todas-${desde}-a-${hasta}.pdf`" texto="Todas" />
        <BotonPdf
          v-for="s in perfil.sucursales"
          :key="s.id"
          :ruta="pdf(s.id)"
          :nombre="`Finanzas-${corto(s.nombre)}-${desde}-a-${hasta}.pdf`"
          :texto="corto(s.nombre)"
        />
      </div>
      <p v-if="resumen" class="mt-3 text-[12.5px] text-[var(--texto-3)]">
        En el periodo: ingresos {{ pesos(resumen.ingresos, true) }} · gastos {{ pesos(resumen.gastos, true) }} · utilidad {{ pesos(resumen.utilidad, true) }}
      </p>
    </div>
  </section>
</template>
