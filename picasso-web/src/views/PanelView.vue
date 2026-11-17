<script setup>
// Propietarios: las seis sucursales en una sola vista.
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { mdiArrowRight } from '@mdi/js'

import BotonPdf from '@/components/BotonPdf.vue'
import Esqueleto from '@/components/Esqueleto.vue'
import Barra from '@/components/Barra.vue'
import Icono from '@/components/Icono.vue'
import Numero from '@/components/Numero.vue'
import { useToast } from '@/composables/useToast.js'
import { corto, cuando, fechaTexto, hora, hoyISO, mensajeError, PRIORIDAD_LISTA } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'

const avisos = useToast()
const FOTOS = ['/sucursales/lerma.jpg', '/sucursales/periferico.jpg', '/sucursales/circuito.jpg', '/sucursales/toluca.jpg', '/sucursales/churubusco.jpg', '/sucursales/vaqueritos.jpg']
const foto = ref(0)
let reloj = null
onMounted(() => (reloj = setInterval(() => (foto.value = (foto.value + 1) % FOTOS.length), 6000)))
onBeforeUnmount(() => clearInterval(reloj))
const datos = ref(null)
const cargando = ref(true)
const dias = ref(1)

const PERIODOS = [
  { valor: 0, texto: 'Hoy' },
  { valor: 1, texto: 'Ayer y hoy' },
  { valor: 6, texto: '7 días' },
  { valor: 29, texto: '30 días' },
]

// Folios abiertos por prioridad (todas las sucursales, sin periodo, como «abiertas»).
const abiertasPorPrioridad = ref(null)
async function cargarPrioridades() {
  try {
    const conteo = await picasso.conteoFolios()
    abiertasPorPrioridad.value = Object.fromEntries(
      PRIORIDAD_LISTA.map((p) => [
        p.valor,
        conteo.filter((c) => c.prioridad === p.valor && ['reportada', 'en_atencion'].includes(c.estado)).reduce((n, c) => n + c.total, 0),
      ]),
    )
  } catch {
    abiertasPorPrioridad.value = null
  }
}

async function cargar(opc) {
  if (!opc?.silencioso) cargando.value = true
  cargarPrioridades()
  try {
    datos.value = await picasso.panel({ desde: hoyISO(dias.value), hasta: hoyISO() })
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

const totales = computed(() => {
  const s = datos.value?.sucursales ?? []
  const suma = (k) => s.reduce((n, x) => n + x[k], 0)
  return {
    gerente: [suma('gerente_completas'), suma('gerente_exigibles')],
    ama: [suma('ama_completas'), suma('ama_exigibles')],
  }
})
const pendientes = computed(() => (datos.value ? datos.value.exigibles - datos.value.completas : 0))
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0)
</script>

<template>
  <div>
    <section class="relative overflow-hidden bg-black text-[#f5f7fa]">
      <img
        v-for="(f, i) in FOTOS"
        :key="f"
        :src="f"
        alt=""
        class="foto-cubierta absolute inset-0 transition-opacity duration-[1600ms]"
        :class="i === foto ? 'opacity-60' : 'opacity-0'"
      />
      <div class="velo absolute inset-0" />
      <div class="contenedor relative pt-14 pb-10 md:pt-24 md:pb-16">
        <p class="etiqueta mb-4 !text-[#f5f7fa]/60">Propietarios</p>
        <h1 class="serif text-[50px] leading-[0.95] md:text-[88px]">
          Seis sucursales,<br /><em class="text-[#fe7877]">en una sola vista.</em>
        </h1>
        <p v-if="datos" class="etiqueta mt-6 !text-[#f5f7fa]/55">
          Corte · {{ fechaTexto(datos.corte) }}, {{ hora(datos.corte) }} · hora de CDMX
        </p>
        <div class="sin-scroll -mx-4 mt-5 flex gap-2 overflow-x-auto px-4">
          <button
            v-for="p in PERIODOS"
            :key="p.valor"
            class="chip"
            :class="dias === p.valor ? '!border-[#fe7877] !bg-[#fe7877] !text-black' : '!border-white/25 !text-white/85'"
            @click="dias = p.valor"
          >
            {{ p.texto }}
          </button>
        </div>
      </div>
    </section>

    <div v-if="cargando && !datos" class="contenedor pt-2"><Esqueleto tipo="panel" /></div>
    <div v-else-if="datos" class="contenedor pt-8" :class="cargando ? 'opacity-60' : ''">
      <div class="escalonado grid gap-3 sm:grid-cols-3">
        <div class="tarjeta tarjeta-viva p-5" style="--i: 0">
          <p class="serif text-[52px] leading-none text-[var(--vino-texto)]"><Numero :valor="datos.completas" /> <span class="text-[var(--texto-3)]">/ <Numero :valor="datos.exigibles" /></span></p>
          <p class="mt-2 font-bold">Revisiones completas</p>
          <p class="mt-1 text-[13px] text-[var(--texto-3)]">Gerente + ama de llaves · faltan {{ pendientes }}</p>
        </div>
        <div class="tarjeta tarjeta-viva p-5" style="--i: 1">
          <RouterLink to="/folios?estado=abiertas" class="block">
            <p class="serif text-[52px] leading-none text-[var(--vino-texto)]"><Numero :valor="datos.abiertas" /></p>
            <p class="mt-2 font-bold">Incidencias abiertas</p>
          </RouterLink>
          <p v-if="!abiertasPorPrioridad" class="mt-1 text-[13px] text-[var(--texto-3)]">Incluye casos en atención</p>
          <div v-else class="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[13px]">
            <RouterLink
              v-for="p in PRIORIDAD_LISTA"
              :key="p.valor"
              :to="`/folios?estado=abiertas&prioridad=${p.valor}`"
              class="inline-flex items-center gap-1.5 text-[var(--texto-2)] hover:text-[var(--texto)]"
            >
              <span class="h-2 w-2 rounded-full" :style="{ background: p.color }" />
              <strong class="tabular-nums">{{ abiertasPorPrioridad[p.valor] }}</strong> {{ p.texto.toLowerCase() }}
            </RouterLink>
          </div>
        </div>
        <div class="tarjeta tarjeta-viva p-5" style="--i: 2">
          <p class="serif text-[52px] leading-none text-[var(--vino-texto)]"><Numero :valor="datos.bloqueados" /></p>
          <p class="mt-2 font-bold">Cuartos bloqueados</p>
          <p class="mt-1 text-[13px] text-[var(--texto-3)]">Decisión vigente: no puede rentarse</p>
        </div>
      </div>

      <div class="mt-12 mb-5 flex items-end justify-between gap-4">
        <div>
          <p class="etiqueta etiqueta-vino mb-2">Resumen por sucursal</p>
          <h2 class="serif text-[40px] leading-none md:text-[56px]">Cada casa, <em>su avance.</em></h2>
        </div>
        <div class="flex items-center gap-2">
          <BotonPdf :ruta="`/reportes/grupo.pdf?desde=${hoyISO(dias)}&hasta=${hoyISO()}`" :nombre="`Reporte-Picasso-${hoyISO(dias)}-a-${hoyISO()}.pdf`" texto="PDF" />
          <RouterLink to="/folios" class="boton boton-vino boton-chico hidden sm:inline-flex">Ver incidencias <Icono :path="mdiArrowRight" :size="18" /></RouterLink>
        </div>
      </div>

      <div class="escalonado grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="(s, i) in datos.sucursales"
          :key="s.sucursal_id"
          :to="`/folios?estado=abiertas&sucursal=${s.sucursal_id}`"
          class="group tarjeta tarjeta-viva overflow-hidden"
          :style="{ '--i': i }"
        >
          <div class="relative h-44 overflow-hidden bg-[var(--carbon)]">
            <img v-if="s.foto" :src="s.foto" alt="" class="foto-cubierta transition duration-700 group-hover:scale-[1.04]" />
            <div v-else class="grid h-full place-items-center">
              <p class="serif text-2xl text-[#f5f7fa]/60">Fotografía <em>pendiente</em></p>
            </div>
            <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
            <span class="etiqueta absolute top-3 left-3 rounded-full bg-black/40 px-3 py-1 !text-[#f5f7fa] backdrop-blur">N° {{ s.clave }}</span>
            <span
              v-if="s.no_rentar"
              class="absolute top-3 right-3 rounded-full bg-[var(--vino)] px-3 py-1 text-xs font-bold text-white"
            >{{ s.no_rentar }} sin rentar</span>
            <p class="serif absolute bottom-3 left-4 text-[34px] text-[#f5f7fa]">{{ corto(s.nombre) }}</p>
          </div>
          <div class="space-y-3 p-5">
            <div>
              <div class="flex justify-between text-sm"><span class="text-[var(--texto-2)]">Gerente</span><strong>{{ s.gerente_completas }} / {{ s.gerente_exigibles }}</strong></div>
              <Barra class="mt-1.5" :parte="s.gerente_completas" :total="s.gerente_exigibles" color="var(--texto)" />
            </div>
            <div>
              <div class="flex justify-between text-sm"><span class="text-[var(--texto-2)]">Ama de llaves</span><strong>{{ s.ama_completas }} / {{ s.ama_exigibles }}</strong></div>
              <Barra class="mt-1.5" :parte="s.ama_completas" :total="s.ama_exigibles" color="#fe7877" />
            </div>
            <div class="divisor flex justify-between pt-3 text-sm">
              <span><strong class="text-[var(--vino-texto)]">{{ s.abiertas }}</strong> folios abiertos</span>
              <span class="text-[var(--texto-3)]">Último chequeo {{ s.ultimo_chequeo ? cuando(s.ultimo_chequeo) : '—' }}</span>
            </div>
          </div>
        </RouterLink>
      </div>

      <!-- La misma información como tabla, para escritorio -->
      <div class="tarjeta mt-10 hidden overflow-hidden md:block">
        <table class="w-full text-left text-[15px]">
          <thead class="bg-[var(--carbon)] text-[#f5f7fa]">
            <tr>
              <th class="etiqueta px-5 py-4 !text-[#f5f7fa]/80">Sucursal</th>
              <th class="etiqueta px-5 py-4 !text-[#f5f7fa]/80">Gerente¹</th>
              <th class="etiqueta px-5 py-4 !text-[#f5f7fa]/80">Ama de llaves¹</th>
              <th class="etiqueta px-5 py-4 !text-[#f5f7fa]/80">Abiertas²</th>
              <th class="etiqueta px-5 py-4 !text-[#f5f7fa]/80">No rentar³</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in datos.sucursales" :key="s.sucursal_id" :class="i % 2 ? '' : 'bg-[var(--superficie-2)]'">
              <td class="px-5 py-3.5">{{ s.nombre }}</td>
              <td class="px-5 py-3.5">{{ s.gerente_completas }} / {{ s.gerente_exigibles }}</td>
              <td class="px-5 py-3.5">{{ s.ama_completas }} / {{ s.ama_exigibles }}</td>
              <td class="px-5 py-3.5">{{ s.abiertas }}</td>
              <td class="px-5 py-3.5">{{ s.no_rentar }}</td>
            </tr>
            <tr class="divisor font-bold">
              <td class="px-5 py-3.5">TOTAL</td>
              <td class="px-5 py-3.5">{{ totales.gerente[0] }} / {{ totales.gerente[1] }}</td>
              <td class="px-5 py-3.5">{{ totales.ama[0] }} / {{ totales.ama[1] }}</td>
              <td class="px-5 py-3.5">{{ datos.abiertas }}</td>
              <td class="px-5 py-3.5">{{ datos.bloqueados }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="mt-4 max-w-3xl text-[13px] leading-relaxed text-[var(--texto-3)]">
        ¹ Revisiones completas / exigibles del periodo, por puesto. Completa no significa sin fallas.
        ² Folios abiertos, incluidos los que están en atención. ³ Habitaciones con decisión vigente de no rentarse.
      </p>
      <RouterLink to="/folios" class="boton boton-vino mt-6 w-full sm:hidden">Ver incidencias</RouterLink>
    </div>
  </div>
</template>
