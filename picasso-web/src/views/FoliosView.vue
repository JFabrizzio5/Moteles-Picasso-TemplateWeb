<script setup>
// Listado de folios. Los filtros viven en la dirección (?estado=…&prioridad=…), así
// que al volver de un folio el listado queda como estaba.
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mdiMagnify } from '@mdi/js'

import Esqueleto from '@/components/Esqueleto.vue'
import EstadoChip from '@/components/EstadoChip.vue'
import Icono from '@/components/Icono.vue'
import Vacio from '@/components/Vacio.vue'
import { useToast } from '@/composables/useToast.js'
import { corto, fecha, hoyISO, mensajeError, pesos, PRIORIDAD, PRIORIDAD_LISTA, PRIORIDADES, relativo, ROLES } from '@/lib/formato.js'
import * as finanzas from '@/services/finanzas.js'
import * as picasso from '@/services/picasso.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const perfil = usePerfilStore()
const ruta = useRoute()
const router = useRouter()
const avisos = useToast()

const lista = ref([])
const cargando = ref(true)
const conteo = ref([])
// Lo gastado en cada folio (gastos ligados); la ama de llaves no lo ve.
const costos = ref(new Map())
const buscar = ref(ruta.query.buscar || '')

const ESTADOS = [
  { valor: 'abiertas', texto: 'Abiertas' },
  { valor: 'reportada', texto: 'Reportadas' },
  { valor: 'en_atencion', texto: 'En atención' },
  { valor: 'cerrada', texto: 'Cerradas' },
  { valor: 'todas', texto: 'Todas' },
]
// Columnas de la tabla «Estado por prioridad».
const COLUMNAS = [
  { valor: 'reportada', texto: 'Reportadas', estados: ['reportada'] },
  { valor: 'en_atencion', texto: 'En atención', estados: ['en_atencion'] },
  { valor: 'cerrada', texto: 'Cerradas', estados: ['cerrada'] },
  { valor: 'todas', texto: 'Todas', estados: null },
]
const PERIODOS = [
  { valor: '', texto: 'Cualquier fecha' },
  { valor: '0', texto: 'Hoy' },
  { valor: '1', texto: 'Ayer y hoy' },
  { valor: '6', texto: 'Últimos 7 días' },
  { valor: '29', texto: 'Últimos 30 días' },
  { valor: 'rango', texto: 'Fechas específicas…' },
]

const filtros = computed(() => ({
  estado: ruta.query.estado || 'abiertas',
  prioridad: PRIORIDAD[ruta.query.prioridad] ? ruta.query.prioridad : '',
  sucursal: ruta.query.sucursal || '',
  dias: ruta.query.dias ?? '',
  // Con «Fechas específicas»: del día `desde` al día `hasta` (reportados en ese rango).
  desde: ruta.query.desde || hoyISO(6),
  hasta: ruta.query.hasta || hoyISO(),
  buscar: ruta.query.buscar || '',
}))

// El conteo no depende del estado ni de la prioridad elegidos: es la tabla completa.
const filtrosConteo = computed(() => {
  const { sucursal, dias, desde, hasta, buscar } = filtros.value
  return { sucursal, dias, desde, hasta, buscar }
})

const LARGA = new Intl.DateTimeFormat('es-MX', { day: 'numeric', month: 'long', year: 'numeric' })
const aFecha = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}
const textoRango = computed(() => {
  const a = aFecha(filtros.value.desde)
  const b = aFecha(filtros.value.hasta)
  const n = Math.round((b - a) / 86400000) + 1
  return `Del ${LARGA.format(a)} al ${LARGA.format(b)} · ${n} ${n === 1 ? 'día' : 'días'}`
})

function cambiar(cambios) {
  router.replace({ query: { ...ruta.query, ...cambios } })
}

function parametros(f) {
  return {
    sucursal_id: f.sucursal || undefined,
    desde: f.dias === 'rango' ? f.desde : f.dias !== '' ? hoyISO(Number(f.dias)) : undefined,
    hasta: f.dias === 'rango' ? f.hasta : undefined,
    buscar: f.buscar || undefined,
  }
}

// Ya hubo una primera carga: las siguientes no tapan la lista con el esqueleto.
const listo = ref(false)
async function cargar() {
  if (ruta.name !== 'folios') return // la dirección cambió porque se fue a otra pantalla
  cargando.value = true
  const f = filtros.value
  try {
    lista.value = await picasso.folios({ ...parametros(f), estado: f.estado, prioridad: f.prioridad || undefined })
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    cargando.value = false
    listo.value = true
  }
}

async function cargarCostos() {
  if (perfil.esAma) return
  try {
    const filas = await finanzas.costosFolios({ sucursal_id: filtros.value.sucursal || undefined })
    costos.value = new Map(filas.map((c) => [c.incidencia_id, c]))
  } catch {
    costos.value = new Map()
  }
}

async function cargarConteo() {
  try {
    conteo.value = await picasso.conteoFolios(parametros(filtros.value))
  } catch {
    conteo.value = []
  }
}

/** Folios con esa prioridad (o todas) en esos estados (o todos). */
function cuantos(prioridad, estados) {
  return conteo.value
    .filter((c) => (!prioridad || c.prioridad === prioridad) && (!estados || estados.includes(c.estado)))
    .reduce((suma, c) => suma + c.total, 0)
}

const estadosElegidos = computed(() => {
  const e = filtros.value.estado
  if (e === 'todas') return null
  if (e === 'abiertas') return ['reportada', 'en_atencion']
  return [e]
})

const hayConteo = computed(() => conteo.value.length > 0)

/** La columna (o columnas, con «Abiertas») que corresponde al estado elegido. */
function columnaActiva(c) {
  const e = filtros.value.estado
  return e === c.valor || (e === 'abiertas' && ['reportada', 'en_atencion'].includes(c.valor))
}

let espera = null
watch(buscar, (v) => {
  clearTimeout(espera)
  espera = setTimeout(() => cambiar({ buscar: v || undefined }), 350)
})
watch(filtros, cargar)
watch(filtrosConteo, () => {
  if (ruta.name !== 'folios') return
  cargarConteo()
  cargarCostos()
})
onMounted(async () => {
  await perfil.cargar().catch(() => {})
  cargar()
  cargarConteo()
  cargarCostos()
})
let primera = true
onActivated(() => {
  if (primera) return (primera = false)
  cargar()
  cargarConteo()
  cargarCostos()
})
</script>

<template>
  <div class="contenedor pt-8">
    <p class="etiqueta etiqueta-vino mb-3">Folios · {{ perfil.veTodas ? 'Seis sucursales' : corto(perfil.miSucursal?.nombre) }}</p>
    <h1 class="titulo-pagina">Elegir un folio. <em>Ver su incidencia.</em></h1>
    <p class="subtitulo mt-3 max-w-2xl">Cada folio nace de una falla en el checklist y conserva su reporte, fotos, decisiones e historial.</p>

    <div class="mt-7 space-y-3">
      <div class="sin-scroll -mx-4 flex gap-2 overflow-x-auto px-4">
        <button
          v-for="e in ESTADOS"
          :key="e.valor"
          class="chip"
          :aria-pressed="filtros.estado === e.valor"
          @click="cambiar({ estado: e.valor })"
        >
          {{ e.texto }}
        </button>
      </div>
      <div class="sin-scroll -mx-4 flex gap-2 overflow-x-auto px-4" aria-label="Prioridad">
        <button class="chip" :aria-pressed="!filtros.prioridad" @click="cambiar({ prioridad: undefined })">Cualquier prioridad</button>
        <button
          v-for="p in PRIORIDAD_LISTA"
          :key="p.valor"
          class="chip"
          :aria-pressed="filtros.prioridad === p.valor"
          @click="cambiar({ prioridad: filtros.prioridad === p.valor ? undefined : p.valor })"
        >
          <span class="punto-prioridad" :style="{ background: p.color }" />
          {{ p.texto }}
          <span v-if="hayConteo" class="tabular-nums opacity-60">{{ cuantos(p.valor, estadosElegidos) }}</span>
        </button>
      </div>
      <div class="grid gap-2 sm:grid-cols-3">
        <div class="relative">
          <Icono :path="mdiMagnify" class="absolute top-1/2 left-4 -translate-y-1/2 text-[var(--texto-3)]" />
          <input v-model="buscar" class="campo pl-11" placeholder="Folio, problema o habitación" />
        </div>
        <select v-if="perfil.veTodas" class="campo" :value="filtros.sucursal" @change="cambiar({ sucursal: $event.target.value || undefined })">
          <option value="">Todas las sucursales</option>
          <option v-for="s in perfil.sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
        <select class="campo" :value="filtros.dias" @change="cambiar({ dias: $event.target.value || undefined, desde: undefined, hasta: undefined })">
          <option v-for="p in PERIODOS" :key="p.valor" :value="p.valor">{{ p.texto }}</option>
        </select>
      </div>
      <!-- Fechas específicas: dos calendarios y el rango escrito, para no adivinar. -->
      <div v-if="filtros.dias === 'rango'" class="tarjeta flex flex-wrap items-end gap-3 p-4">
        <label class="text-[13px] font-semibold text-[var(--texto-2)]">
          Reportados desde
          <input type="date" class="campo mt-1" :value="filtros.desde" :max="filtros.hasta" @change="$event.target.value && cambiar({ desde: $event.target.value })" />
        </label>
        <label class="text-[13px] font-semibold text-[var(--texto-2)]">
          Hasta
          <input type="date" class="campo mt-1" :value="filtros.hasta" :min="filtros.desde" :max="hoyISO()" @change="$event.target.value && cambiar({ hasta: $event.target.value })" />
        </label>
        <p class="pb-3 text-sm text-[var(--texto-2)]">{{ textoRango }}</p>
      </div>
    </div>

    <!-- Estado por prioridad: cada número filtra el listado. -->
    <section v-if="hayConteo" class="tarjeta mt-4 overflow-hidden">
      <div class="flex items-baseline justify-between gap-3 px-4 pt-4 pb-2 sm:px-5">
        <p class="etiqueta">Estado por prioridad</p>
        <p class="hidden text-[12.5px] text-[var(--texto-3)] sm:block">Toca un número para ver esos folios</p>
      </div>
      <table class="tabla-prioridad w-full text-left">
        <thead>
          <tr>
            <th class="w-[34%]"><span class="sr-only">Prioridad</span></th>
            <th
              v-for="c in COLUMNAS"
              :key="c.valor"
              :class="{ activa: columnaActiva(c) }"
            >
              {{ c.texto }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in PRIORIDAD_LISTA" :key="p.valor" :class="{ elegida: filtros.prioridad === p.valor }">
            <th>
              <button class="flex items-center gap-2" @click="cambiar({ prioridad: filtros.prioridad === p.valor ? undefined : p.valor })">
                <span class="punto-prioridad" :style="{ background: p.color }" />
                {{ p.texto }}
              </button>
            </th>
            <td v-for="c in COLUMNAS" :key="c.valor">
              <button
                class="celda"
                :class="{
                  vacia: !cuantos(p.valor, c.estados),
                  marcada: filtros.prioridad === p.valor && filtros.estado === c.valor,
                }"
                :style="{ '--color': p.color }"
                :aria-label="`${c.texto} con prioridad ${p.texto.toLowerCase()}`"
                @click="cambiar({ prioridad: p.valor, estado: c.valor })"
              >
                {{ cuantos(p.valor, c.estados) }}
              </button>
            </td>
          </tr>
          <tr class="total">
            <th>Total</th>
            <td v-for="c in COLUMNAS" :key="c.valor">
              <button class="celda" :class="{ vacia: !cuantos(null, c.estados) }" @click="cambiar({ prioridad: undefined, estado: c.valor })">
                {{ cuantos(null, c.estados) }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <p v-if="listo" class="etiqueta mt-6 mb-3">
      {{ lista.length }} {{ lista.length === 1 ? 'folio' : 'folios' }}
      <template v-if="filtros.prioridad"> · prioridad {{ PRIORIDAD[filtros.prioridad].texto.toLowerCase() }}</template>
    </p>
    <Esqueleto v-if="!listo" tipo="tarjetas" :n="6" />
    <Vacio
      v-else-if="!lista.length && !cargando"
      titulo="Sin folios"
      :texto="filtros.prioridad ? 'No hay incidencias con esta prioridad y estos filtros.' : 'No hay incidencias con estos filtros. Prueba con «Todas».'"
    />

    <div v-else class="escalonado grid gap-3 transition-opacity lg:grid-cols-2" :class="cargando ? 'opacity-60' : ''">
      <RouterLink
        v-for="(f, i) in lista"
        :key="f.id"
        :to="`/folios/${f.id}`"
        class="tarjeta tarjeta-viva franja-prioridad flex items-start justify-between gap-4 p-5"
        :style="{ '--i': Math.min(i, 14), '--color': PRIORIDAD[f.prioridad]?.color }"
      >
        <div class="min-w-0">
          <p class="folio-codigo">{{ f.folio }}</p>
          <p class="mt-1.5 text-[18px] leading-snug font-bold">{{ f.titulo }}</p>
          <p class="mt-1 text-sm text-[var(--texto-2)]">
            {{ f.sucursal_nombre }} · Hab. {{ f.habitacion_numero }} ·
            <span class="font-semibold" :style="{ color: PRIORIDAD[f.prioridad]?.color }">{{ PRIORIDADES[f.prioridad] }}</span>
          </p>
          <p v-if="costos.get(f.id)" class="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[var(--vino-suave)] px-2.5 py-0.5 text-[12.5px] font-semibold text-[var(--vino-texto)]">
            Gastado {{ pesos(costos.get(f.id).total) }} · {{ costos.get(f.id).gastos }} {{ costos.get(f.id).gastos === 1 ? 'gasto' : 'gastos' }}
          </p>
          <p class="mt-2 text-[13px] text-[var(--texto-3)]">
            {{ ROLES[f.origen_rol] }} · {{ fecha(f.reportada_en) }} · {{ f.estado === 'cerrada' ? `cerrado ${relativo(f.cerrada_en)}` : relativo(f.reportada_en) }}
          </p>
        </div>
        <div class="flex shrink-0 flex-col items-end gap-3">
          <EstadoChip :folio="f.estado" />
          <span class="boton boton-chico boton-suave">Ver detalle</span>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.punto-prioridad {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border-radius: 999px;
}
.chip[aria-pressed='true'] .punto-prioridad {
  box-shadow: 0 0 0 2px var(--fondo);
}

.tabla-prioridad th,
.tabla-prioridad td {
  padding: 0;
  border-top: 1px solid var(--linea);
}
.tabla-prioridad thead th {
  border-top: 0;
  padding: 0 4px 8px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--texto-3);
  text-align: center;
  white-space: nowrap;
}
.tabla-prioridad thead th.activa {
  color: var(--texto);
}
.tabla-prioridad tbody th {
  padding: 0 0 0 16px;
  font-size: 14px;
  font-weight: 600;
}
.tabla-prioridad tbody th button {
  min-height: 46px;
  width: 100%;
}
.tabla-prioridad tr.elegida th,
.tabla-prioridad tr.elegida td {
  background: var(--superficie-2);
}
.tabla-prioridad tr.total th,
.tabla-prioridad tr.total td {
  background: var(--superficie-2);
  color: var(--texto-2);
}
.celda {
  display: block;
  width: 100%;
  min-height: 46px;
  font-size: 17px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: center;
  transition: background 0.15s;
}
.celda:hover {
  background: var(--superficie-3);
}
.celda.vacia {
  font-weight: 400;
  color: var(--texto-3);
}
.celda.marcada {
  background: var(--texto);
  color: var(--fondo);
}
@media (min-width: 640px) {
  .tabla-prioridad tbody th {
    padding-left: 20px;
  }
  .tabla-prioridad thead th {
    font-size: 12.5px;
  }
}

/* Franja del color de la prioridad a la izquierda de cada tarjeta. */
.franja-prioridad {
  position: relative;
  overflow: hidden;
}
.franja-prioridad::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--color, transparent);
}
</style>
