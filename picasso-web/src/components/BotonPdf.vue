<script setup>
import { ref } from 'vue'
import { mdiFilePdfBox } from '@mdi/js'

import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { descargarPdf } from '@/services/picasso.js'

const props = defineProps({
  ruta: { type: String, required: true },
  nombre: { type: String, required: true },
  texto: { type: String, default: 'PDF' },
  claro: { type: Boolean, default: false },
})
const avisos = useToast()
const bajando = ref(false)

async function bajar() {
  bajando.value = true
  try {
    await descargarPdf(props.ruta, props.nombre)
    avisos.success('Reporte descargado.')
  } catch (e) {
    avisos.error(e.response ? 'No se pudo generar el reporte.' : 'Sin conexión: inténtalo con señal.')
  } finally {
    bajando.value = false
  }
}
</script>

<template>
  <button
    type="button"
    class="boton boton-chico"
    :class="claro ? 'border border-white/25 text-white' : 'boton-borde'"
    :disabled="bajando"
    @click="bajar"
  >
    <span v-if="bajando" class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
    <Icono v-else :path="mdiFilePdfBox" :size="18" />
    {{ bajando ? 'Generando…' : texto }}
  </button>
</template>
