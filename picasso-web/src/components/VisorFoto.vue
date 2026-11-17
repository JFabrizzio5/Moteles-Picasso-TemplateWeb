<script setup>
import { fechaHora, ROLES } from '@/lib/formato.js'

defineProps({ foto: { type: Object, required: true } })
const emit = defineEmits(['cerrar'])
const TIPOS = { punto: 'Evidencia del punto', avance: 'Avance', reparacion: 'Foto de reparación' }
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[60] flex flex-col bg-black/95" @click.self="emit('cerrar')">
      <div class="flex items-center justify-between p-4 text-white">
        <div>
          <p class="etiqueta !text-white/60">{{ TIPOS[foto.tipo] }} {{ foto.codigo_punto ? `· ${foto.codigo_punto}` : '' }}</p>
          <p class="text-sm">{{ foto.subida_por_nombre }} · {{ ROLES[foto.subida_por_rol] }} · {{ fechaHora(foto.creada_en) }}</p>
        </div>
        <button class="boton boton-chico bg-white/10 !px-4 text-white" @click="emit('cerrar')">Cerrar</button>
      </div>
      <div class="flex flex-1 items-center justify-center p-3" @click.self="emit('cerrar')">
        <img :src="foto.url" alt="Evidencia" class="max-h-full max-w-full rounded-xl object-contain" />
      </div>
      <p v-if="foto.nota" class="p-4 text-center text-sm text-white/80">{{ foto.nota }}</p>
    </div>
  </Teleport>
</template>
