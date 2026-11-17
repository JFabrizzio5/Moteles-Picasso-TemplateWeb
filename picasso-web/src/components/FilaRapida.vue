<script setup>
// Un punto en la lista rápida: ✓ si está bien, ✗ si está mal, ··· para No aplica
// o una nota. Tocar el texto lo despliega completo.
import { computed, ref } from 'vue'
import { mdiCheckBold, mdiCloseThick, mdiDotsHorizontal } from '@mdi/js'

import Icono from '@/components/Icono.vue'

const props = defineProps({
  punto: { type: Object, required: true },
  soloLectura: { type: Boolean, default: false },
})
const emit = defineEmits(['bien', 'falla', 'mas'])

const abierto = ref(false)
const golpe = ref('')

const estado = computed(() => props.punto.resultado)
const fondo = computed(
  () =>
    ({
      falla: 'bg-[var(--falla-suave)]',
      no_aplica: 'opacity-70',
    })[estado.value] ?? '',
)

function tocar(tipo) {
  if (props.soloLectura) return
  golpe.value = tipo
  setTimeout(() => (golpe.value = ''), 340)
  emit(tipo)
}
</script>

<template>
  <div class="flex items-center gap-3 px-4 py-3 transition-colors duration-300" :class="fondo">
    <button type="button" class="min-w-0 flex-1 text-left" @click="abierto = !abierto">
      <p class="flex items-baseline gap-2">
        <span class="etiqueta shrink-0 !text-[11px]">{{ punto.codigo }}</span>
        <span class="line-clamp-2 text-[15.5px] leading-snug font-semibold" :class="estado === 'no_aplica' ? 'line-through decoration-[var(--texto-3)]' : ''">{{ punto.titulo }}</span>
      </p>
      <p class="mt-0.5 text-[13px] leading-snug text-[var(--texto-3)]" :class="abierto ? '' : 'line-clamp-1'">{{ punto.texto }}</p>
      <p v-if="estado === 'falla' && punto.observacion" class="mt-1 text-[13px] font-semibold leading-snug text-[var(--falla)]">
        {{ punto.observacion }}<span v-if="punto.folio" class="folio-codigo ml-2 !text-[11px]">{{ punto.folio }}</span>
      </p>
      <p v-else-if="estado === 'no_aplica'" class="mt-1 text-[12.5px] text-[var(--na)]">No aplica · {{ punto.motivo_no_aplica }}</p>
      <p v-else-if="punto.en_bloque" class="mt-1 text-[12px] text-[var(--texto-3)]">Bien en bloque</p>
      <p v-if="punto.evidencias.length" class="mt-1 text-[12px] text-[var(--texto-3)]">📷 {{ punto.evidencias.length }} {{ punto.evidencias.length === 1 ? 'foto' : 'fotos' }}</p>
    </button>

    <template v-if="estado !== 'no_aplica' || !soloLectura">
      <button
        type="button"
        :aria-pressed="estado === 'bien'"
        :aria-label="`${punto.codigo} bien`"
        :disabled="soloLectura"
        class="grid h-12 w-12 shrink-0 place-items-center rounded-full border-2 transition-all duration-200 active:scale-90"
        :class="[
          estado === 'bien' ? 'border-transparent bg-[var(--bien-solido)] text-white' : 'border-[var(--linea-fuerte)] text-[var(--texto-3)]',
          golpe === 'bien' ? 'pop' : '',
        ]"
        @click="tocar('bien')"
      >
        <Icono :path="mdiCheckBold" :size="22" />
      </button>
      <button
        type="button"
        :aria-pressed="estado === 'falla'"
        :aria-label="`${punto.codigo} mal`"
        :disabled="soloLectura"
        class="grid h-12 w-12 shrink-0 place-items-center rounded-full border-2 transition-all duration-200 active:scale-90"
        :class="[
          estado === 'falla' ? 'border-transparent bg-[var(--vino)] text-white' : 'border-[var(--linea-fuerte)] text-[var(--texto-3)]',
          golpe === 'falla' ? 'pop' : '',
        ]"
        @click="tocar('falla')"
      >
        <Icono :path="mdiCloseThick" :size="22" />
      </button>
    </template>
    <button
      v-if="!soloLectura"
      type="button"
      :aria-label="`Más opciones de ${punto.codigo}`"
      class="-mr-1 grid h-10 w-7 shrink-0 place-items-center text-[var(--texto-3)]"
      @click="emit('mas')"
    >
      <Icono :path="mdiDotsHorizontal" :size="20" />
    </button>
  </div>
</template>
