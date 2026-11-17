<script setup>
import { ref } from 'vue'

import VisorFoto from '@/components/VisorFoto.vue'

defineProps({ fotos: { type: Array, default: () => [] }, chicas: { type: Boolean, default: false } })
const abierta = ref(null)
</script>

<template>
  <div v-if="fotos.length" class="flex flex-wrap gap-2">
    <button
      v-for="f in fotos"
      :key="f.id"
      class="overflow-hidden rounded-xl border border-[var(--linea)] bg-[var(--superficie-2)]"
      :class="chicas ? 'h-16 w-16' : 'h-24 w-24'"
      @click="abierta = f"
    >
      <img :src="f.url" alt="" loading="lazy" class="foto-cubierta" />
    </button>
    <VisorFoto v-if="abierta" :foto="abierta" @cerrar="abierta = null" />
  </div>
</template>
