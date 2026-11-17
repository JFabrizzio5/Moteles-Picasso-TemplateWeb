<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import Avisos from '@/components/Avisos.vue'
import Marco from '@/layouts/Marco.vue'

const ruta = useRoute()
// Hasta que el enrutador resuelve la primera ruta no se sabe si es la entrada
// o una pantalla privada: sin esto el marco cargaba el perfil sin sesión (401).
const listo = computed(() => ruta.matched.length > 0)
const sinMarco = computed(() => ruta.meta?.public)
</script>

<template>
  <template v-if="listo">
    <RouterView v-if="sinMarco" />
    <Marco v-else />
  </template>
  <Avisos />
</template>
