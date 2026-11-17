<script setup>
// Un número que cuenta desde cero al aparecer (y al cambiar), en medio segundo.
import { onMounted, ref, watch } from 'vue'

const props = defineProps({ valor: { type: Number, default: 0 }, duracion: { type: Number, default: 650 } })
const mostrado = ref(0)
const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function animar(desde, hasta) {
  if (quieto || desde === hasta) {
    mostrado.value = hasta
    return
  }
  const inicio = performance.now()
  const paso = (ahora) => {
    const t = Math.min(1, (ahora - inicio) / props.duracion)
    const suave = 1 - Math.pow(1 - t, 3)
    mostrado.value = Math.round(desde + (hasta - desde) * suave)
    if (t < 1) requestAnimationFrame(paso)
  }
  requestAnimationFrame(paso)
}
onMounted(() => animar(0, props.valor))
watch(
  () => props.valor,
  (nuevo, viejo) => animar(viejo ?? 0, nuevo),
)
</script>

<template>
  <span class="tabular-nums">{{ mostrado }}</span>
</template>
