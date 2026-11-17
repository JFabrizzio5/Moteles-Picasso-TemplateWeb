<script setup>
// "Tomar foto": abre la cámara trasera en el celular; en escritorio, el
// selector de archivos. La foto se comprime antes de emitirse.
import { ref } from 'vue'
import { mdiCameraOutline } from '@mdi/js'

import Icono from '@/components/Icono.vue'
import { comprimir } from '@/lib/fotos.js'

defineProps({ texto: { type: String, default: 'Tomar foto' }, ocupado: { type: Boolean, default: false } })
const emit = defineEmits(['foto', 'error'])
const entrada = ref(null)

async function elegida(e) {
  const archivo = e.target.files?.[0]
  e.target.value = ''
  if (!archivo) return
  try {
    emit('foto', await comprimir(archivo))
  } catch (err) {
    emit('error', err.message)
  }
}
</script>

<template>
  <button
    type="button"
    class="flex min-h-[52px] w-full items-center gap-3 rounded-[14px] bg-[var(--vino-suave)] px-4 font-semibold text-[var(--vino-texto)] transition active:scale-[0.99] disabled:opacity-50"
    :disabled="ocupado"
    @click="entrada.click()"
  >
    <Icono :path="mdiCameraOutline" :size="22" />
    <span>{{ ocupado ? 'Subiendo foto…' : texto }}</span>
    <input ref="entrada" type="file" accept="image/*" capture="environment" class="hidden" @change="elegida" />
  </button>
</template>
