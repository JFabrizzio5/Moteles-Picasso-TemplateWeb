<script setup>
// Accesos de un toque para la demostración: un botón por puesto y la
// sucursal que se quiere ver. Solo aparece con el modo demo encendido.
import { computed, ref } from 'vue'
import { mdiAccountTieOutline, mdiBroom, mdiChevronRight, mdiCogOutline, mdiOfficeBuildingOutline } from '@mdi/js'

import Icono from '@/components/Icono.vue'
import { SUCURSALES_DEMO } from '@/lib/demo.js'

defineProps({ cargando: { type: String, default: '' } })
const emit = defineEmits(['entrar'])

const sucursal = ref(SUCURSALES_DEMO[0])

const cuentas = computed(() => [
  {
    correo: 'propietario@picasso.mx',
    titulo: 'Propietarios',
    nombre: 'Las seis sucursales',
    ayuda: 'Panel, folios y reportes de todo el grupo',
    icono: mdiOfficeBuildingOutline,
  },
  {
    correo: `gerente.${sucursal.value.clave}@picasso.mx`,
    titulo: `Gerente · ${sucursal.value.nombre}`,
    nombre: sucursal.value.gerente,
    ayuda: 'Checklist de 25 puntos, renta y cierre de folios',
    icono: mdiAccountTieOutline,
  },
  {
    correo: `ama.${sucursal.value.clave}@picasso.mx`,
    titulo: `Ama de llaves · ${sucursal.value.nombre}`,
    nombre: sucursal.value.ama,
    ayuda: 'Checklist de 29 puntos después de cada limpieza',
    icono: mdiBroom,
  },
  {
    correo: 'admin.demo@picasso.mx',
    titulo: 'Administración',
    nombre: 'Configura cuartos y equipo',
    ayuda: 'Qué tiene cada cuarto (Netflix, sillón, minibar…), personal y reglas',
    icono: mdiCogOutline,
  },
])
</script>

<template>
  <section class="rounded-[16px] border border-[#fe7877]/40 bg-black/70 p-5 backdrop-blur-xl md:p-6">
    <div class="flex items-center justify-between gap-3">
      <p class="etiqueta !text-[#fe7877]">Demo · datos de ejemplo</p>
      <span class="rounded-full bg-[#fe7877] px-2.5 py-0.5 text-[11px] font-bold text-black">DEMO</span>
    </div>
    <h2 class="serif mt-2 text-[32px] text-[#f5f7fa]">Entra como…</h2>

    <p class="mt-4 mb-2 text-[13px] text-white/60">Sucursal para gerente y ama de llaves</p>
    <div class="sin-scroll -mx-5 flex gap-2 overflow-x-auto px-5 md:-mx-6 md:px-6">
      <button
        v-for="s in SUCURSALES_DEMO"
        :key="s.clave"
        type="button"
        class="chip shrink-0 !h-9"
        :class="sucursal.clave === s.clave ? '!border-[#f5f7fa] !bg-[#f5f7fa] !text-black' : '!border-white/20 !text-white/75'"
        @click="sucursal = s"
      >
        {{ s.nombre }}
      </button>
    </div>

    <div class="mt-4 space-y-2">
      <button
        v-for="c in cuentas"
        :key="c.correo"
        type="button"
        class="flex w-full items-center gap-3 rounded-[12px] border border-white/12 bg-white/[0.06] px-4 py-3.5 text-left text-[#f5f7fa] transition hover:border-[#fe7877]/60 active:scale-[0.99] disabled:opacity-50"
        :disabled="!!cargando"
        @click="emit('entrar', c.correo)"
      >
        <span class="grid h-10 w-10 shrink-0 place-items-center rounded-[10px] bg-[#fe7877] text-black">
          <Icono :path="c.icono" :size="22" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-[15px] font-semibold">{{ c.titulo }}</span>
          <span class="line-clamp-2 block text-[12.5px] leading-snug text-white/60">{{ c.nombre }} · {{ c.ayuda }}</span>
        </span>
        <span v-if="cargando === c.correo" class="h-5 w-5 animate-spin rounded-full border-2 border-white/25 border-t-[#fe7877]" />
        <Icono v-else :path="mdiChevronRight" class="text-white/50" />
      </button>
    </div>
    <p class="mt-4 text-[12px] leading-relaxed text-white/45">
      Cuartos, personas y folios son inventados para enseñar la app. Lo que hagas aquí se guarda en la base de prueba.
    </p>
  </section>
</template>
