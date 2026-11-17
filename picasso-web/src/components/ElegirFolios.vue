<script setup>
// Elegir con casillas los folios de incidencia a los que se carga un gasto.
// Solo los de la sucursal del gasto; por omisión los activos (reportados o en atención).
import { computed, onMounted, ref, watch } from 'vue'
import { mdiMagnify } from '@mdi/js'

import Cargando from '@/components/Cargando.vue'
import EstadoChip from '@/components/EstadoChip.vue'
import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import { mensajeError, PRIORIDAD } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'

const props = defineProps({
  sucursalId: { type: [Number, String], required: true },
  sucursalNombre: { type: String, default: '' },
  /** Folios ya elegidos: [{ incidencia_id, folio, titulo, habitacion_numero }]. */
  elegidos: { type: Array, default: () => [] },
})
const emit = defineEmits(['cerrar', 'listo'])

const POR_PAGINA = 8
const lista = ref([])
const cargando = ref(true)
const error = ref('')
const buscar = ref('')
const conCerradas = ref(false)
const pagina = ref(1)
const marcados = ref(new Map(props.elegidos.map((f) => [f.incidencia_id, f])))

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    lista.value = await picasso.folios({
      estado: conCerradas.value ? 'todas' : 'abiertas',
      sucursal_id: props.sucursalId,
      buscar: buscar.value || undefined,
    })
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    cargando.value = false
    pagina.value = 1
  }
}
let espera = null
watch(buscar, () => {
  clearTimeout(espera)
  espera = setTimeout(cargar, 300)
})
watch(conCerradas, cargar)
onMounted(cargar)

const paginas = computed(() => Math.max(1, Math.ceil(lista.value.length / POR_PAGINA)))
const visibles = computed(() => lista.value.slice((pagina.value - 1) * POR_PAGINA, pagina.value * POR_PAGINA))

function alternar(f) {
  const m = new Map(marcados.value)
  if (m.has(f.id)) m.delete(f.id)
  else m.set(f.id, { incidencia_id: f.id, folio: f.folio, titulo: f.titulo, habitacion_numero: f.habitacion_numero })
  marcados.value = m
}
</script>

<template>
  <Hoja titulo="Vincular folios" :etiqueta="sucursalNombre || 'Incidencias'" @cerrar="emit('cerrar')">
    <div class="relative">
      <Icono :path="mdiMagnify" class="absolute top-1/2 left-4 -translate-y-1/2 text-[var(--texto-3)]" />
      <input v-model="buscar" class="campo pl-11" placeholder="Folio, problema o habitación" />
    </div>
    <label class="mt-3 flex items-center gap-2 text-sm text-[var(--texto-2)]">
      <input v-model="conCerradas" type="checkbox" class="h-4 w-4" /> Incluir folios cerrados
    </label>

    <Cargando v-if="cargando" texto="Buscando folios" />
    <p v-else-if="error" class="mt-4 text-sm text-[var(--falla)]">{{ error }}</p>
    <p v-else-if="!lista.length" class="mt-5 text-sm text-[var(--texto-3)]">
      {{ conCerradas ? 'No hay folios con esa búsqueda.' : 'Esta sucursal no tiene folios activos. Prueba con «Incluir folios cerrados».' }}
    </p>
    <ul v-else class="mt-3 divide-y divide-[var(--linea)]">
      <li v-for="f in visibles" :key="f.id">
        <label class="flex cursor-pointer items-start gap-3 py-3">
          <input type="checkbox" class="mt-1 h-5 w-5 shrink-0" :checked="marcados.has(f.id)" @change="alternar(f)" />
          <span class="min-w-0 flex-1">
            <span class="folio-codigo block">{{ f.folio }}</span>
            <span class="block font-semibold leading-snug">{{ f.titulo }}</span>
            <span class="block text-[13px] text-[var(--texto-3)]">
              Hab. {{ f.habitacion_numero }} ·
              <span :style="{ color: PRIORIDAD[f.prioridad]?.color }">prioridad {{ PRIORIDAD[f.prioridad]?.texto.toLowerCase() }}</span>
            </span>
          </span>
          <EstadoChip :folio="f.estado" />
        </label>
      </li>
    </ul>

    <div v-if="paginas > 1" class="mt-3 flex items-center justify-between text-sm">
      <button class="boton boton-suave boton-chico" :disabled="pagina === 1" @click="pagina--">Anterior</button>
      <span class="text-[var(--texto-2)]">Página {{ pagina }} de {{ paginas }}</span>
      <button class="boton boton-suave boton-chico" :disabled="pagina === paginas" @click="pagina++">Siguiente</button>
    </div>

    <button class="boton boton-vino mt-5 w-full" @click="emit('listo', [...marcados.values()])">
      {{ marcados.size ? `Vincular ${marcados.size} ${marcados.size === 1 ? 'folio' : 'folios'}` : 'Sin folios' }}
    </button>
  </Hoja>
</template>
