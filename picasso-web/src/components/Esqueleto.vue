<script setup>
// La forma de la pantalla mientras llegan los datos, en vez de un indicador que gira.
// Así el cambio de módulo se siente inmediato: se ve dónde va a quedar cada cosa.
defineProps({
  /** tarjetas · panel · detalle · graficas · lista */
  tipo: { type: String, default: 'tarjetas' },
  n: { type: Number, default: 6 },
})
</script>

<template>
  <div class="mt-6" aria-busy="true" aria-label="Cargando">
    <!-- Tarjetas (folios, gastos) -->
    <div v-if="tipo === 'tarjetas'" class="grid gap-3 lg:grid-cols-2">
      <div v-for="i in n" :key="i" class="tarjeta p-5">
        <div class="esqueleto h-3 w-28" />
        <div class="esqueleto mt-3 h-5 w-3/4" />
        <div class="esqueleto mt-2 h-3.5 w-1/2" />
        <div class="mt-4 flex gap-2">
          <div class="esqueleto h-6 w-24 !rounded-full" />
          <div class="esqueleto h-6 w-16 !rounded-full" />
        </div>
      </div>
    </div>

    <!-- Panel: cifras y sucursales -->
    <template v-else-if="tipo === 'panel'">
      <div class="grid gap-3 sm:grid-cols-3">
        <div v-for="i in 3" :key="i" class="tarjeta p-5">
          <div class="esqueleto h-11 w-24" />
          <div class="esqueleto mt-3 h-4 w-40" />
          <div class="esqueleto mt-2 h-3 w-32" />
        </div>
      </div>
      <div class="esqueleto mt-12 h-10 w-72" />
      <div class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="i in 3" :key="i" class="tarjeta overflow-hidden">
          <div class="esqueleto h-36 !rounded-none" />
          <div class="p-5">
            <div class="esqueleto h-5 w-32" />
            <div class="esqueleto mt-3 h-2 w-full" />
            <div class="esqueleto mt-2 h-2 w-4/5" />
          </div>
        </div>
      </div>
    </template>

    <!-- Detalle de un folio, cuarto o revisión -->
    <div v-else-if="tipo === 'detalle'" class="contenedor max-w-5xl pt-2">
      <div class="esqueleto h-4 w-32" />
      <div class="esqueleto mt-4 h-10 w-2/3" />
      <div class="esqueleto mt-3 h-4 w-1/2" />
      <div class="esqueleto mt-6 h-28 w-full" />
      <div class="mt-4 grid gap-4 md:grid-cols-2">
        <div class="esqueleto h-40" />
        <div class="esqueleto h-40" />
      </div>
    </div>

    <!-- Cifras y gráficas (finanzas, reportes) -->
    <template v-else-if="tipo === 'graficas'">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div v-for="i in 4" :key="i" class="tarjeta p-5">
          <div class="esqueleto h-3 w-20" />
          <div class="esqueleto mt-3 h-9 w-28" />
          <div class="esqueleto mt-2 h-3 w-24" />
        </div>
      </div>
      <div class="tarjeta mt-4 p-5">
        <div class="esqueleto h-3 w-40" />
        <div class="mt-5 flex h-44 items-end gap-2">
          <div v-for="i in 14" :key="i" class="esqueleto flex-1 !rounded-[4px]" :style="{ height: `${25 + ((i * 37) % 70)}%` }" />
        </div>
      </div>
    </template>

    <!-- Renglones -->
    <div v-else class="tarjeta divide-y divide-[var(--linea)]">
      <div v-for="i in n" :key="i" class="flex items-center gap-4 p-4">
        <div class="esqueleto h-10 w-10 !rounded-full" />
        <div class="flex-1">
          <div class="esqueleto h-4 w-1/2" />
          <div class="esqueleto mt-2 h-3 w-1/3" />
        </div>
      </div>
    </div>
  </div>
</template>
