<script setup>
// Indicadores con su definición: cumplimiento, conformidad, tiempo de solución
// y reincidencia. Sin revisar nunca se presenta como aprobado.
import { onActivated, onMounted, ref, watch } from 'vue'

import BotonPdf from '@/components/BotonPdf.vue'
import Esqueleto from '@/components/Esqueleto.vue'
import ReporteFinanzas from '@/components/ReporteFinanzas.vue'
import { useToast } from '@/composables/useToast.js'
import { corto, hoyISO, mensajeError, porcentaje } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const avisos = useToast()
const perfil = usePerfilStore()
const datos = ref(null)
const dias = ref(6)
const cargando = ref(true)
const PERIODOS = [
  { valor: 0, texto: 'Hoy' },
  { valor: 6, texto: '7 días' },
  { valor: 29, texto: '30 días' },
  { valor: 89, texto: '90 días' },
]

async function cargar(opc) {
  if (!opc?.silencioso) cargando.value = true
  try {
    datos.value = await picasso.indicadores({ desde: hoyISO(dias.value), hasta: hoyISO() })
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    cargando.value = false
  }
}
watch(dias, cargar)
onMounted(cargar)
let primera = true
onActivated(() => (primera ? (primera = false) : cargar({ silencioso: true })))

const horas = (h) => (h === null || h === undefined ? '—' : h < 48 ? `${h} h` : `${Math.round(h / 24)} días`)
</script>

<template>
  <div class="contenedor pt-8">
    <p class="etiqueta etiqueta-vino mb-3">Reportes</p>
    <h1 class="titulo-pagina">Información que lleva <em>a una decisión.</em></h1>
    <div class="mt-5">
      <BotonPdf
        :ruta="`/reportes/grupo.pdf?desde=${hoyISO(dias)}&hasta=${hoyISO()}`"
        :nombre="`Reporte-Picasso-${hoyISO(dias)}-a-${hoyISO()}.pdf`"
        texto="Descargar reporte del periodo (PDF)"
      />
    </div>
    <div class="sin-scroll -mx-4 mt-6 flex gap-2 overflow-x-auto px-4">
      <button v-for="p in PERIODOS" :key="p.valor" class="chip" :aria-pressed="dias === p.valor" @click="dias = p.valor">{{ p.texto }}</button>
    </div>

    <Esqueleto v-if="cargando && !datos" tipo="graficas" />
    <template v-else-if="datos">
      <div class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" :class="cargando ? 'opacity-60' : ''">
        <div class="tarjeta p-5">
          <p class="etiqueta">Cumplimiento de revisión</p>
          <p class="serif mt-2 text-[44px] leading-none">{{ porcentaje(datos.total.cumplimiento_gerente) }}</p>
          <p class="text-sm text-[var(--texto-2)]">gerente · ama {{ porcentaje(datos.total.cumplimiento_ama) }}</p>
          <p class="mt-3 text-[12px] text-[var(--texto-3)]">Completas / exigibles, por puesto y frecuencia.</p>
        </div>
        <div class="tarjeta p-5">
          <p class="etiqueta">Conformidad de puntos</p>
          <p class="serif mt-2 text-[44px] leading-none">{{ porcentaje(datos.total.conformidad) }}</p>
          <p class="text-sm text-[var(--texto-2)]">{{ datos.total.bien }} bien · {{ datos.total.fallas }} fallas</p>
          <p class="mt-3 text-[12px] text-[var(--texto-3)]">Bien / (Bien + Falla). No aplica: {{ datos.total.no_aplica }} · Sin revisar: {{ datos.total.sin_revisar }}.</p>
        </div>
        <div class="tarjeta p-5">
          <p class="etiqueta">Tiempo de solución</p>
          <p class="serif mt-2 text-[44px] leading-none">{{ horas(datos.total.horas_solucion_promedio) }}</p>
          <p class="text-sm text-[var(--texto-2)]">promedio · {{ datos.total.cerradas }} cerrados</p>
          <p class="mt-3 text-[12px] text-[var(--texto-3)]">El abierto más antiguo lleva {{ horas(datos.total.horas_abiertas_max) }}.</p>
        </div>
        <div class="tarjeta p-5">
          <p class="etiqueta">Reincidencia</p>
          <p class="serif mt-2 text-[44px] leading-none">{{ datos.reincidencias.length }}</p>
          <p class="text-sm text-[var(--texto-2)]">cuartos con la misma falla repetida</p>
          <p class="mt-3 text-[12px] text-[var(--texto-3)]">Misma categoría, misma habitación, dentro del periodo.</p>
        </div>
      </div>

      <h2 class="serif mt-12 mb-4 text-[40px]">Por <em>sucursal</em></h2>
      <div class="tarjeta overflow-x-auto">
        <table class="w-full min-w-[720px] text-left text-[14px]">
          <thead class="bg-[var(--carbon)] text-[#f5f7fa]">
            <tr>
              <th class="etiqueta px-4 py-3 !text-[#f5f7fa]/80">Sucursal</th>
              <th class="etiqueta px-4 py-3 !text-[#f5f7fa]/80">Gerente</th>
              <th class="etiqueta px-4 py-3 !text-[#f5f7fa]/80">Ama</th>
              <th class="etiqueta px-4 py-3 !text-[#f5f7fa]/80">Conformidad</th>
              <th class="etiqueta px-4 py-3 !text-[#f5f7fa]/80">Fallas</th>
              <th class="etiqueta px-4 py-3 !text-[#f5f7fa]/80">Abiertos</th>
              <th class="etiqueta px-4 py-3 !text-[#f5f7fa]/80">Solución</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in datos.sucursales" :key="s.sucursal_id" :class="i % 2 ? '' : 'bg-[var(--superficie-2)]'">
              <td class="px-4 py-3 font-semibold">{{ corto(s.nombre) }}</td>
              <td class="px-4 py-3">{{ porcentaje(s.cumplimiento_gerente) }}</td>
              <td class="px-4 py-3">{{ porcentaje(s.cumplimiento_ama) }}</td>
              <td class="px-4 py-3">{{ porcentaje(s.conformidad) }}</td>
              <td class="px-4 py-3">{{ s.fallas }}</td>
              <td class="px-4 py-3">{{ s.abiertas }}</td>
              <td class="px-4 py-3">{{ horas(s.horas_solucion_promedio) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-12 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 class="serif mb-4 text-[34px]">Fallas <em>frecuentes</em></h2>
          <div class="tarjeta divide-y divide-[var(--linea)]">
            <div v-for="f in datos.fallas_frecuentes" :key="f.codigo" class="flex items-center justify-between p-4">
              <span><strong class="etiqueta etiqueta-vino mr-2">{{ f.codigo }}</strong>{{ f.titulo }}</span>
              <span class="serif text-2xl">{{ f.veces }}</span>
            </div>
            <p v-if="!datos.fallas_frecuentes.length" class="p-4 text-sm text-[var(--texto-2)]">Sin fallas en el periodo.</p>
          </div>
        </section>
        <section>
          <h2 class="serif mb-4 text-[34px]">Reincidencias</h2>
          <div class="tarjeta divide-y divide-[var(--linea)]">
            <RouterLink v-for="r in datos.reincidencias" :key="`${r.habitacion_id}-${r.categoria}`" :to="`/habitacion/${r.habitacion_id}`" class="flex items-center justify-between gap-3 p-4">
              <span><strong>{{ corto(r.sucursal_nombre) }} · Hab. {{ r.habitacion_numero }}</strong><br /><span class="text-sm text-[var(--texto-2)]">{{ r.categoria }} · {{ r.folios.join(', ') }}</span></span>
              <span class="serif text-2xl text-[var(--vino-texto)]">{{ r.veces }}×</span>
            </RouterLink>
            <p v-if="!datos.reincidencias.length" class="p-4 text-sm text-[var(--texto-2)]">Ninguna falla se repitió en la misma habitación.</p>
          </div>
        </section>
      </div>
    </template>

    <!-- Finanzas: gerentes, administración y propietarios (la ama de llaves no la ve). -->
    <ReporteFinanzas v-if="perfil.perfil && !perfil.esAma" :desde="hoyISO(dias)" :hasta="hoyISO()" />
  </div>
</template>
