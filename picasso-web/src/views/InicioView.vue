<script setup>
// Cada puesto entra a lo suyo: propietarios al panel; gerente y ama de llaves
// a las habitaciones de su sucursal.
import { onMounted, ref } from 'vue'

import Esqueleto from '@/components/Esqueleto.vue'
import Vacio from '@/components/Vacio.vue'
import { mensajeError } from '@/lib/formato.js'
import { usePerfilStore } from '@/stores/perfil.store.js'
import PanelView from '@/views/PanelView.vue'
import TableroView from '@/views/TableroView.vue'

const perfil = usePerfilStore()
const error = ref('')
onMounted(() => perfil.cargar().catch((e) => (error.value = mensajeError(e))))
</script>

<template>
  <div v-if="error" class="contenedor pt-10"><Vacio titulo="No se pudo cargar" :texto="error" /></div>
  <div v-else-if="!perfil.perfil" class="contenedor pt-6"><Esqueleto tipo="panel" /></div>
  <PanelView v-else-if="perfil.veTodas" />
  <TableroView v-else />
</template>
