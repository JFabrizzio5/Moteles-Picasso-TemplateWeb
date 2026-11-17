import { readonly, ref } from 'vue'

import { setTheme as fijar, storedTheme } from '@/composables/useTheme.js'

const guardado = storedTheme()
// 'system' no aplica aquí: sin elección, la app es clara como el sitio de Picasso.
const actual = ref(guardado === 'system' ? 'light' : guardado)

export function setTheme(valor) {
  actual.value = valor
  fijar(valor)
}

export function useThemeValue() {
  return readonly(actual)
}
