<script setup>
// Un punto del checklist. Bien y Sin revisar se guardan con un toque; Falla
// pide la observación (abre el folio) y No aplica pide el motivo.
import { computed, nextTick, ref, watch } from 'vue'
import { mdiCheck, mdiCloudOffOutline } from '@mdi/js'

import BotonFoto from '@/components/BotonFoto.vue'
import Galeria from '@/components/Galeria.vue'
import Icono from '@/components/Icono.vue'
import { RESULTADOS } from '@/lib/formato.js'

const props = defineProps({
  punto: { type: Object, required: true },
  soloLectura: { type: Boolean, default: false },
  estadoGuardado: { type: String, default: '' }, // '', 'guardando', 'guardado', 'pendiente', 'error'
  subiendo: { type: Boolean, default: false },
})
const emit = defineEmits(['guardar', 'foto', 'error'])

const MOTIVOS = ['No existe en esta habitación', 'La habitación estaba sucia', 'Fuera de servicio por mantenimiento']

const elegido = ref(props.punto.resultado)
const observacion = ref(props.punto.observacion || '')
const motivo = ref(props.punto.motivo_no_aplica || '')
const nota = ref(false)
const caja = ref(null)

watch(
  () => props.punto,
  (p) => {
    elegido.value = p.resultado
    observacion.value = p.observacion || ''
    motivo.value = p.motivo_no_aplica || ''
  },
)

const sinGuardar = computed(
  () =>
    elegido.value !== props.punto.resultado ||
    (observacion.value || '') !== (props.punto.observacion || '') ||
    (elegido.value === 'no_aplica' && (motivo.value || '') !== (props.punto.motivo_no_aplica || '')),
)
const pideTexto = computed(() => elegido.value === 'falla' || elegido.value === 'no_aplica')
const listo = computed(() => {
  if (elegido.value === 'falla') return observacion.value.trim().length > 1
  if (elegido.value === 'no_aplica') return motivo.value.trim().length > 1
  return true
})
const mostrarNota = computed(() => elegido.value === 'falla' || nota.value || !!props.punto.observacion)

async function elegir(valor) {
  if (props.soloLectura) return
  elegido.value = valor
  if (valor === 'bien' || valor === 'sin_revisar') {
    emit('guardar', { resultado: valor, observacion: observacion.value || null })
  } else {
    await nextTick()
    caja.value?.focus()
  }
}

function guardar() {
  if (!listo.value) return
  emit('guardar', {
    resultado: elegido.value,
    observacion: observacion.value || null,
    motivo_no_aplica: elegido.value === 'no_aplica' ? motivo.value : null,
  })
}

function usarMotivo(m) {
  motivo.value = m
  guardar()
}

const clases = {
  bien: 'bg-[var(--bien)] text-white border-[var(--bien)]',
  falla: 'bg-[var(--vino)] text-white border-[var(--vino)]',
  no_aplica: 'bg-[var(--na)] text-white border-[var(--na)]',
  sin_revisar: 'bg-[var(--texto-2)] text-[var(--fondo)] border-[var(--texto-2)]',
}
</script>

<template>
  <article
    :id="`punto-${punto.codigo}`"
    class="tarjeta scroll-mt-[190px] p-4 sm:p-5"
    :class="punto.resultado === 'falla' ? '!border-[var(--vino)]/50' : ''"
  >
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="etiqueta etiqueta-vino">{{ punto.codigo }} · {{ punto.titulo }}</p>
        <p class="mt-1.5 text-[15px] leading-snug font-semibold">{{ punto.texto }}</p>
      </div>
      <span class="mt-0.5 shrink-0 text-[var(--texto-3)]" :title="estadoGuardado">
        <span v-if="estadoGuardado === 'guardando'" class="block h-4 w-4 animate-spin rounded-full border-2 border-[var(--linea-fuerte)] border-t-[var(--vino)]" />
        <Icono v-else-if="estadoGuardado === 'guardado'" :path="mdiCheck" :size="18" class="text-[var(--bien)]" />
        <Icono v-else-if="estadoGuardado === 'pendiente'" :path="mdiCloudOffOutline" :size="18" class="text-[var(--na)]" />
      </span>
    </header>

    <div class="mt-4 grid grid-cols-4 gap-1.5" role="radiogroup" :aria-label="`Resultado de ${punto.codigo}`">
      <button
        v-for="r in RESULTADOS"
        :key="r.valor"
        type="button"
        role="radio"
        :aria-checked="elegido === r.valor"
        :disabled="soloLectura"
        class="h-11 rounded-[12px] border px-1 text-[13px] font-semibold transition active:scale-[0.97] disabled:cursor-default"
        :class="elegido === r.valor ? clases[r.valor] : 'border-[var(--linea)] bg-[var(--superficie-2)] text-[var(--texto-2)]'"
        @click="elegir(r.valor)"
      >
        {{ r.texto }}
      </button>
    </div>

    <p v-if="punto.automatico && punto.resultado === 'no_aplica'" class="mt-3 text-[13px] text-[var(--texto-3)]">
      Marcado por el sistema: {{ punto.motivo_no_aplica }}
    </p>

    <!-- No aplica: el motivo -->
    <div v-if="elegido === 'no_aplica' && !punto.automatico" class="mt-4">
      <label class="mb-1.5 block text-sm font-semibold">Motivo</label>
      <div class="sin-scroll mb-2 flex gap-2 overflow-x-auto">
        <button v-for="m in MOTIVOS" :key="m" type="button" class="chip !h-8 !text-[13px]" :disabled="soloLectura" @click="usarMotivo(m)">
          {{ m }}
        </button>
      </div>
      <input ref="caja" v-model="motivo" class="campo" :readonly="soloLectura" placeholder="¿Por qué no corresponde?" @keyup.enter="guardar" />
    </div>

    <!-- Observación (obligatoria en Falla) y fotos -->
    <div v-if="mostrarNota && elegido !== 'no_aplica'" class="mt-4">
      <label class="mb-1.5 block text-sm font-semibold">
        Observación <span v-if="elegido === 'falla'" class="font-normal text-[var(--texto-3)]">· abre el folio</span>
      </label>
      <textarea
        ref="caja"
        v-model="observacion"
        rows="2"
        class="campo"
        :readonly="soloLectura"
        :placeholder="elegido === 'falla' ? 'Qué falla, dónde y desde cuándo' : 'Nota opcional'"
      />
    </div>

    <button
      v-if="!soloLectura && pideTexto && sinGuardar"
      type="button"
      class="boton boton-vino boton-chico mt-3 w-full"
      :disabled="!listo"
      @click="guardar"
    >
      {{ elegido === 'falla' ? (punto.folio ? 'Guardar observación' : 'Guardar falla y abrir folio') : 'Guardar motivo' }}
    </button>
    <button
      v-else-if="!soloLectura && elegido === 'bien' && sinGuardar && observacion"
      type="button"
      class="boton boton-carbon boton-chico mt-3 w-full"
      @click="guardar"
    >
      Guardar nota
    </button>

    <div v-if="!soloLectura && (elegido === 'falla' || mostrarNota)" class="mt-3">
      <BotonFoto
        :texto="elegido === 'falla' ? 'Tomar foto de la falla' : 'Agregar foto'"
        :ocupado="subiendo"
        @foto="emit('foto', $event)"
        @error="emit('error', $event)"
      />
    </div>

    <div v-if="punto.evidencias.length" class="mt-3">
      <Galeria :fotos="punto.evidencias" chicas />
    </div>

    <RouterLink
      v-if="punto.folio"
      :to="`/folios/${punto.incidencia_id}`"
      class="mt-3 flex min-h-[44px] items-center justify-center rounded-[12px] bg-[var(--vino-suave)] text-sm font-bold text-[var(--vino-texto)]"
    >
      Ver {{ punto.folio }}
    </RouterLink>

    <button
      v-if="!soloLectura && !mostrarNota && elegido !== 'no_aplica' && elegido !== 'falla'"
      type="button"
      class="mt-3 text-[13px] font-semibold text-[var(--texto-3)]"
      @click="nota = true"
    >
      + Nota o foto
    </button>
  </article>
</template>
