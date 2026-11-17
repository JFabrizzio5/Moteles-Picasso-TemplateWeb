<script setup>
// Finanzas: ingresos (leídos de Kairos cada noche) contra gastos (capturados
// aquí, cosa por cosa), y la auditoría para la contadora.
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mdiDownload, mdiFileExcelOutline, mdiMagnify, mdiPlus, mdiRefresh } from '@mdi/js'

import BotonPdf from '@/components/BotonPdf.vue'
import Cargando from '@/components/Cargando.vue'
import GastoHoja from '@/components/GastoHoja.vue'
import Icono from '@/components/Icono.vue'
import Vacio from '@/components/Vacio.vue'
import { useToast } from '@/composables/useToast.js'
import { CATEGORIA_GASTO, CATEGORIAS_GASTO, corto, cuando, dia, FORMA_PAGO, mensajeError, pesos, ROLES } from '@/lib/formato.js'
import * as finanzas from '@/services/finanzas.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const perfil = usePerfilStore()
const ruta = useRoute()
const router = useRouter()
const avisos = useToast()

const VISTAS = [
  { valor: 'ingresos', texto: 'Ingresos' },
  { valor: 'gastos', texto: 'Gastos' },
  { valor: 'auditoria', texto: 'Auditoría' },
]
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
function periodoDe(clave) {
  const hoy = new Date()
  const ayer = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1)
  if (clave === 'ayer') return [iso(ayer), iso(ayer)]
  if (clave === '7') return [iso(new Date(ayer.getFullYear(), ayer.getMonth(), ayer.getDate() - 6)), iso(ayer)]
  if (clave === '30') return [iso(new Date(ayer.getFullYear(), ayer.getMonth(), ayer.getDate() - 29)), iso(ayer)]
  if (clave === 'pasado') return [iso(new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)), iso(new Date(hoy.getFullYear(), hoy.getMonth(), 0))]
  return [iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), iso(hoy)] // mes en curso
}
const PERIODOS = [
  { valor: 'ayer', texto: 'Ayer' },
  { valor: '7', texto: '7 días' },
  { valor: 'mes', texto: 'Este mes' },
  { valor: 'pasado', texto: 'Mes pasado' },
  { valor: '30', texto: '30 días' },
  { valor: 'rango', texto: 'Elegir fechas' },
]

const vista = computed(() => (VISTAS.some((v) => v.valor === ruta.query.vista) ? ruta.query.vista : 'ingresos'))
const periodo = computed(() => (PERIODOS.some((p) => p.valor === ruta.query.periodo) ? ruta.query.periodo : 'mes'))
const sucursal = computed(() => ruta.query.sucursal || '')
const rango = computed(() => {
  if (periodo.value !== 'rango') return periodoDe(periodo.value)
  const [d, h] = periodoDe('mes')
  const desde = ruta.query.desde || d
  const hasta = ruta.query.hasta || h
  return desde <= hasta ? [desde, hasta] : [hasta, desde]
})
const rutaPdf = computed(
  () => `/finanzas/reporte.pdf?desde=${rango.value[0]}&hasta=${rango.value[1]}${sucursal.value ? `&sucursal_id=${sucursal.value}` : ''}`,
)
const parametros = computed(() => ({ desde: rango.value[0], hasta: rango.value[1], sucursal_id: sucursal.value || undefined }))
const cambiar = (c) => router.replace({ query: { ...ruta.query, ...c } })

const cargando = ref(true)
const resumen = ref(null)
const dias = ref([])
const tarifas = ref([])
const lista = ref([])
const analisis = ref(null)
const buscar = ref('')
const categoria = ref('')
const sinFolio = ref(false)
const hoja = ref(null)
const exportando = ref(false)

async function cargar() {
  cargando.value = true
  const p = parametros.value
  try {
    if (vista.value === 'ingresos') {
      const [r, d, t] = await Promise.all([finanzas.resumen(p), finanzas.ingresos(p), finanzas.tarifas(p)])
      resumen.value = r
      dias.value = d
      tarifas.value = t
    } else if (vista.value === 'gastos') {
      lista.value = await finanzas.gastos({
        ...p,
        buscar: buscar.value || undefined,
        categoria: categoria.value || undefined,
        sin_incidencia: sinFolio.value || undefined,
      })
    } else {
      analisis.value = await finanzas.analisisGastos(p)
    }
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    cargando.value = false
  }
}

// Por día: si son todas las sucursales, se suman.
const porDia = computed(() => {
  const mapa = new Map()
  for (const d of dias.value) {
    const x = mapa.get(d.fecha) ?? { fecha: d.fecha, rentas: 0, habitaciones: 0, room_service: 0, extras: 0 }
    x.rentas += d.rentas
    x.habitaciones += Number(d.habitaciones)
    x.room_service += Number(d.room_service)
    x.extras += Number(d.extras)
    mapa.set(d.fecha, x)
  }
  return [...mapa.values()].sort((a, b) => b.fecha.localeCompare(a.fecha))
})
const maxDia = computed(() => Math.max(1, ...porDia.value.map((d) => d.habitaciones + d.room_service + d.extras)))
const totalGastos = computed(() => lista.value.reduce((s, g) => s + Number(g.importe), 0))
const pendientes = computed(() => lista.value.filter((g) => !g.exportado_en).length)
const conXml = computed(() => lista.value.some((g) => g.archivos.some((a) => a.tipo === 'xml')))

async function exportar(tipo, soloPendientes = false) {
  exportando.value = true
  const cuerpo = { ...parametros.value, solo_pendientes: soloPendientes }
  const etiqueta = `${rango.value[0]}_a_${rango.value[1]}`
  try {
    const n =
      tipo === 'xml'
        ? await finanzas.exportarXml(cuerpo, `Facturas-Picasso-${etiqueta}.zip`)
        : await finanzas.exportarEcont(cuerpo, `Gastos-Picasso-E-Cont-${etiqueta}.xlsx`)
    avisos.success(tipo === 'xml' ? `${n} XML listos para E-Cont.` : `${n} gastos en el Excel para E-Cont.`)
    if (tipo !== 'xml') cargar()
  } catch (e) {
    avisos.error((await finanzas.mensajeDeBlob(e)) || mensajeError(e))
  } finally {
    exportando.value = false
  }
}

async function releer() {
  const [desde, hasta] = periodoDe('ayer')
  try {
    await finanzas.importar({ desde, hasta, detalle: true })
    avisos.success('Se pidió volver a leer Kairos de ayer; tarda unos minutos.')
  } catch (e) {
    avisos.error(mensajeError(e))
  }
}

function guardado() {
  hoja.value = null
  cargar()
}

let espera = null
watch(buscar, () => {
  clearTimeout(espera)
  espera = setTimeout(cargar, 350)
})
watch([categoria, sinFolio], cargar)
watch(() => ruta.query, cargar)
onMounted(async () => {
  await perfil.cargar().catch(() => {})
  cargar()
})
</script>

<template>
  <div class="contenedor pt-8">
    <p class="etiqueta etiqueta-vino mb-3">Finanzas · {{ perfil.veTodas ? 'Seis sucursales' : corto(perfil.miSucursal?.nombre) }}</p>
    <h1 class="titulo-pagina">Lo que entra. <em>Lo que sale.</em></h1>
    <p class="subtitulo mt-3 max-w-2xl">
      Los ingresos llegan solos de Kairos cada noche. Los gastos se registran aquí, cosa por cosa, y se pasan a E-Cont con un archivo.
    </p>

    <div class="mt-7 space-y-3">
      <div class="sin-scroll -mx-4 flex gap-2 overflow-x-auto px-4">
        <button v-for="v in VISTAS" :key="v.valor" class="chip" :aria-pressed="vista === v.valor" @click="cambiar({ vista: v.valor })">{{ v.texto }}</button>
      </div>
      <div class="sin-scroll -mx-4 flex gap-2 overflow-x-auto px-4">
        <button v-for="p in PERIODOS" :key="p.valor" class="chip" :aria-pressed="periodo === p.valor" @click="cambiar({ periodo: p.valor })">{{ p.texto }}</button>
      </div>
      <select v-if="perfil.veTodas" class="campo sm:max-w-xs" :value="sucursal" @change="cambiar({ sucursal: $event.target.value || undefined })">
        <option value="">Todas las sucursales</option>
        <option v-for="s in perfil.sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
      <div v-if="periodo === 'rango'" class="grid max-w-md grid-cols-2 gap-2">
        <label class="text-sm font-semibold">Desde<input type="date" class="campo mt-1" :value="rango[0]" @change="cambiar({ desde: $event.target.value })" /></label>
        <label class="text-sm font-semibold">Hasta<input type="date" class="campo mt-1" :value="rango[1]" @change="cambiar({ hasta: $event.target.value })" /></label>
      </div>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p class="text-[13px] text-[var(--texto-3)]">Del {{ dia(rango[0]) }} al {{ dia(rango[1]) }}</p>
        <BotonPdf :ruta="rutaPdf" :nombre="`Finanzas-Picasso-${rango[0]}-a-${rango[1]}.pdf`" texto="Imprimir reporte" />
      </div>
    </div>

    <Cargando v-if="cargando && !resumen && !lista.length && !analisis" texto="Sumando" />

    <!-- INGRESOS -->
    <template v-if="vista === 'ingresos' && resumen">
      <div class="escalonado mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4" :class="cargando ? 'opacity-60' : ''">
        <div class="tarjeta p-5" style="--i: 0">
          <p class="etiqueta">Ingresos</p>
          <p class="serif mt-2 text-[34px] leading-none text-[var(--bien)] md:text-[42px]">{{ pesos(resumen.ingresos, true) }}</p>
          <p class="mt-1 text-[12.5px] text-[var(--texto-3)]">Cuartos, room service y extras</p>
        </div>
        <div class="tarjeta p-5" style="--i: 1">
          <p class="etiqueta">Rentas</p>
          <p class="serif mt-2 text-[34px] leading-none md:text-[42px]">{{ resumen.rentas.toLocaleString('es-MX') }}</p>
          <p class="mt-1 text-[12.5px] text-[var(--texto-3)]">De Kairos</p>
        </div>
        <div class="tarjeta p-5" style="--i: 2">
          <p class="etiqueta">Gastos</p>
          <p class="serif mt-2 text-[34px] leading-none text-[var(--vino-texto)] md:text-[42px]">{{ pesos(resumen.gastos, true) }}</p>
          <p class="mt-1 text-[12.5px] text-[var(--texto-3)]">Registrados en Picasso</p>
        </div>
        <div class="tarjeta p-5" style="--i: 3">
          <p class="etiqueta">Utilidad</p>
          <p class="serif mt-2 text-[34px] leading-none md:text-[42px]">{{ pesos(resumen.utilidad, true) }}</p>
          <p class="mt-1 text-[12.5px] text-[var(--texto-3)]">Ingresos menos gastos</p>
        </div>
      </div>

      <section v-if="resumen.sucursales.length > 1" class="tarjeta mt-4 overflow-x-auto">
        <table class="tabla-fin w-full min-w-[720px]">
          <thead>
            <tr><th class="izq">Sucursal</th><th>Rentas</th><th>Cuartos</th><th>Room service</th><th>Extras</th><th>Ingresos</th><th>Gastos</th><th>Utilidad</th><th class="izq">Kairos</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in resumen.sucursales" :key="s.sucursal_id" class="cursor-pointer" @click="cambiar({ sucursal: s.sucursal_id })">
              <td class="izq font-semibold">{{ corto(s.nombre) }}</td>
              <td>{{ s.rentas }}</td>
              <td>{{ pesos(s.habitaciones, true) }}</td>
              <td>{{ pesos(s.room_service, true) }}</td>
              <td>{{ pesos(s.extras, true) }}</td>
              <td class="font-semibold">{{ pesos(s.ingresos, true) }}</td>
              <td class="text-[var(--vino-texto)]">{{ pesos(s.gastos, true) }}</td>
              <td class="font-semibold">{{ pesos(s.utilidad, true) }}</td>
              <td class="izq text-[12px]">
                <span v-if="s.ultimo_error" class="text-[var(--falla)]" :title="s.ultimo_error">● Sin leer</span>
                <span v-else-if="s.ultimo_ok" class="text-[var(--bien)]">● {{ cuando(s.ultimo_ok) }}</span>
                <span v-else class="text-[var(--texto-3)]">● Pendiente</span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
      <p v-else-if="resumen.sucursales[0]?.ultimo_error" class="mt-3 text-[13px] text-[var(--falla)]">Kairos: {{ resumen.sucursales[0].ultimo_error }}</p>

      <div class="mt-4 grid gap-4 lg:grid-cols-[1fr_340px]">
        <section class="tarjeta p-5">
          <p class="etiqueta etiqueta-vino mb-3">Por día</p>
          <Vacio v-if="!porDia.length" titulo="Sin datos de Kairos" texto="Kairos se lee cada noche a las 4:30. Si es una sucursal nueva, el historial se va llenando noche a noche." />
          <ul v-else class="space-y-2">
            <li v-for="d in porDia" :key="d.fecha" class="grid grid-cols-[86px_1fr_auto] items-center gap-3 text-sm">
              <span class="text-[var(--texto-2)]">{{ dia(d.fecha) }}</span>
              <span class="h-2.5 overflow-hidden rounded-full bg-[var(--superficie-2)]">
                <span class="block h-full rounded-full bg-[var(--primario)]" :style="{ width: `${((d.habitaciones + d.room_service + d.extras) / maxDia) * 100}%` }" />
              </span>
              <span class="text-right tabular-nums"><strong>{{ pesos(d.habitaciones + d.room_service + d.extras, true) }}</strong> <span class="text-[var(--texto-3)]">· {{ d.rentas }}</span></span>
            </li>
          </ul>
        </section>
        <section class="tarjeta p-5">
          <p class="etiqueta etiqueta-vino mb-3">Por tarifa</p>
          <p v-if="!tarifas.length" class="text-sm text-[var(--texto-3)]">Sin rentas en el periodo.</p>
          <ul v-else class="divide-y divide-[var(--linea)] text-sm">
            <li v-for="t in tarifas" :key="t.tarifa" class="flex justify-between gap-3 py-2">
              <span>{{ t.tarifa }} <span class="text-[var(--texto-3)]">· {{ t.cantidad }}</span></span>
              <span class="font-semibold tabular-nums">{{ pesos(t.importe, true) }}</span>
            </li>
          </ul>
          <button v-if="perfil.veTodas" class="boton boton-suave boton-chico mt-4 w-full" @click="releer">
            <Icono :path="mdiRefresh" :size="18" /> Volver a leer ayer de Kairos
          </button>
        </section>
      </div>
    </template>

    <!-- GASTOS -->
    <template v-if="vista === 'gastos'">
      <div class="mt-6 flex flex-wrap items-center gap-2">
        <button class="boton boton-vino" @click="hoja = 'nuevo'"><Icono :path="mdiPlus" :size="20" /> Registrar gasto</button>
        <button class="boton boton-borde" :disabled="exportando || !lista.length" @click="exportar('excel')">
          <Icono :path="mdiFileExcelOutline" :size="20" /> Exportar a E-Cont
        </button>
        <button v-if="pendientes && pendientes < lista.length" class="boton boton-suave boton-chico" :disabled="exportando" @click="exportar('excel', true)">
          Solo los {{ pendientes }} sin exportar
        </button>
        <button v-if="conXml" class="boton boton-suave boton-chico" :disabled="exportando" @click="exportar('xml')">
          <Icono :path="mdiDownload" :size="18" /> XML de facturas
        </button>
      </div>
      <div class="mt-3 grid gap-2 sm:grid-cols-3">
        <div class="relative">
          <Icono :path="mdiMagnify" class="absolute top-1/2 left-4 -translate-y-1/2 text-[var(--texto-3)]" />
          <input v-model="buscar" class="campo pl-11" placeholder="Folio, concepto, proveedor" />
        </div>
        <select v-model="categoria" class="campo">
          <option value="">Todas las categorías</option>
          <option v-for="c in CATEGORIAS_GASTO" :key="c.valor" :value="c.valor">{{ c.texto }}</option>
        </select>
        <label class="flex items-center gap-2 text-sm"><input v-model="sinFolio" type="checkbox" class="h-5 w-5" /> Solo sin folio de incidencia</label>
      </div>
      <p v-if="!cargando" class="etiqueta mt-5 mb-3">{{ lista.length }} gastos · {{ pesos(totalGastos) }}</p>
      <Vacio v-if="!cargando && !lista.length" titulo="Sin gastos" texto="Registra el primero con el botón de arriba o desde un folio de incidencia." />
      <div class="escalonado grid gap-3 lg:grid-cols-2">
        <button v-for="(g, i) in lista" :key="g.id" class="tarjeta tarjeta-viva p-5 text-left" :style="{ '--i': Math.min(i, 14) }" @click="hoja = { gasto: g }">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="folio-codigo">{{ g.folio }}</p>
              <p class="mt-1 text-[17px] leading-snug font-bold">{{ g.concepto }}</p>
              <p class="mt-1 text-sm text-[var(--texto-2)]">{{ corto(g.sucursal_nombre) }} · {{ g.proveedor }} · {{ FORMA_PAGO[g.forma_pago] }}</p>
            </div>
            <p class="shrink-0 text-[18px] font-bold tabular-nums">{{ pesos(g.importe) }}</p>
          </div>
          <p class="mt-2 line-clamp-2 text-[13px] text-[var(--texto-2)]">{{ g.partidas.map((p) => `${p.descripcion} ×${Number(p.cantidad)} ${p.unidad}`).join(' · ') }}</p>
          <div class="mt-3 flex flex-wrap items-center gap-2 text-[12px]">
            <span class="estado estado-pendiente">{{ CATEGORIA_GASTO[g.categoria] }}</span>
            <span
              v-for="f in g.incidencias"
              :key="f.incidencia_id"
              class="estado estado-falla cursor-pointer hover:underline"
              :title="`Ir a ${f.folio}`"
              @click.stop="router.push(`/folios/${f.incidencia_id}`)"
            >{{ f.folio }} ↗</span>
            <span v-if="g.exportado_en" class="estado estado-bien">En E-Cont</span>
            <span v-if="g.archivos.length" class="text-[var(--texto-3)]">📎 {{ g.archivos.length }}</span>
            <span class="text-[var(--texto-3)]">{{ dia(g.fecha) }} · {{ g.capturo_nombre }}</span>
          </div>
        </button>
      </div>
    </template>

    <!-- AUDITORÍA -->
    <template v-if="vista === 'auditoria' && analisis">
      <div class="mt-6 grid grid-cols-2 gap-3" :class="cargando ? 'opacity-60' : ''">
        <div class="tarjeta p-5"><p class="etiqueta">Gastado</p><p class="serif mt-2 text-[36px] leading-none text-[var(--vino-texto)]">{{ pesos(analisis.total, true) }}</p></div>
        <div class="tarjeta p-5"><p class="etiqueta">Gastos registrados</p><p class="serif mt-2 text-[36px] leading-none">{{ analisis.gastos }}</p></div>
      </div>
      <Vacio v-if="!analisis.gastos" class="mt-4" titulo="Nada que auditar" texto="No hay gastos en este periodo." />
      <template v-else>
        <section class="tarjeta mt-4 overflow-x-auto p-5">
          <p class="etiqueta etiqueta-vino mb-3">Quién gasta más</p>
          <table class="tabla-fin w-full min-w-[560px]">
            <thead><tr><th class="izq">Persona</th><th class="izq">Sucursal</th><th>Gastos</th><th>Total</th><th class="izq">Gasta más en</th></tr></thead>
            <tbody>
              <tr v-for="p in analisis.por_persona" :key="p.capturo_nombre + p.sucursal_nombre">
                <td class="izq font-semibold">{{ p.capturo_nombre }} <span class="font-normal text-[var(--texto-3)]">· {{ ROLES[p.capturo_rol] }}</span></td>
                <td class="izq">{{ corto(p.sucursal_nombre) }}</td>
                <td>{{ p.gastos }}</td>
                <td class="font-semibold">{{ pesos(p.total) }}</td>
                <td class="izq">{{ CATEGORIA_GASTO[p.categoria_mayor] }}</td>
              </tr>
            </tbody>
          </table>
        </section>
        <section class="tarjeta mt-4 p-5">
          <p class="etiqueta etiqueta-vino mb-3">En qué se gasta</p>
          <ul class="space-y-3">
            <li v-for="c in analisis.por_categoria" :key="c.categoria">
              <div class="flex justify-between text-sm"><strong>{{ CATEGORIA_GASTO[c.categoria] }}</strong><span class="tabular-nums">{{ pesos(c.total) }} · {{ c.partidas }} partidas</span></div>
              <span class="mt-1 block h-2 overflow-hidden rounded-full bg-[var(--superficie-2)]"><span class="block h-full bg-[var(--vino)]" :style="{ width: `${(c.total / analisis.total) * 100}%` }" /></span>
              <p class="mt-1 text-[12px] text-[var(--texto-3)]">{{ Object.entries(c.por_sucursal).map(([s, t]) => `${corto(s)} ${pesos(t, true)}`).join(' · ') }}</p>
            </li>
          </ul>
        </section>
        <section class="tarjeta mt-4 overflow-x-auto p-5">
          <p class="etiqueta etiqueta-vino mb-1">Precio por artículo</p>
          <p class="mb-3 text-[12.5px] text-[var(--texto-3)]">El mismo artículo comprado a precios muy distintos se marca en rojo.</p>
          <table class="tabla-fin w-full min-w-[640px]">
            <thead><tr><th class="izq">Artículo</th><th>Veces</th><th>Cantidad</th><th>Total</th><th>Promedio</th><th>Mín · Máx</th><th class="izq">Dónde</th></tr></thead>
            <tbody>
              <tr v-for="a in analisis.por_articulo" :key="a.articulo + a.unidad">
                <td class="izq font-semibold">{{ a.articulo }} <span class="font-normal text-[var(--texto-3)]">· {{ CATEGORIA_GASTO[a.categoria] }}</span></td>
                <td>{{ a.veces }}</td>
                <td>{{ Number(a.cantidad).toLocaleString('es-MX') }} {{ a.unidad }}</td>
                <td>{{ pesos(a.total) }}</td>
                <td class="font-semibold">{{ pesos(a.precio_promedio) }}/{{ a.unidad }}</td>
                <td :class="Number(a.precio_maximo) > Number(a.precio_minimo) * 1.3 ? 'font-semibold text-[var(--falla)]' : ''">{{ pesos(a.precio_minimo) }} · {{ pesos(a.precio_maximo) }}</td>
                <td class="izq text-[12px]">{{ a.sucursales.map(corto).join(', ') }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>
    </template>

    <GastoHoja v-if="hoja === 'nuevo'" @cerrar="hoja = null" @guardado="guardado" />
    <GastoHoja v-else-if="hoja?.gasto" :gasto="hoja.gasto" @cerrar="hoja = null" @guardado="guardado" />
  </div>
</template>

<style scoped>
.tabla-fin {
  font-size: 13.5px;
  font-variant-numeric: tabular-nums;
}
.tabla-fin th {
  padding: 0 10px 8px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--texto-3);
  text-align: right;
  white-space: nowrap;
}
.tabla-fin td {
  padding: 9px 10px;
  border-top: 1px solid var(--linea);
  text-align: right;
  white-space: nowrap;
}
.tabla-fin .izq {
  text-align: left;
}
.tabla-fin tbody tr:hover td {
  background: var(--superficie-2);
}
</style>
