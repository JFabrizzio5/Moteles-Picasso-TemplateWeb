<script setup>
// El expediente de un folio: reporte original, renta, atención, evidencias e
// historial. El gerente lo actualiza y lo cierra; los demás lo consultan.
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mdiArrowLeft, mdiCheckCircle, mdiCircleOutline } from '@mdi/js'

import BotonFoto from '@/components/BotonFoto.vue'
import BotonPdf from '@/components/BotonPdf.vue'
import Cargando from '@/components/Cargando.vue'
import EstadoChip from '@/components/EstadoChip.vue'
import Galeria from '@/components/Galeria.vue'
import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { fechaHora, mensajeError, PRIORIDADES, ROLES } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const ruta = useRoute()
const router = useRouter()
const avisos = useToast()
const perfil = usePerfilStore()

const f = ref(null)
const cargando = ref(true)
const pestana = ref('resumen')
const ocupado = ref(false)
const hoja = ref(null) // 'avance' | 'cerrar' | 'renta' | 'atencion'
const form = reactive({ nota: '', correccion: '', responsable: '', puede: true, motivo: '' })

const id = computed(() => Number(ruta.params.id))
const abierto = computed(() => ['reportada', 'en_atencion'].includes(f.value?.estado))
const gestiona = computed(() => perfil.esGerente && abierto.value)

async function cargar() {
  try {
    await perfil.cargar()
    f.value = await picasso.folio(id.value)
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

const fotos = computed(() => ({
  inicial: f.value?.evidencias.filter((e) => e.tipo === 'punto') ?? [],
  avance: f.value?.evidencias.filter((e) => e.tipo === 'avance') ?? [],
  reparacion: f.value?.evidencias.filter((e) => e.tipo === 'reparacion') ?? [],
}))

// Lo que le toca hacer al gerente ahora, en una sola tarjeta.
const siguiente = computed(() => {
  const x = f.value
  if (!x || !gestiona.value) return null
  if (!x.decisiones.length) {
    return { clave: 'renta', titulo: '¿El cuarto puede rentarse?', texto: 'Con esta falla, decide si se renta mientras se repara.' }
  }
  if (x.estado === 'reportada') {
    return { clave: 'atencion', titulo: 'Pon quién lo atiende', texto: 'Mantenimiento, un proveedor o quien lo vaya a reparar.' }
  }
  if (!fotos.value.reparacion.length) {
    return { clave: 'foto', titulo: 'Cuando quede reparado, toma la foto', texto: 'Compruébalo tú y toma al menos una foto de la reparación.' }
  }
  return { clave: 'cerrar', titulo: 'Ya puedes cerrar el folio', texto: 'Escribe qué se corrigió y ciérralo. Luego confirma la renta.' }
})

const pasos = computed(() => {
  const x = f.value
  if (!x) return []
  return [
    { texto: 'Detectar y registrar', hecho: true },
    { texto: 'Decidir si puede rentarse', hecho: x.decisiones.length > 0 },
    { texto: 'Atender la corrección', hecho: x.estado !== 'reportada' },
    { texto: 'Verificar y fotografiar', hecho: fotos.value.reparacion.length > 0 },
    { texto: 'Actualizar y cerrar', hecho: x.estado === 'cerrada' },
  ]
})

async function hacer(accion, exito) {
  ocupado.value = true
  try {
    const r = await accion()
    if (r && r.folio) f.value = r
    if (exito) avisos.success(exito)
    hoja.value = null
    return true
  } catch (e) {
    avisos.error(mensajeError(e))
    return false
  } finally {
    ocupado.value = false
  }
}

const prioridad = (valor) => hacer(() => picasso.actualizarFolio(id.value, { prioridad: valor }), 'Prioridad actualizada.')
const atender = () =>
  hacer(
    () => picasso.actualizarFolio(id.value, { responsable_atencion: form.responsable, en_atencion: true }),
    'El folio está en atención.',
  )
const anotar = async () => {
  if (await hacer(() => picasso.avance(id.value, form.nota), 'Avance anotado.')) form.nota = ''
}
async function fotoReparacion(archivo) {
  ocupado.value = true
  try {
    await picasso.fotoDeFolio(id.value, archivo, 'reparacion')
    f.value = await picasso.folio(id.value)
    avisos.success('Foto de reparación guardada.')
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    ocupado.value = false
  }
}
async function cerrar() {
  if (await hacer(() => picasso.cerrarFolio(id.value, form.correccion), 'Folio cerrado.')) {
    form.puede = true
    form.motivo = 'Reparación verificada.'
    hoja.value = 'renta'
  }
}
function abrirRenta(puede) {
  form.puede = puede
  form.motivo = puede ? 'Reparación verificada.' : `${f.value.titulo}: ${f.value.descripcion}`.slice(0, 290)
  hoja.value = 'renta'
}
async function decidir() {
  ocupado.value = true
  try {
    await picasso.decidirRenta(f.value.habitacion_id, { puede_rentarse: form.puede, motivo: form.motivo, incidencia_id: f.value.id })
    f.value = await picasso.folio(id.value)
    hoja.value = null
    avisos.success('Decisión registrada.')
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    ocupado.value = false
  }
}
</script>

<template>
  <Cargando v-if="cargando" texto="Abriendo folio" />
  <div v-else-if="f" class="contenedor max-w-5xl pt-6">
    <div class="flex items-center justify-between gap-3">
      <button class="boton boton-suave boton-chico" @click="router.back()"><Icono :path="mdiArrowLeft" :size="18" /> Folios</button>
      <div class="flex items-center gap-2">
        <span v-if="!perfil.esGerente" class="etiqueta hidden sm:inline">Solo lectura</span>
        <BotonPdf :ruta="`/reportes/incidencia/${f.id}.pdf`" :nombre="`${f.folio}.pdf`" texto="Descargar PDF" />
      </div>
    </div>

    <div class="mt-6 flex items-start justify-between gap-4">
      <p class="folio-codigo">{{ f.folio }}</p>
      <EstadoChip :folio="f.estado" />
    </div>
    <h1 class="titulo-pagina mt-2">{{ f.titulo }}</h1>
    <p class="subtitulo mt-2">
      {{ f.sucursal_nombre }} ·
      <RouterLink v-if="!perfil.esAma" :to="`/habitacion/${f.habitacion_id}`" class="underline decoration-[var(--linea-fuerte)] underline-offset-4">Hab. {{ f.habitacion_numero }}</RouterLink>
      <span v-else>Hab. {{ f.habitacion_numero }}</span>
      · {{ PRIORIDADES[f.prioridad] }} · {{ f.categoria }}
    </p>

    <!-- Lo que sigue (gerente) -->
    <section v-if="siguiente" class="bloque-negro aparecer relative mt-6 overflow-hidden p-5">
      <div class="absolute -top-16 -right-10 h-40 w-40 rounded-full bg-[#fe7877]/20 blur-3xl" />
      <p class="etiqueta relative !text-[#fe7877]">Siguiente paso</p>
      <p class="serif relative mt-1 text-[28px] leading-[1.05]">{{ siguiente.titulo }}</p>
      <p class="relative mt-1 text-[14px] text-white/70">{{ siguiente.texto }}</p>
      <div class="relative mt-4">
        <div v-if="siguiente.clave === 'renta'" class="grid grid-cols-2 gap-2">
          <button class="boton boton-chico border border-white/25 text-white" @click="abrirRenta(true)">Sí, puede</button>
          <button class="boton boton-primario boton-chico" @click="abrirRenta(false)">No rentar</button>
        </div>
        <button v-else-if="siguiente.clave === 'atencion'" class="boton boton-primario w-full" @click="form.responsable = f.responsable_atencion || 'Mantenimiento'; hoja = 'atencion'">
          Poner en atención
        </button>
        <BotonFoto v-else-if="siguiente.clave === 'foto'" texto="Tomar foto de reparación" :ocupado="ocupado" @foto="fotoReparacion" @error="avisos.error" />
        <button v-else class="boton boton-primario w-full" @click="hoja = 'cerrar'">Actualizar y cerrar</button>
      </div>
    </section>

    <!-- Los cinco pasos del seguimiento -->
    <ol class="sin-scroll -mx-4 mt-6 flex gap-2 overflow-x-auto px-4">
      <li
        v-for="(p, i) in pasos"
        :key="p.texto"
        class="flex shrink-0 items-center gap-2 rounded-full border px-3 py-2 text-[13px] font-semibold"
        :class="p.hecho ? 'border-transparent bg-[var(--bien-suave)] text-[var(--bien)]' : 'border-[var(--linea)] text-[var(--texto-3)]'"
      >
        <Icono :path="p.hecho ? mdiCheckCircle : mdiCircleOutline" :size="16" />
        {{ String(i + 1).padStart(2, '0') }} {{ p.texto }}
      </li>
    </ol>

    <div class="mt-6 flex gap-2">
      <button v-for="t in ['resumen', 'evidencias', 'historial']" :key="t" class="chip capitalize" :aria-pressed="pestana === t" @click="pestana = t">
        {{ t === 'resumen' ? 'Resumen' : t === 'evidencias' ? `Evidencias (${f.evidencias.length})` : 'Historial' }}
      </button>
    </div>

    <div class="mt-5 grid gap-4 lg:grid-cols-[1fr_360px]">
      <div class="space-y-4">
        <template v-if="pestana === 'resumen'">
          <div class="grid gap-4 md:grid-cols-2">
            <section class="tarjeta p-5">
              <p class="etiqueta etiqueta-vino">Reporte original</p>
              <p class="mt-3 text-[17px] font-bold">{{ f.descripcion }}</p>
              <p class="mt-3 text-sm leading-relaxed text-[var(--texto-2)]">
                Origen: {{ ROLES[f.origen_rol] }} · Checklist {{ f.codigo_punto }}<br />
                Reportó: {{ f.reporto_nombre }}<br />
                {{ fechaHora(f.reportada_en) }}
              </p>
            </section>
            <section class="tarjeta p-5">
              <p class="etiqueta etiqueta-vino">Decisión vigente de renta</p>
              <template v-if="f.renta_vigente">
                <p class="serif mt-3 text-[30px]" :class="f.renta_vigente.puede_rentarse ? 'text-[var(--bien)]' : 'text-[var(--vino-texto)]'">
                  {{ f.renta_vigente.puede_rentarse ? 'Puede rentarse' : 'No puede rentarse' }}
                </p>
                <p class="mt-2 text-sm leading-relaxed text-[var(--texto-2)]">
                  Motivo: {{ f.renta_vigente.motivo }}<br />
                  {{ f.renta_vigente.gerente_nombre }} · {{ fechaHora(f.renta_vigente.decidida_en) }}
                  <template v-if="f.decisiones.length > 1"><br />Anterior: {{ f.decisiones[1].puede_rentarse ? 'puede rentarse' : 'no rentarse' }} · {{ f.decisiones[1].motivo }}</template>
                </p>
              </template>
              <p v-else class="mt-3 text-sm text-[var(--texto-2)]">El gerente aún no registra una decisión para esta habitación.</p>
            </section>
          </div>
          <section class="tarjeta p-5">
            <p class="etiqueta etiqueta-vino">Atención y corrección</p>
            <p class="mt-3 text-[15px]">
              {{ f.responsable_atencion ? `Atiende: ${f.responsable_atencion}.` : 'Sin responsable asignado todavía.' }}
            </p>
            <p v-if="f.correccion" class="mt-2 text-[15px]">{{ f.correccion }}</p>
            <p v-if="f.cerrada_en" class="mt-3 text-sm text-[var(--texto-2)]">Verificó y cerró: {{ f.cerrada_por_nombre }} · {{ fechaHora(f.cerrada_en) }}</p>
          </section>
          <section class="tarjeta p-5">
            <p class="etiqueta etiqueta-vino">Evidencias del folio</p>
            <div class="mt-3 space-y-4">
              <div>
                <p class="mb-2 text-sm font-semibold">Foto inicial</p>
                <Galeria v-if="fotos.inicial.length" :fotos="fotos.inicial" />
                <p v-else class="text-sm text-[var(--texto-3)]">Se reportó sin foto.</p>
              </div>
              <div>
                <p class="mb-2 text-sm font-semibold">Foto del gerente (reparación)</p>
                <Galeria v-if="fotos.reparacion.length" :fotos="fotos.reparacion" />
                <p v-else class="text-sm text-[var(--texto-3)]">Aún no hay foto de la reparación.</p>
              </div>
            </div>
          </section>
        </template>

        <section v-else-if="pestana === 'evidencias'" class="tarjeta p-5">
          <p class="etiqueta etiqueta-vino mb-4">Todas las fotos</p>
          <Galeria v-if="f.evidencias.length" :fotos="f.evidencias" />
          <p v-else class="text-sm text-[var(--texto-3)]">Este folio no tiene fotos.</p>
        </section>

        <section v-else class="tarjeta p-5">
          <p class="etiqueta etiqueta-vino mb-4">Historial · quién hizo qué y cuándo</p>
          <ol class="relative space-y-5 border-l border-[var(--linea)] pl-5">
            <li v-for="(h, i) in f.historial" :key="i" class="relative">
              <span class="absolute top-1.5 -left-[25px] h-2.5 w-2.5 rounded-full bg-[var(--vino)]" />
              <p class="etiqueta">{{ fechaHora(h.fecha) }}</p>
              <p class="mt-1 text-[15px]"><strong>{{ h.actor_nombre }}</strong> <span class="text-[var(--texto-3)]">({{ ROLES[h.actor_rol] }})</span></p>
              <p class="text-[15px] text-[var(--texto-2)]">{{ h.detalle }}</p>
            </li>
          </ol>
        </section>
      </div>

      <!-- Acciones del gerente -->
      <aside v-if="gestiona" class="order-first space-y-3 lg:order-none lg:sticky lg:top-[80px] lg:self-start">
        <div class="tarjeta p-5">
          <p class="etiqueta etiqueta-vino">Dar seguimiento</p>
          <label class="mt-4 mb-1.5 block text-sm font-semibold">Prioridad</label>
          <div class="grid grid-cols-3 gap-1.5">
            <button
              v-for="p in ['alta', 'media', 'baja']"
              :key="p"
              class="h-10 rounded-[12px] border text-sm font-semibold capitalize"
              :class="f.prioridad === p ? 'border-[var(--carbon)] bg-[var(--carbon)] text-[var(--sobre-carbon)]' : 'border-[var(--linea)] text-[var(--texto-2)]'"
              :disabled="ocupado"
              @click="prioridad(p)"
            >
              {{ p }}
            </button>
          </div>
          <button v-if="f.estado === 'reportada'" class="boton boton-carbon mt-4 w-full" @click="form.responsable = f.responsable_atencion || 'Mantenimiento'; hoja = 'atencion'">
            Poner en atención
          </button>
          <button class="boton boton-borde mt-2 w-full" @click="hoja = 'avance'">Anotar avance</button>
          <div class="mt-2 grid grid-cols-2 gap-2">
            <button class="boton boton-borde boton-chico" @click="abrirRenta(true)">Puede rentarse</button>
            <button class="boton boton-chico bg-[var(--vino-suave)] text-[var(--vino-texto)]" @click="abrirRenta(false)">No rentar</button>
          </div>
        </div>
        <div class="tarjeta p-5">
          <p class="etiqueta etiqueta-vino">Al corregir la falla</p>
          <div class="mt-4"><BotonFoto texto="Tomar foto de reparación" :ocupado="ocupado" @foto="fotoReparacion" @error="avisos.error" /></div>
          <button class="boton boton-vino mt-3 w-full" :disabled="!f.puede_cerrar" @click="hoja = 'cerrar'">Actualizar y cerrar</button>
          <ul v-if="f.falta_para_cerrar.length" class="mt-3 space-y-1 text-[13px] text-[var(--texto-3)]">
            <li v-for="m in f.falta_para_cerrar" :key="m">· {{ m }}</li>
          </ul>
          <p class="mt-2 text-[12px] text-[var(--texto-3)]">Se habilita con foto del gerente y la descripción de la corrección.</p>
        </div>
      </aside>
    </div>

    <Hoja v-if="hoja === 'atencion'" titulo="Poner en atención" :etiqueta="f.folio" @cerrar="hoja = null">
      <label class="mb-1.5 block text-sm font-semibold">¿Quién atiende?</label>
      <input v-model="form.responsable" class="campo" placeholder="Mantenimiento, plomero, proveedor…" />
      <button class="boton boton-vino mt-5 w-full" :disabled="ocupado || !form.responsable.trim()" @click="atender">Guardar</button>
    </Hoja>
    <Hoja v-if="hoja === 'avance'" titulo="Anotar avance" :etiqueta="f.folio" @cerrar="hoja = null">
      <textarea v-model="form.nota" rows="3" class="campo" placeholder="Qué se hizo o qué falta" />
      <button class="boton boton-vino mt-5 w-full" :disabled="ocupado || form.nota.trim().length < 2" @click="anotar">Guardar avance</button>
    </Hoja>
    <Hoja v-if="hoja === 'cerrar'" titulo="Actualizar y cerrar" :etiqueta="f.folio" @cerrar="hoja = null">
      <p class="mb-4 text-sm text-[var(--texto-2)]">Comprobaste la corrección y ya hay foto de la reparación. Escribe qué se corrigió.</p>
      <textarea v-model="form.correccion" rows="4" class="campo" placeholder="Se sustituyó el sello y se verificó la operación del monomando." />
      <button class="boton boton-vino mt-5 w-full" :disabled="ocupado || form.correccion.trim().length < 5" @click="cerrar">Cerrar folio</button>
      <p class="mt-3 text-[12px] text-[var(--texto-3)]">Si la corrección no es satisfactoria, no cierres: el folio sigue abierto.</p>
    </Hoja>
    <Hoja v-if="hoja === 'renta'" :titulo="form.puede ? 'Puede rentarse' : 'No puede rentarse'" :etiqueta="`Hab. ${f.habitacion_numero} · decisión del gerente`" @cerrar="hoja = null">
      <div class="mb-4 grid grid-cols-2 gap-2">
        <button class="chip justify-center" :aria-pressed="form.puede" @click="form.puede = true">Puede rentarse</button>
        <button class="chip justify-center" :aria-pressed="!form.puede" @click="form.puede = false">No puede rentarse</button>
      </div>
      <label class="mb-1.5 block text-sm font-semibold">Motivo</label>
      <textarea v-model="form.motivo" rows="3" class="campo" maxlength="300" />
      <button class="boton boton-vino mt-5 w-full" :disabled="ocupado || form.motivo.trim().length < 3" @click="decidir">Registrar decisión</button>
    </Hoja>
  </div>
</template>
