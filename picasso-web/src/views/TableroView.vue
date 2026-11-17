<script setup>
// Inicio de gerente y ama de llaves. Arriba, "Tu siguiente paso": la app dice
// qué toca hacer y lo deja a un toque. Abajo, los cuartos con un estado en
// palabras simples (Por revisar, A medias, No rentar…), cada uno con su color.
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  mdiArrowRight,
  mdiBroom,
  mdiCheckDecagramOutline,
  mdiChevronRight,
  mdiClipboardCheckOutline,
  mdiClockOutline,
  mdiFileDocumentAlertOutline,
  mdiProgressClock,
} from '@mdi/js'

import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import Numero from '@/components/Numero.vue'
import Vacio from '@/components/Vacio.vue'
import { useToast } from '@/composables/useToast.js'
import { AMENIDADES, corto, cuando, fechaHora, mensajeError, relativo, ROLES } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const perfil = usePerfilStore()
const router = useRouter()
const avisos = useToast()

const cuartos = ref([])
const abiertos = ref([])
const cargando = ref(true)
const filtro = ref('todas')
const elegido = ref(null)
const abriendo = ref(false)

const sucursal = computed(() => perfil.miSucursal)
const esGerente = computed(() => perfil.esGerente)

const saludo = computed(() => {
  const h = new Date().getHours()
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches'
})
const hoyTexto = new Intl.DateTimeFormat('es-MX', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())

async function cargar(opc) {
  if (!opc?.silencioso) cargando.value = true
  try {
    await perfil.cargar()
    const [t, f] = await Promise.all([picasso.tablero(perfil.perfil.sucursal_id), picasso.folios({ estado: 'abiertas' })])
    cuartos.value = t
    abiertos.value = f
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)
let primera = true
onActivated(() => (primera ? (primera = false) : cargar({ silencioso: true })))

// -- estado de cada cuarto, en palabras ------------------------------------------

const ESTADOS = {
  bloqueado: { texto: 'No rentar', color: 'var(--vino)', fondo: 'var(--falla-suave)', tinta: 'var(--falla)' },
  medias: { texto: 'A medias', color: 'var(--na-solido)', fondo: 'var(--na-suave)', tinta: 'var(--na)' },
  enviado: { texto: 'Enviado por ama', color: '#fe7877', fondo: 'rgb(254 120 119 / 0.14)', tinta: '#d9443f' },
  revisar: { texto: 'Por revisar hoy', color: '#fe7877', fondo: 'rgb(254 120 119 / 0.14)', tinta: '#d9443f' },
  folio: { texto: 'Con folio', color: 'var(--vino)', fondo: 'var(--falla-suave)', tinta: 'var(--falla)' },
  listo: { texto: 'Al día', color: 'var(--bien-solido)', fondo: 'var(--bien-suave)', tinta: 'var(--bien)' },
  libre: { texto: 'Sin pendientes', color: 'var(--linea-fuerte)', fondo: 'var(--pendiente-suave)', tinta: 'var(--pendiente)' },
}

function estadoDe(c) {
  if (c.mi_revision_en_curso) return 'medias'
  if (c.renta && !c.renta.puede_rentarse) return 'bloqueado'
  if (esGerente.value && c.ama_enviada_sin_gerente) return 'enviado'
  if (esGerente.value && c.gerente_pendiente) return 'revisar'
  if (c.incidencias_abiertas) return 'folio'
  return esGerente.value ? 'listo' : 'libre'
}

const conteo = computed(() => {
  const n = (clave) => cuartos.value.filter((c) => estadoDe(c) === clave).length
  return {
    revisar: n('revisar') + n('enviado'),
    medias: n('medias'),
    enviado: n('enviado'),
    bloqueado: cuartos.value.filter((c) => c.renta && !c.renta.puede_rentarse).length,
    folios: cuartos.value.reduce((t, c) => t + c.incidencias_abiertas, 0),
  }
})

// -- el siguiente paso -------------------------------------------------------------

const paso = computed(() => {
  const lista = cuartos.value
  const mediasMia = lista.find((c) => c.mi_revision_en_curso)
  if (mediasMia) {
    return {
      icono: mdiProgressClock,
      titulo: `Tienes el ${mediasMia.numero} a medias`,
      texto: 'Lo que marcaste ya está guardado. Sigue donde te quedaste.',
      boton: `Seguir con el ${mediasMia.numero}`,
      accion: () => tocar(mediasMia),
    }
  }
  if (esGerente.value) {
    const enviados = lista.filter((c) => c.ama_enviada_sin_gerente)
    if (enviados.length) {
      return {
        icono: mdiBroom,
        titulo: `La ama de llaves envió ${enviados.length} ${enviados.length === 1 ? 'cuarto' : 'cuartos'}`,
        texto: `Revísalos tú: ${enviados.map((c) => c.numero).join(', ')}.`,
        boton: `Revisar el ${enviados[0].numero}`,
        accion: () => empezar(enviados[0]),
      }
    }
    const nuevos = abiertos.value.filter((f) => f.estado === 'reportada')
    if (nuevos.length) {
      return {
        icono: mdiFileDocumentAlertOutline,
        titulo: `${nuevos.length} ${nuevos.length === 1 ? 'folio nuevo' : 'folios nuevos'} sin atender`,
        texto: `${nuevos[0].titulo} en el ${nuevos[0].habitacion_numero}. Decide la renta y pon quién lo atiende.`,
        boton: `Abrir ${nuevos[0].folio}`,
        accion: () => router.push(`/folios/${nuevos[0].id}`),
      }
    }
    const pendientes = lista.filter((c) => c.gerente_pendiente)
    if (pendientes.length) {
      return {
        icono: mdiClipboardCheckOutline,
        titulo: `Te faltan ${pendientes.length} ${pendientes.length === 1 ? 'cuarto' : 'cuartos'} por revisar hoy`,
        texto: 'Toca un cuarto y sigue el checklist punto por punto.',
        boton: `Empezar con el ${pendientes[0].numero}`,
        accion: () => empezar(pendientes[0]),
      }
    }
    return { icono: mdiCheckDecagramOutline, titulo: 'Todo al día', texto: 'No hay cuartos ni folios pendientes por ahora.', listo: true }
  }
  return {
    icono: mdiBroom,
    titulo: '¿Terminaste de limpiar un cuarto?',
    texto: 'Tócalo abajo y revisa los 29 puntos. Al final lo envías al gerente.',
    listo: true,
  }
})

// -- filtros ------------------------------------------------------------------------

const filtros = computed(() => {
  const base = [{ valor: 'todas', texto: 'Todos', n: cuartos.value.length }]
  if (esGerente.value) base.push({ valor: 'revisar', texto: 'Por revisar', n: conteo.value.revisar })
  base.push({ valor: 'medias', texto: 'A medias', n: conteo.value.medias })
  base.push({ valor: 'folio', texto: 'Con folio', n: cuartos.value.filter((c) => c.incidencias_abiertas).length })
  base.push({ valor: 'bloqueado', texto: 'No rentar', n: conteo.value.bloqueado })
  return base
})
const visibles = computed(() =>
  cuartos.value.filter((c) => {
    const e = estadoDe(c)
    if (filtro.value === 'revisar') return e === 'revisar' || e === 'enviado'
    if (filtro.value === 'medias') return e === 'medias'
    if (filtro.value === 'folio') return c.incidencias_abiertas > 0
    if (filtro.value === 'bloqueado') return c.renta && !c.renta.puede_rentarse
    return true
  }),
)

function ultima(rev) {
  if (!rev) return 'sin revisión'
  if (rev.estado === 'en_curso') return `a medias · ${rev.revisados}/${rev.total}`
  return relativo(rev.completada_en)
}

async function empezar(cuarto) {
  abriendo.value = true
  try {
    const rev = await picasso.abrirRevision(cuarto.habitacion_id)
    router.push({ name: 'revision', params: { id: rev.id } })
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    abriendo.value = false
  }
}
function tocar(cuarto) {
  if (cuarto.mi_revision_en_curso) router.push({ name: 'revision', params: { id: cuarto.mi_revision_en_curso } })
  else elegido.value = cuarto
}
</script>

<template>
  <div>
    <!-- Portada de la sucursal -->
    <section class="relative overflow-hidden bg-black text-[#f5f7fa]">
      <img v-if="sucursal?.foto" :src="sucursal.foto" alt="" class="foto-cubierta absolute inset-0 scale-105 opacity-70" />
      <div class="velo absolute inset-0" />
      <div class="contenedor relative pt-10 pb-8 md:pt-16 md:pb-12">
        <p class="etiqueta aparecer !text-white/70">{{ ROLES[perfil.rol] }} · {{ hoyTexto }}</p>
        <h1 class="serif aparecer mt-2 text-[48px] leading-[0.95] md:text-[80px]" style="animation-delay: 60ms">
          Picasso <em class="!text-[#fe7877]">{{ corto(sucursal?.nombre) }}</em>
        </h1>
        <p class="aparecer mt-2 text-[15px] text-white/75" style="animation-delay: 120ms">{{ saludo }}, {{ perfil.perfil?.nombre?.split(' ')[0] }}.</p>
        <div class="escalonado mt-6 grid grid-cols-3 gap-2 sm:max-w-lg">
          <div class="rounded-[12px] bg-black/45 px-3 py-3 backdrop-blur" style="--i: 2">
            <p class="serif text-[34px] leading-none"><Numero :valor="esGerente ? conteo.revisar : conteo.medias" /></p>
            <p class="mt-1 text-[12px] leading-tight text-white/70">{{ esGerente ? 'por revisar hoy' : 'a medias' }}</p>
          </div>
          <div class="rounded-[12px] bg-black/45 px-3 py-3 backdrop-blur" style="--i: 3">
            <p class="serif text-[34px] leading-none"><Numero :valor="conteo.folios" /></p>
            <p class="mt-1 text-[12px] leading-tight text-white/70">folios abiertos</p>
          </div>
          <div class="rounded-[12px] bg-black/45 px-3 py-3 backdrop-blur" style="--i: 4">
            <p class="serif text-[34px] leading-none"><Numero :valor="conteo.bloqueado" /></p>
            <p class="mt-1 text-[12px] leading-tight text-white/70">sin rentar</p>
          </div>
        </div>
      </div>
    </section>

    <div class="contenedor pt-5">
      <!-- Tu siguiente paso -->
      <div v-if="cargando" class="esqueleto h-[132px]" />
      <section v-else class="bloque-negro aparecer relative overflow-hidden p-5 md:p-6">
        <div class="absolute -top-16 -right-10 h-44 w-44 rounded-full bg-[#fe7877]/20 blur-3xl" />
        <div class="relative flex items-start gap-4">
          <span class="grid h-11 w-11 shrink-0 place-items-center rounded-[12px]" :class="paso.listo ? 'bg-white/10 text-white' : 'bg-[#fe7877] text-black'">
            <Icono :path="paso.icono" :size="24" />
          </span>
          <div class="min-w-0 flex-1">
            <p class="etiqueta !text-[#fe7877]">Tu siguiente paso</p>
            <p class="serif mt-1 text-[28px] leading-[1.05]">{{ paso.titulo }}</p>
            <p class="mt-1.5 text-[14px] leading-snug text-white/70">{{ paso.texto }}</p>
          </div>
        </div>
        <button v-if="paso.boton" class="boton boton-primario latido relative mt-4 w-full" :disabled="abriendo" @click="paso.accion()">
          {{ abriendo ? 'Abriendo…' : paso.boton }} <Icono :path="mdiArrowRight" :size="18" />
        </button>
      </section>

      <!-- Folios abiertos (gerente) -->
      <section v-if="esGerente && abiertos.length" class="mt-8">
        <div class="mb-3 flex items-end justify-between">
          <p class="seccion">Folios abiertos</p>
          <RouterLink to="/folios" class="text-sm font-semibold text-[var(--vino-texto)]">Ver todos</RouterLink>
        </div>
        <div class="sin-scroll escalonado -mx-[18px] flex gap-3 overflow-x-auto px-[18px] pb-2">
          <RouterLink
            v-for="(f, i) in abiertos.slice(0, 8)"
            :key="f.id"
            :to="`/folios/${f.id}`"
            class="tarjeta tarjeta-viva min-w-[260px] overflow-hidden"
            :style="{ '--i': i }"
          >
            <div class="h-1" :class="f.estado === 'reportada' ? 'bg-[var(--vino)]' : 'bg-[var(--na-solido)]'" />
            <div class="p-4">
              <div class="flex items-center justify-between gap-2">
                <span class="folio-codigo">{{ f.folio }}</span>
                <span class="estado" :class="f.estado === 'reportada' ? 'estado-falla' : 'estado-na'">{{ f.estado === 'reportada' ? 'Nuevo' : 'En atención' }}</span>
              </div>
              <p class="mt-2 font-semibold leading-snug">{{ f.titulo }}</p>
              <p class="mt-1 text-sm text-[var(--texto-2)]">Cuarto {{ f.habitacion_numero }} · {{ relativo(f.reportada_en) }}</p>
            </div>
          </RouterLink>
        </div>
      </section>

      <!-- Cuartos -->
      <div class="mt-8 mb-3 flex items-end justify-between">
        <div>
          <p class="seccion">Cuartos</p>
          <p class="mt-1 text-[13px] text-[var(--texto-3)]">Toca un cuarto para revisarlo.</p>
        </div>
        <button class="text-sm font-semibold text-[var(--texto-2)]" @click="cargar">Actualizar</button>
      </div>

      <div class="sin-scroll -mx-[18px] mb-4 flex gap-2 overflow-x-auto px-[18px]">
        <button v-for="f in filtros" :key="f.valor" class="chip shrink-0" :aria-pressed="filtro === f.valor" @click="filtro = f.valor">
          {{ f.texto }} <span class="opacity-60">{{ f.n }}</span>
        </button>
      </div>

      <div v-if="cargando" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <div v-for="n in 6" :key="n" class="esqueleto h-[150px]" />
      </div>
      <Vacio v-else-if="!visibles.length" titulo="Nada por aquí" texto="Ningún cuarto coincide con este filtro." />

      <div v-else class="escalonado grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <button
          v-for="(c, i) in visibles"
          :key="c.habitacion_id"
          class="tarjeta tarjeta-viva relative flex flex-col overflow-hidden text-left"
          :style="{ '--i': Math.min(i, 12) }"
          @click="tocar(c)"
        >
          <span class="absolute inset-y-0 left-0 w-1" :style="{ background: ESTADOS[estadoDe(c)].color }" />
          <div class="flex flex-1 flex-col p-4 pl-5">
            <span class="serif text-[46px] leading-none">{{ c.numero }}</span>
            <span
              class="mt-2 inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold"
              :style="{ background: ESTADOS[estadoDe(c)].fondo, color: ESTADOS[estadoDe(c)].tinta }"
            >
              <span class="h-1.5 w-1.5 rounded-full bg-current" />
              {{ ESTADOS[estadoDe(c)].texto }}
            </span>
            <p class="etiqueta mt-3 !text-[10.5px]">{{ c.amenidades.map((a) => AMENIDADES[a]).join(' · ') || 'Sencilla' }}</p>
            <p v-if="c.equipo.length" class="mt-1 line-clamp-1 text-[12px] text-[var(--texto-3)]">
              {{ c.equipo.slice(0, 2).join(' · ') }}<template v-if="c.equipo.length > 2"> · +{{ c.equipo.length - 2 }}</template>
            </p>
            <div class="mt-2 text-[12.5px] leading-snug text-[var(--texto-2)]">
              <p class="flex items-center gap-1 font-semibold text-[var(--texto)]">
                <Icono :path="mdiClockOutline" :size="14" class="text-[var(--texto-3)]" />
                {{ c.ultimo_chequeo ? cuando(c.ultimo_chequeo.fecha) : 'Sin chequeo' }}
              </p>
              <p v-if="c.ultimo_chequeo" class="mt-0.5 truncate">
                {{ c.ultimo_chequeo.rol === 'gerente' ? 'Gerente' : 'Ama' }} · {{ c.ultimo_chequeo.responsable_nombre.split(' ')[0] }}
                <span v-if="c.ultimo_chequeo.fallas" class="font-semibold text-[var(--falla)]">· {{ c.ultimo_chequeo.fallas }} mal</span>
              </p>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- Al tocar un cuarto -->
    <Hoja v-if="elegido" :titulo="`Cuarto ${elegido.numero}`" :etiqueta="`Picasso ${corto(sucursal?.nombre)}`" @cerrar="elegido = null">
      <div class="space-y-3">
        <div class="tarjeta-plana divide-y divide-[var(--linea)] text-sm">
          <p class="flex justify-between gap-3 p-3.5">
            <span class="text-[var(--texto-3)]">Último chequeo</span>
            <span class="text-right font-semibold">{{ elegido.ultimo_chequeo ? `${cuando(elegido.ultimo_chequeo.fecha)} · ${elegido.ultimo_chequeo.responsable_nombre}` : 'Ninguno' }}</span>
          </p>
          <p class="flex justify-between gap-3 p-3.5">
            <span class="text-[var(--texto-3)]">Ama de llaves</span>
            <span class="text-right">{{ elegido.ama_llaves ? `${elegido.ama_llaves.responsable_nombre} · ${fechaHora(elegido.ama_llaves.completada_en || elegido.ama_llaves.iniciada_en)}` : 'Sin revisión' }}</span>
          </p>
          <p class="flex justify-between gap-3 p-3.5">
            <span class="text-[var(--texto-3)]">Gerente</span>
            <span class="text-right">{{ elegido.gerente ? `${elegido.gerente.responsable_nombre} · ${fechaHora(elegido.gerente.completada_en || elegido.gerente.iniciada_en)}` : 'Sin revisión' }}</span>
          </p>
          <p class="flex justify-between gap-3 p-3.5">
            <span class="text-[var(--texto-3)]">Renta</span>
            <span v-if="elegido.renta" class="text-right font-semibold" :class="elegido.renta.puede_rentarse ? 'text-[var(--bien)]' : 'text-[var(--vino-texto)]'">
              {{ elegido.renta.puede_rentarse ? 'Puede rentarse' : 'No puede rentarse' }}
            </span>
            <span v-else class="text-right">Sin decisión</span>
          </p>
        </div>
        <div v-if="elegido.equipo.length">
          <p class="mb-2 text-[13px] font-semibold text-[var(--texto-2)]">Tiene</p>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="e in elegido.equipo" :key="e" class="rounded-full bg-[var(--superficie-2)] px-3 py-1 text-[13px]">{{ e }}</span>
          </div>
        </div>
        <button class="boton boton-primario w-full" :disabled="abriendo" @click="empezar(elegido)">
          {{ abriendo ? 'Abriendo…' : `Revisar el cuarto ${elegido.numero}` }}
        </button>
        <RouterLink v-if="esGerente" :to="`/habitacion/${elegido.habitacion_id}`" class="boton boton-borde w-full">
          Expediente y renta <Icono :path="mdiChevronRight" />
        </RouterLink>
      </div>
    </Hoja>
  </div>
</template>
