<script setup>
// Barra de avance que se llena al aparecer.
import { onMounted, ref } from 'vue'

const props = defineProps({
  parte: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  color: { type: String, default: 'var(--primario)' },
  alto: { type: Number, default: 6 },
})
const ancho = ref(0)
onMounted(() =>
  requestAnimationFrame(() => (ancho.value = props.total ? Math.min(100, (props.parte / props.total) * 100) : 0)),
)
</script>

<template>
  <div class="overflow-hidden rounded-full bg-[var(--linea)]" :style="{ height: `${alto}px` }">
    <div
      class="h-full rounded-full transition-[width] duration-[900ms] ease-[cubic-bezier(0.2,0.7,0.2,1)]"
      :style="{ width: `${ancho}%`, background: color }"
    />
  </div>
</template>
