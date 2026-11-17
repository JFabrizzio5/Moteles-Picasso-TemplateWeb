<script setup>
// El checklist, en su forma más simple: se toca SOLO lo que está mal (qué falla
// y la foto). Al terminar, todo lo que no se tocó queda Bien (marcado "en
// bloque") y la hora del chequeo queda registrada.
// Si la sucursal exige revisar punto por punto (interruptor en Ajustes), cada
// renglón trae ✓ y ✗.
// Cada toque se guarda al momento; sin señal, queda en una cola del teléfono.
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mdiCheckCircle, mdiClockOutline, mdiClose } from '@mdi/js'

import BotonFoto from '@/components/BotonFoto.vue'
import BotonPdf from '@/components/BotonPdf.vue'
import Esqueleto from '@/components/Esqueleto.vue'
import FilaMal from '@/components/FilaMal.vue'
import FilaRapida from '@/components/FilaRapida.vue'
import Galeria from '@/components/Galeria.vue'
import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { corto, cuando, fechaHora, mensajeError, ROLES } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const ruta = useRoute()
const router = useRouter()
const avisos = useToast()
const perfil = usePerfilStore()

const rev = ref(null)
const cargando = ref(true)
const fin = ref(false)
const subiendo = reactive({})
const sinSubir = ref(0)
const terminando = ref(false)
const confirmar = ref(false)
const renta = reactive({ ver: false, puede: null, motivo: '', folio: null, enviando: false })
const falla = reactive({ codigo: null, observacion: '', verNoAplica: false, motivo: '' })

const id = computed(() => Number(ruta.params.id))
const CLAVE_COLA = computed(() => `picasso:cola:${id.value}`)

const puntos = computed(() => rev.value?.puntos ?? [])
const soloLectura = computed(() => rev.value?.estado === 'completa')
const esGerente = computed(() => rev.value?.rol === 'gerente')
const soloMal = computed(() => perfil.sucursal(rev.value?.sucursal_id)?.permite_bien_en_bloque ?? true)
// Los que el sistema marcó No aplica (el cuarto no tiene jacuzzi, etc.) no se enseñan.
const visibles = computed(() => puntos.value.filter((p) => !(p.automatico && p.resultado === 'no_aplica')))
const automaticos = computed(() => puntos.value.filter((p) => p.automatico && p.resultado === 'no_aplica'))
const pendientes = computed(() => puntos.value.filter((p) => p.resultado === 'sin_revisar'))
const fallas = computed(() => puntos.value.filter((p) => p.resultado === 'falla'))
const cuenta = computed(() => ({
  bien: puntos.value.filter((p) => p.resultado === 'bien').length,
  falla: fallas.value.length,
  na: puntos.value.filter((p) => p.resultado === 'no_aplica').length,
}))
const secciones = computed(() => {
  const grupos = []
  for (const p of visibles.value) {
    let g = grupos.find((x) => x.nombre === p.seccion)
    if (!g) grupos.push((g = { nombre: p.seccion, puntos: [] }))
    g.puntos.push(p)
  }
  return grupos
})
const puntoFalla = computed(() => puntos.value.find((p) => p.codigo === falla.codigo))

// -- carga ----------------------------------------------------------------------------

async function cargar() {
  try {
    const [r] = await Promise.all([picasso.revision(id.value), perfil.cargar().catch(() => null)])
    rev.value = r
    fin.value = r.estado === 'completa'
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    cargando.value = false
  }
}

// -- cola sin conexión --------------------------------------------------------------------

function leerCola() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_COLA.value)) || {}
  } catch {
    return {}
  }
}
function escribirCola(cola) {
  sinSubir.value = Object.keys(cola).length
  try {
    if (sinSubir.value) localStorage.setItem(CLAVE_COLA.value, JSON.stringify(cola))
    else localStorage.removeItem(CLAVE_COLA.value)
  } catch {
    /* sin almacenamiento: la cola vive solo en esta pestaña */
  }
}
function reemplazar(punto) {
  const i = rev.value.puntos.findIndex((p) => p.codigo === punto.codigo)
  if (i >= 0) rev.value.puntos[i] = punto
}
async function enviar(codigo, cuerpo, anterior) {
  try {
    const nuevo = await picasso.guardarPunto(id.value, codigo, cuerpo)
    reemplazar(nuevo)
    const cola = leerCola()
    delete cola[codigo]
    escribirCola(cola)
    if (cuerpo.resultado === 'falla' && nuevo.folio && !anterior?.folio) avisos.success(`Folio ${nuevo.folio} abierto.`)
  } catch (e) {
    if (!e.response) {
      const cola = leerCola()
      cola[codigo] = cuerpo
      escribirCola(cola)
    } else {
      if (anterior) reemplazar(anterior)
      avisos.error(mensajeError(e))
    }
  }
}
function guardarPunto(codigo, cuerpo) {
  const anterior = puntos.value.find((p) => p.codigo === codigo)
  reemplazar({ ...anterior, ...cuerpo, motivo_no_aplica: cuerpo.motivo_no_aplica ?? null, en_bloque: false })
  return enviar(codigo, cuerpo, anterior)
}
async function vaciarCola() {
  const cola = leerCola()
  sinSubir.value = Object.keys(cola).length
  for (const [codigo, cuerpo] of Object.entries(cola)) await enviar(codigo, cuerpo, null)
}
async function foto(codigo, archivo) {
  subiendo[codigo] = true
  try {
    const evidencia = await picasso.fotoDePunto(id.value, codigo, archivo)
    const p = rev.value.puntos.find((x) => x.codigo === codigo)
    reemplazar({ ...p, evidencias: [...p.evidencias, evidencia] })
  } catch (e) {
    avisos.error(e.response ? mensajeError(e) : 'Sin señal: toma la foto otra vez cuando haya conexión.')
  } finally {
    subiendo[codigo] = false
  }
}

let reintento = null
onMounted(async () => {
  await cargar()
  vaciarCola()
  window.addEventListener('online', vaciarCola)
  reintento = setInterval(() => Object.keys(leerCola()).length && vaciarCola(), 20000)
})
onBeforeUnmount(() => {
  window.removeEventListener('online', vaciarCola)
  clearInterval(reintento)
})

// -- marcar lo que está mal -----------------------------------------------------------

function abrir(p) {
  falla.codigo = p.codigo
  falla.observacion = p.resultado === 'falla' ? p.observacion || '' : ''
  falla.verNoAplica = false
  falla.motivo = ''
}
async function guardarFalla() {
  const codigo = falla.codigo
  falla.codigo = null
  await guardarPunto(codigo, { resultado: 'falla', observacion: falla.observacion.trim() })
}
async function quitarFalla() {
  const codigo = falla.codigo
  falla.codigo = null
  await guardarPunto(codigo, { resultado: 'sin_revisar' })
}
async function noAplica(motivo) {
  const codigo = falla.codigo
  falla.codigo = null
  await guardarPunto(codigo, { resultado: 'no_aplica', motivo_no_aplica: motivo })
}
function tocarBien(p) {
  guardarPunto(p.codigo, { resultado: p.resultado === 'bien' && !p.en_bloque ? 'sin_revisar' : 'bien' })
}

// -- terminar ---------------------------------------------------------------------------

/** Si no se marcó nada, se pregunta antes: "¿todo está bien con el cuarto?". */
function pedirTerminar() {
  if (soloMal.value && cuenta.value.falla === 0) confirmar.value = true
  else terminar()
}

async function terminar() {
  if (sinSubir.value) {
    avisos.error('Hay cambios sin subir por falta de señal. Espera a tener conexión.')
    return
  }
  terminando.value = true
  try {
    // Lo que no se tocó queda Bien (en bloque); después se cierra con su hora.
    confirmar.value = false
    if (pendientes.value.length) rev.value = await picasso.restoBien(id.value)
    const resumen = await picasso.completar(id.value)
    rev.value.estado = 'completa'
    rev.value.completada_en = resumen.completada_en
    fin.value = true
    window.scrollTo({ top: 0 })
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    terminando.value = false
  }
}

function abrirRenta(puede) {
  renta.puede = puede
  renta.motivo = puede
    ? fallas.value.length
      ? 'Las fallas no impiden la renta.'
      : 'Revisión sin fallas.'
    : fallas.value.map((f) => `${f.titulo}: ${f.observacion}`).join('; ').slice(0, 290)
  renta.folio = !puede && fallas.value[0]?.incidencia_id ? fallas.value[0].incidencia_id : null
  renta.ver = true
}
async function decidir() {
  renta.enviando = true
  try {
    rev.value.renta = await picasso.decidirRenta(rev.value.habitacion_id, {
      puede_rentarse: renta.puede,
      motivo: renta.motivo,
      incidencia_id: renta.folio,
    })
    renta.ver = false
    avisos.success('Decisión registrada.')
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    renta.enviando = false
  }
}

const MOTIVOS = ['No existe en esta habitación', 'La habitación estaba sucia', 'Fuera de servicio']
</script>

<template>
  <Esqueleto v-if="cargando" tipo="detalle" />
  <div v-else-if="rev" class="min-h-dvh">
    <!-- Encabezado -->
    <header class="vidrio sticky top-0 z-30 border-b border-[var(--linea)]" style="padding-top: env(safe-area-inset-top)">
      <div class="contenedor flex max-w-2xl items-center gap-3 py-3">
        <button class="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-[var(--linea-fuerte)]" aria-label="Salir" @click="router.push('/')">
          <Icono :path="mdiClose" />
        </button>
        <div class="min-w-0 flex-1">
          <p class="serif truncate text-[26px] leading-none">Cuarto {{ rev.habitacion_numero }} <em>· {{ corto(rev.sucursal_nombre) }}</em></p>
          <p class="mt-1 truncate text-[12.5px] text-[var(--texto-3)]">{{ ROLES[rev.rol] }} · {{ rev.responsable_nombre }}</p>
        </div>
        <span
          class="shrink-0 rounded-full px-3 py-1.5 text-[13px] font-bold"
          :class="cuenta.falla ? 'bg-[#e5372f] text-white' : 'bg-[var(--bien-suave)] text-[var(--bien)]'"
        >
          {{ cuenta.falla ? `✕ ${cuenta.falla} mal` : 'Todo bien' }}
        </span>
      </div>
    </header>

    <!-- Checklist -->
    <section v-if="!fin" class="contenedor max-w-2xl pt-5 pb-40">
      <!-- La hora del último chequeo de este cuarto -->
      <div class="tarjeta-plana mb-4 flex items-center gap-3 px-4 py-3">
        <Icono :path="mdiClockOutline" class="text-[var(--texto-3)]" />
        <p class="text-[14px] leading-snug">
          <template v-if="rev.ultimo_chequeo">
            Último chequeo: <strong>{{ cuando(rev.ultimo_chequeo.fecha) }}</strong>
            <span class="text-[var(--texto-3)]">
              · {{ rev.ultimo_chequeo.responsable_nombre }} ({{ ROLES[rev.ultimo_chequeo.rol].toLowerCase() }})
              <template v-if="rev.ultimo_chequeo.fallas"> · {{ rev.ultimo_chequeo.fallas }} mal</template>
            </span>
          </template>
          <template v-else>Primer chequeo de este cuarto.</template>
        </p>
      </div>

      <p class="mb-5 text-[15px] leading-snug text-[var(--texto-2)]">
        <template v-if="soloMal">Toca <strong class="text-[var(--texto)]">solo lo que está mal</strong>. Lo demás queda bien al terminar.</template>
        <template v-else>Marca cada punto con ✓ o ✗. Esta sucursal pide revisarlos uno por uno.</template>
      </p>

      <div v-for="s in secciones" :key="s.nombre" class="mb-5">
        <p class="seccion mb-2">{{ s.nombre }}</p>
        <div class="tarjeta divide-y divide-[var(--linea)] overflow-hidden">
          <template v-if="soloMal">
            <FilaMal v-for="p in s.puntos" :key="p.codigo" :punto="p" @tocar="abrir(p)" />
          </template>
          <template v-else>
            <FilaRapida
              v-for="p in s.puntos"
              :key="p.codigo"
              :punto="p"
              @bien="tocarBien(p)"
              @falla="abrir(p)"
              @mas="abrir(p)"
            />
          </template>
        </div>
      </div>
      <p v-if="automaticos.length" class="text-[13px] text-[var(--texto-3)]">
        No aplican a este cuarto: {{ automaticos.map((p) => p.titulo.toLowerCase()).join(', ') }}.
      </p>
    </section>

    <!-- Terminado -->
    <section v-else class="contenedor max-w-2xl pt-8 pb-16">
      <div class="aparecer flex items-center gap-3">
        <span class="pop grid h-12 w-12 place-items-center rounded-full bg-[var(--bien-solido)] text-white">
          <Icono :path="mdiCheckCircle" :size="28" />
        </span>
        <div>
          <p class="etiqueta">Chequeo registrado · {{ cuando(rev.completada_en) }}</p>
          <p class="serif text-[34px] leading-none" :class="cuenta.falla ? 'text-[#d92d24]' : 'text-[var(--bien)]'">
            {{ cuenta.falla ? `${cuenta.falla} ${cuenta.falla === 1 ? 'cosa mal' : 'cosas mal'}` : 'Todo bien' }}
          </p>
        </div>
      </div>
      <p class="mt-4 text-[15px] text-[var(--texto-2)]">
        {{ rev.responsable_nombre }} · {{ ROLES[rev.rol] }} ·
        <strong :class="cuenta.falla ? 'text-[var(--falla)]' : 'text-[var(--bien)]'">{{ cuenta.falla ? `${cuenta.falla} mal` : 'todo bien' }}</strong>
      </p>

      <div v-if="fallas.length" class="tarjeta mt-5 divide-y divide-[var(--linea)]">
        <RouterLink v-for="f in fallas" :key="f.codigo" :to="`/folios/${f.incidencia_id}`" class="flex items-center justify-between gap-3 px-4 py-3.5">
          <span class="min-w-0"><span class="block font-semibold">{{ f.titulo }}</span><span class="block truncate text-[13px] text-[var(--texto-3)]">{{ f.observacion }}</span></span>
          <span class="folio-codigo">{{ f.folio }}</span>
        </RouterLink>
      </div>

      <div v-if="esGerente" class="tarjeta mt-5 p-5">
        <p class="etiqueta etiqueta-vino">¿Este cuarto puede rentarse?</p>
        <p v-if="rev.renta" class="mt-2 text-[14px] text-[var(--texto-2)]">
          Vigente:
          <strong :class="rev.renta.puede_rentarse ? 'text-[var(--bien)]' : 'text-[var(--vino-texto)]'">{{ rev.renta.puede_rentarse ? 'puede rentarse' : 'no puede rentarse' }}</strong>
          · {{ fechaHora(rev.renta.decidida_en) }}
        </p>
        <div class="mt-4 grid grid-cols-2 gap-2">
          <button class="boton boton-borde boton-chico" @click="abrirRenta(true)">Sí, puede</button>
          <button class="boton boton-alerta boton-chico" @click="abrirRenta(false)">No rentar</button>
        </div>
      </div>
      <p v-else class="mt-5 rounded-[var(--radio)] border border-[var(--linea)] p-4 text-[14px] leading-relaxed text-[var(--texto-2)]">
        Ya está con el gerente: él decide si el cuarto puede rentarse.
      </p>

      <div class="mt-5 grid grid-cols-2 gap-2">
        <BotonPdf :ruta="`/reportes/revision/${rev.id}.pdf`" :nombre="`Revision-${rev.sucursal_clave}-${rev.habitacion_numero}.pdf`" texto="PDF" class="w-full" />
        <button class="boton boton-primario boton-chico w-full" @click="router.push('/')">Volver a cuartos</button>
      </div>
    </section>

    <!-- Terminar -->
    <nav v-if="!fin" class="vidrio fixed inset-x-0 bottom-0 z-30 border-t border-[var(--linea)]" style="padding-bottom: calc(env(safe-area-inset-bottom) + 10px)">
      <div class="contenedor max-w-2xl pt-2.5">
        <button
          class="boton w-full"
          :class="cuenta.falla ? 'boton-alerta' : 'boton-primario'"
          :disabled="terminando || (!soloMal && pendientes.length > 0)"
          @click="pedirTerminar"
        >
          <template v-if="terminando">Guardando…</template>
          <template v-else-if="!soloMal && pendientes.length">Faltan {{ pendientes.length }} por marcar</template>
          <template v-else>
            {{ esGerente ? 'Terminar' : 'Enviar al gerente' }} ·
            {{ cuenta.falla ? `${cuenta.falla} mal` : 'todo bien' }}
          </template>
        </button>
        <p v-if="sinSubir" class="mt-1.5 text-center text-[12px] text-[var(--na)]">{{ sinSubir }} sin subir por falta de señal; se suben solos.</p>
      </div>
    </nav>

    <!-- Sin nada marcado: confirmar que todo está bien -->
    <Hoja v-if="confirmar" titulo="¿Todo bien con el cuarto?" :etiqueta="`Cuarto ${rev.habitacion_numero}`" @cerrar="confirmar = false">
      <p class="text-[15.5px] leading-relaxed text-[var(--texto-2)]">
        No marcaste nada mal. ¿Confirmas que <strong class="text-[var(--texto)]">todo está bien</strong> con la habitación {{ rev.habitacion_numero }}?
      </p>
      <p class="mt-2 text-[13px] text-[var(--texto-3)]">Se registra como «todo bien» con la hora de este chequeo.</p>
      <button class="boton boton-primario mt-5 w-full" :disabled="terminando" @click="terminar">
        {{ terminando ? 'Guardando…' : 'Sí, todo está bien' }}
      </button>
      <button class="boton boton-borde boton-chico mt-2 w-full" @click="confirmar = false">No, voy a revisar otra vez</button>
    </Hoja>

    <!-- Qué está mal -->
    <Hoja v-if="puntoFalla" :titulo="puntoFalla.titulo" :etiqueta="`${puntoFalla.codigo} · ¿qué está mal?`" @cerrar="falla.codigo = null">
      <p class="mb-3 text-[14px] leading-snug text-[var(--texto-2)]">{{ puntoFalla.texto }}</p>
      <textarea v-model="falla.observacion" rows="3" class="campo" placeholder="Ej.: fuga al abrir la regadera" />
      <div class="mt-3"><BotonFoto texto="Tomar foto" :ocupado="!!subiendo[puntoFalla.codigo]" @foto="foto(puntoFalla.codigo, $event)" @error="avisos.error" /></div>
      <div v-if="puntoFalla.evidencias.length" class="mt-3"><Galeria :fotos="puntoFalla.evidencias" chicas /></div>
      <button class="boton boton-alerta mt-5 w-full" :disabled="falla.observacion.trim().length < 2" @click="guardarFalla">
        {{ puntoFalla.resultado === 'falla' ? 'Guardar' : 'Está mal' }}
      </button>
      <button v-if="puntoFalla.resultado === 'falla' || puntoFalla.resultado === 'no_aplica'" class="boton boton-borde boton-chico mt-2 w-full" @click="quitarFalla">
        Quitar (fue un error)
      </button>

      <button v-if="!falla.verNoAplica" class="mt-4 w-full text-center text-[13px] font-semibold text-[var(--texto-3)]" @click="falla.verNoAplica = true">
        Este punto no aplica en este cuarto
      </button>
      <div v-else class="mt-4">
        <p class="mb-2 text-sm font-semibold">No aplica porque…</p>
        <div class="flex flex-wrap gap-2">
          <button v-for="m in MOTIVOS" :key="m" class="chip" @click="noAplica(m)">{{ m }}</button>
        </div>
        <form class="mt-2 flex gap-2" @submit.prevent="falla.motivo.trim().length > 1 && noAplica(falla.motivo.trim())">
          <input v-model="falla.motivo" class="campo" placeholder="Otro motivo" />
          <button class="boton boton-carbon boton-chico shrink-0" :disabled="falla.motivo.trim().length < 2">Guardar</button>
        </form>
      </div>
    </Hoja>

    <Hoja v-if="renta.ver" :titulo="renta.puede ? 'Puede rentarse' : 'No puede rentarse'" :etiqueta="`Cuarto ${rev.habitacion_numero} · decisión del gerente`" @cerrar="renta.ver = false">
      <label class="mb-1.5 block text-sm font-semibold">Motivo</label>
      <textarea v-model="renta.motivo" rows="3" class="campo" maxlength="300" />
      <template v-if="!renta.puede && fallas.length">
        <label class="mt-4 mb-1.5 block text-sm font-semibold">Folio relacionado</label>
        <select v-model="renta.folio" class="campo">
          <option :value="null">Ninguno</option>
          <option v-for="f in fallas" :key="f.codigo" :value="f.incidencia_id">{{ f.folio }} · {{ f.titulo }}</option>
        </select>
      </template>
      <button class="boton mt-5 w-full" :class="renta.puede ? 'boton-primario' : 'boton-alerta'" :disabled="renta.enviando || renta.motivo.trim().length < 3" @click="decidir">
        {{ renta.enviando ? 'Guardando…' : 'Registrar decisión' }}
      </button>
    </Hoja>
  </div>
</template>
