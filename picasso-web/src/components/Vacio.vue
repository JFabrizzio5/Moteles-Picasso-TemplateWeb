<script setup>
defineProps({ titulo: { type: String, required: true }, texto: { type: String, default: '' } })
</script>

<template>
  <div class="tarjeta-plana px-6 py-12 text-center">
    <p class="serif text-3xl">{{ titulo }}</p>
    <p v-if="texto" class="subtitulo mx-auto mt-2 max-w-sm">{{ texto }}</p>
    <div class="mt-5 flex justify-center gap-2"><slot /></div>
  </div>
</template>
