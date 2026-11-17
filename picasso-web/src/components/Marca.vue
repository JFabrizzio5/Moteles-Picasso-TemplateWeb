<script setup>
// El logotipo oficial de Motel Picasso (tomado de motelpicasso.mx).
// Blanco sobre fondos oscuros (la barra, las fotos); negro sobre claros.
defineProps({
  claro: { type: Boolean, default: true },
  alto: { type: Number, default: 40 },
})
</script>

<template>
  <img
    :src="claro ? '/marca/picasso-logo-blanco.svg' : '/marca/picasso-logo-negro.svg'"
    alt="Motel Picasso"
    :style="{ height: `${alto}px`, width: 'auto' }"
    class="block select-none"
    draggable="false"
  />
</template>
