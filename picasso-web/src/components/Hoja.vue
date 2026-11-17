<script setup>
// Ventana que sube desde abajo en el celular y se centra en escritorio.
import { onBeforeUnmount, onMounted } from 'vue'

const props = defineProps({ titulo: { type: String, default: '' }, etiqueta: { type: String, default: '' } })
const emit = defineEmits(['cerrar'])

function tecla(e) {
  if (e.key === 'Escape') emit('cerrar')
}
onMounted(() => {
  document.addEventListener('keydown', tecla)
  document.body.style.overflow = 'hidden'
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', tecla)
  document.body.style.overflow = ''
})
void props
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true">
      <div class="velo-hoja absolute inset-0 bg-black/55 backdrop-blur-[3px]" @click="emit('cerrar')" />
      <div
        class="panel-hoja relative max-h-[92dvh] w-full overflow-y-auto rounded-t-[22px] bg-[var(--fondo)] p-5 pb-8 shadow-2xl sm:max-w-lg sm:rounded-[18px] sm:p-7"
        style="padding-bottom: calc(env(safe-area-inset-bottom) + 24px)"
      >
        <div class="mx-auto mb-4 h-1 w-10 rounded-full bg-[var(--linea-fuerte)] sm:hidden" />
        <div class="mb-5 flex items-start justify-between gap-4">
          <div>
            <p v-if="etiqueta" class="etiqueta etiqueta-vino mb-1">{{ etiqueta }}</p>
            <h2 class="serif text-[34px]">{{ titulo }}</h2>
          </div>
          <button class="boton boton-suave boton-chico !px-3" aria-label="Cerrar" @click="emit('cerrar')">✕</button>
        </div>
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.velo-hoja {
  animation: velo-entra 0.22s ease both;
}
.panel-hoja {
  animation: subir 0.34s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
</style>
