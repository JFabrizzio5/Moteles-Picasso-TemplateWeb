<script setup>
// Código QR para abrir la app en el celular desde una pantalla grande.
// Apunta a la entrada del mismo sitio que se está viendo, así sirve igual en el
// VPS de prueba que en el dominio de Picasso. La librería se carga solo aquí.
import { onMounted, ref } from 'vue'

const props = defineProps({
  oscuro: { type: Boolean, default: false },
  ruta: { type: String, default: '/login' },
})

const url = `${window.location.origin}${props.ruta}`
const svg = ref('')

onMounted(async () => {
  const { default: QRCode } = await import('qrcode')
  svg.value = await QRCode.toString(url, {
    type: 'svg',
    margin: 0,
    errorCorrectionLevel: 'M',
    color: { dark: '#000000', light: '#ffffff' },
  })
})
</script>

<template>
  <div
    class="flex items-center gap-4 rounded-[14px] p-3 pr-5"
    :class="oscuro ? 'border border-white/12 bg-black/60 text-[#f5f7fa] backdrop-blur-xl' : 'border border-[var(--linea)] bg-[var(--superficie)]'"
  >
    <div class="h-[104px] w-[104px] shrink-0 rounded-[10px] bg-white p-2">
      <div v-if="svg" class="qr h-full w-full" role="img" :aria-label="`Código QR de ${url}`" v-html="svg" />
    </div>
    <div class="min-w-0">
      <p class="text-[15px] font-semibold">Ábrela en tu celular</p>
      <p class="mt-1 text-[13px] leading-snug" :class="oscuro ? 'text-[#f5f7fa]/65' : 'text-[var(--texto-2)]'">
        Apunta la cámara al código y entra con tu cuenta.
      </p>
      <p class="mt-1.5 truncate font-mono text-[11.5px]" :class="oscuro ? 'text-[#f5f7fa]/45' : 'text-[var(--texto-3)]'">{{ url.replace(/^https?:\/\//, '') }}</p>
    </div>
  </div>
</template>

<style scoped>
.qr :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
