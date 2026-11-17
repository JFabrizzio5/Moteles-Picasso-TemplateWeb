<script setup>
defineProps({ texto: { type: String, default: 'Cargando' } })
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-20 text-[var(--texto-3)]">
    <span class="h-6 w-6 animate-spin rounded-full border-2 border-[var(--linea-fuerte)] border-t-[var(--vino)]" />
    <span class="etiqueta">{{ texto }}</span>
  </div>
</template>
