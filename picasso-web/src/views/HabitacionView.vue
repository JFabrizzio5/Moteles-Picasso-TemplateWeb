<script setup>
// Reporte por habitación: últimas revisiones de ambos puestos, pendientes,
// folios y decisión de renta con motivo, fecha y gerente.
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mdiArrowLeft } from '@mdi/js'

import BotonPdf from '@/components/BotonPdf.vue'
import Esqueleto from '@/components/Esqueleto.vue'
import EstadoChip from '@/components/EstadoChip.vue'
import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { AMENIDADES, corto, fechaHora, mensajeError, ROLES } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'

const ruta = useRoute()
const router = useRouter()
const avisos = useToast()
const h = ref(null)

onMounted(async () => {
  try {
    h.value = await picasso.expediente(ruta.params.id)
  } catch (e) {
    avisos.error(mensajeError(e))
  }
})
</script>

<template>
  <Esqueleto v-if="!h" tipo="detalle" />
  <div v-else class="contenedor max-w-5xl pt-6">
    <div class="flex items-center justify-between gap-3">
      <button class="boton boton-suave boton-chico" @click="router.back()"><Icono :path="mdiArrowLeft" :size="18" /> Volver</button>
      <BotonPdf :ruta="`/reportes/habitacion/${h.habitacion_id}.pdf`" :nombre="`Cuarto-${h.numero}.pdf`" texto="Descargar PDF" />
    </div>
    <p class="etiqueta etiqueta-vino mt-6">Expediente · {{ h.sucursal_nombre }}</p>
    <h1 class="titulo-pagina mt-2">Habitación <em>{{ h.numero }}</em></h1>
    <p class="subtitulo mt-2">{{ h.amenidades.map((a) => AMENIDADES[a]).join(' · ') || 'Sin amenidades especiales' }}</p>

    <div class="mt-6 grid gap-4 md:grid-cols-2">
      <section class="tarjeta p-5">
        <p class="etiqueta etiqueta-vino">Decisión vigente de renta</p>
        <template v-if="h.renta">
          <p class="serif mt-3 text-[34px]" :class="h.renta.puede_rentarse ? 'text-[var(--bien)]' : 'text-[var(--vino-texto)]'">
            {{ h.renta.puede_rentarse ? 'Puede rentarse' : 'No puede rentarse' }}
          </p>
          <p class="mt-2 text-sm text-[var(--texto-2)]">{{ h.renta.motivo }}<br />{{ h.renta.gerente_nombre }} · {{ fechaHora(h.renta.decidida_en) }}</p>
        </template>
        <p v-else class="mt-3 text-sm text-[var(--texto-2)]">Sin decisión registrada.</p>
        <details v-if="h.decisiones.length > 1" class="mt-4 text-sm">
          <summary class="cursor-pointer font-semibold text-[var(--texto-2)]">Decisiones anteriores ({{ h.decisiones.length - 1 }})</summary>
          <ul class="mt-2 space-y-1.5 text-[var(--texto-2)]">
            <li v-for="d in h.decisiones.slice(1)" :key="d.id">{{ fechaHora(d.decidida_en) }} · {{ d.puede_rentarse ? 'puede' : 'no puede' }} · {{ d.motivo }}</li>
          </ul>
        </details>
      </section>
      <section class="tarjeta p-5">
        <p class="etiqueta etiqueta-vino">Puntos pendientes</p>
        <p v-if="!h.pendientes.length" class="mt-3 text-sm text-[var(--texto-2)]">No hay revisiones a medias.</p>
        <ul v-else class="mt-3 space-y-1.5 text-sm">
          <li v-for="p in h.pendientes" :key="p.codigo"><strong>{{ p.codigo }}</strong> · {{ p.titulo }}</li>
        </ul>
      </section>
    </div>

    <h2 class="serif mt-10 mb-4 text-[36px]">Folios</h2>
    <p v-if="!h.incidencias.length" class="text-sm text-[var(--texto-2)]">Esta habitación no tiene folios.</p>
    <div class="grid gap-3 md:grid-cols-2">
      <RouterLink v-for="f in h.incidencias" :key="f.id" :to="`/folios/${f.id}`" class="tarjeta flex items-start justify-between gap-3 p-4">
        <div><p class="etiqueta etiqueta-vino">{{ f.folio }}</p><p class="mt-1 font-bold">{{ f.titulo }}</p><p class="text-sm text-[var(--texto-3)]">{{ fechaHora(f.reportada_en) }}</p></div>
        <EstadoChip :folio="f.estado" />
      </RouterLink>
    </div>

    <h2 class="serif mt-10 mb-4 text-[36px]">Revisiones</h2>
    <div class="tarjeta divide-y divide-[var(--linea)]">
      <RouterLink v-for="r in h.revisiones" :key="r.id" :to="`/revision/${r.id}`" class="flex items-center justify-between gap-3 p-4">
        <div>
          <p class="font-semibold">{{ ROLES[r.rol] }} · {{ r.responsable_nombre }}</p>
          <p class="text-sm text-[var(--texto-3)]">{{ fechaHora(r.completada_en || r.iniciada_en) }} · {{ r.revisados }}/{{ r.total }} · {{ r.fallas }} {{ r.fallas === 1 ? 'falla' : 'fallas' }}</p>
        </div>
        <span class="estado" :class="r.estado === 'completa' ? 'estado-bien' : 'estado-na'">{{ r.estado === 'completa' ? 'Completa' : 'A medias' }}</span>
      </RouterLink>
      <p v-if="!h.revisiones.length" class="p-4 text-sm text-[var(--texto-2)]">Sin revisiones.</p>
    </div>
    <p class="mt-6 text-[13px] text-[var(--texto-3)]">{{ corto(h.sucursal_nombre) }} · Hab. {{ h.numero }}</p>
  </div>
</template>
