<script setup>
import { useToast } from '@/composables/useToast.js'

const { toasts, dismiss } = useToast()
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 top-3 z-[70] flex flex-col items-center gap-2 px-4">
    <TransitionGroup name="aviso">
      <button
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto flex max-w-md items-start gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium shadow-xl"
        :class="
          t.variant === 'error'
            ? 'bg-[var(--vino)] text-white'
            : 'bg-[var(--carbon)] text-[var(--sobre-carbon)]'
        "
        @click="dismiss(t.id)"
      >
        <span>{{ t.message }}</span>
      </button>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.aviso-enter-active,
.aviso-leave-active {
  transition: all 0.25s ease;
}
.aviso-enter-from,
.aviso-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
