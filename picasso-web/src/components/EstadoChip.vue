<script setup>
import { computed } from 'vue'

import { ESTADOS_FOLIO, RESULTADO } from '@/lib/formato.js'

const props = defineProps({
  resultado: { type: String, default: null },
  folio: { type: String, default: null },
})
const info = computed(() =>
  props.resultado ? RESULTADO[props.resultado] : ESTADOS_FOLIO[props.folio] ?? { texto: props.folio, clase: 'estado-pendiente' },
)
</script>

<template>
  <span class="estado" :class="info.clase">{{ info.texto }}</span>
</template>
