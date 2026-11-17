<script setup>
// Ajustes de administración: reglas por sucursal, cuartos con lo que tiene cada
// uno (áreas especiales y equipo del catálogo), el catálogo de equipo y el personal.
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { mdiPencilOutline, mdiPlus } from '@mdi/js'

import Esqueleto from '@/components/Esqueleto.vue'
import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { AMENIDADES, corto, mensajeError, ROLES } from '@/lib/formato.js'
import * as picasso from '@/services/picasso.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const perfil = usePerfilStore()
const avisos = useToast()

const pestana = ref('cuartos')
const sucursalId = ref(null)
const cuartos = ref([])
const catalogo = ref([])
const gente = ref([])
const nuevoCuarto = ref('')
const alta = ref(false)
const persona = reactive({ nombre: '', email: '', password: '', rol: 'ama_llaves', sucursal_id: null })
const ocupado = ref(false)
const editando = reactive({ cuarto: null, seleccion: new Set() })
const nuevoEquipo = reactive({ nombre: '', categoria: 'Entretenimiento', otraCategoria: '' })

const CATEGORIAS_BASE = ['Entretenimiento', 'Mobiliario especial', 'Confort', 'Baño']
const sucursal = computed(() => perfil.sucursal(sucursalId.value))
const porId = computed(() => Object.fromEntries(catalogo.value.map((e) => [e.id, e])))
const categorias = computed(() => {
  const nombres = new Set([...CATEGORIAS_BASE, ...catalogo.value.map((e) => e.categoria)])
  return [...nombres].map((nombre) => ({ nombre, equipos: catalogo.value.filter((e) => e.categoria === nombre) }))
})

onMounted(async () => {
  await perfil.cargar(true)
  sucursalId.value = perfil.sucursales[0]?.id ?? null
  const [c, g] = await Promise.all([picasso.equipos().catch(() => []), picasso.personal().catch(() => [])])
  catalogo.value = c
  gente.value = g
})
watch(sucursalId, async (id) => {
  if (id) cuartos.value = await picasso.habitaciones(id, true)
})

async function guardarSucursal(cambios) {
  try {
    await picasso.actualizarSucursal(sucursalId.value, cambios)
    await perfil.cargar(true)
    avisos.success('Guardado.')
  } catch (e) {
    avisos.error(mensajeError(e))
  }
}
async function cambiarCuarto(c, cambios) {
  try {
    Object.assign(c, await picasso.actualizarHabitacion(c.id, cambios))
  } catch (e) {
    avisos.error(mensajeError(e))
  }
}
async function agregarCuarto() {
  try {
    cuartos.value.push(await picasso.crearHabitacion(sucursalId.value, { numero: nuevoCuarto.value }))
    nuevoCuarto.value = ''
  } catch (e) {
    avisos.error(mensajeError(e))
  }
}

// -- equipo de un cuarto -------------------------------------------------------------------

function editarEquipo(c) {
  editando.cuarto = c
  editando.seleccion = new Set(c.equipo_ids)
}
function alternar(id) {
  const s = new Set(editando.seleccion)
  s.has(id) ? s.delete(id) : s.add(id)
  editando.seleccion = s
}
async function guardarEquipo() {
  ocupado.value = true
  try {
    const c = editando.cuarto
    Object.assign(c, await picasso.asignarEquipos(c.id, [...editando.seleccion]))
    editando.cuarto = null
    avisos.success(`Cuarto ${c.numero} actualizado.`)
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    ocupado.value = false
  }
}
const nombresDe = (c) => c.equipo_ids.map((id) => porId.value[id]?.nombre).filter(Boolean)

// -- catálogo ----------------------------------------------------------------------------------

async function agregarEquipo() {
  const categoria = nuevoEquipo.categoria === '__otra' ? nuevoEquipo.otraCategoria.trim() : nuevoEquipo.categoria
  try {
    catalogo.value.push(await picasso.crearEquipo({ nombre: nuevoEquipo.nombre.trim(), categoria }))
    nuevoEquipo.nombre = ''
    nuevoEquipo.otraCategoria = ''
    avisos.success('Agregado al catálogo.')
  } catch (e) {
    avisos.error(mensajeError(e))
  }
}
async function cambiarEquipo(e, cambios) {
  try {
    Object.assign(e, await picasso.actualizarEquipo(e.id, cambios))
  } catch (err) {
    avisos.error(mensajeError(err))
  }
}
async function renombrar(e) {
  const nombre = window.prompt('Nuevo nombre', e.nombre)
  if (nombre && nombre.trim() && nombre.trim() !== e.nombre) await cambiarEquipo(e, { nombre: nombre.trim() })
}

// -- personal -------------------------------------------------------------------------------------

async function darAlta() {
  ocupado.value = true
  try {
    const cuerpo = { ...persona, sucursal_id: ['gerente', 'ama_llaves'].includes(persona.rol) ? persona.sucursal_id : null }
    gente.value.push(await picasso.crearPersonal(cuerpo))
    alta.value = false
    Object.assign(persona, { nombre: '', email: '', password: '' })
    avisos.success('Cuenta creada. Entrega la contraseña en persona.')
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    ocupado.value = false
  }
}
const nombreSucursal = (id) => perfil.sucursal(id)?.nombre ?? 'Todas'
</script>

<template>
  <div class="contenedor max-w-5xl pt-8">
    <p class="seccion mb-3">Administración</p>
    <h1 class="titulo-pagina">Cuartos, equipo <em>y personal.</em></h1>
    <div class="sin-scroll -mx-[18px] mt-6 flex gap-2 overflow-x-auto px-[18px]">
      <button class="chip shrink-0" :aria-pressed="pestana === 'cuartos'" @click="pestana = 'cuartos'">Cuartos</button>
      <button class="chip shrink-0" :aria-pressed="pestana === 'equipo'" @click="pestana = 'equipo'">Catálogo de equipo</button>
      <button class="chip shrink-0" :aria-pressed="pestana === 'personal'" @click="pestana = 'personal'">Personal</button>
    </div>

    <Esqueleto v-if="!perfil.sucursales.length" tipo="lista" :n="5" />

    <!-- Cuartos -->
    <template v-else-if="pestana === 'cuartos'">
      <div class="sin-scroll -mx-[18px] mt-5 flex gap-2 overflow-x-auto px-[18px]">
        <button v-for="s in perfil.sucursales" :key="s.id" class="chip shrink-0" :aria-pressed="sucursalId === s.id" @click="sucursalId = s.id">{{ corto(s.nombre) }}</button>
      </div>

      <section v-if="sucursal" class="tarjeta mt-4 grid gap-4 p-5 md:grid-cols-3">
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Revisión del gerente</label>
          <select class="campo" :value="sucursal.frecuencia_gerente_dias" @change="guardarSucursal({ frecuencia_gerente_dias: Number($event.target.value) })">
            <option :value="1">Diaria</option>
            <option :value="2">Cada dos días</option>
            <option :value="3">Cada tres días</option>
          </select>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Exigibles de ama de llaves</label>
          <select class="campo" :value="sucursal.ama_exigible" @change="guardarSucursal({ ama_exigible: $event.target.value })">
            <option value="por_limpieza">Una por cada limpieza</option>
            <option value="diaria">Una por cuarto al día</option>
          </select>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Checklist</label>
          <select class="campo" :value="String(sucursal.permite_bien_en_bloque)" @change="guardarSucursal({ permite_bien_en_bloque: $event.target.value === 'true' })">
            <option value="true">Solo marcar lo que está mal</option>
            <option value="false">Marcar cada punto ✓ o ✗</option>
          </select>
        </div>
      </section>

      <div class="mt-7 flex items-end justify-between gap-3">
        <div>
          <p class="seccion">Cuartos</p>
          <p class="mt-1 text-[13px] text-[var(--texto-3)]">Lo que tiene cada cuarto entra a su checklist. Tipo, jacuzzi y sauna vienen de Kairos.</p>
        </div>
        <form class="flex gap-2" @submit.prevent="agregarCuarto">
          <input v-model="nuevoCuarto" class="campo !min-h-[40px] w-24 !py-2" placeholder="Número" />
          <button class="boton boton-primario boton-chico" :disabled="!nuevoCuarto.trim()"><Icono :path="mdiPlus" :size="18" /></button>
        </form>
      </div>
      <div class="escalonado mt-3 grid gap-3 md:grid-cols-2">
        <div v-for="(c, i) in cuartos" :key="c.id" class="tarjeta p-4" :class="c.activa ? '' : 'opacity-50'" :style="{ '--i': Math.min(i, 12) }">
          <div class="flex items-start justify-between gap-3">
            <div>
              <span class="serif text-[38px] leading-none">{{ c.numero }}</span>
              <p v-if="c.tipo" class="mt-1 text-[12.5px] font-semibold tracking-wide text-[var(--texto-2)] uppercase">
                {{ c.tipo }}<template v-if="c.seccion"> · {{ c.seccion }}</template>
              </p>
            </div>
            <div class="flex gap-2">
              <button class="boton boton-primario boton-chico" @click="editarEquipo(c)">Equipo</button>
              <button class="boton boton-borde boton-chico" @click="cambiarCuarto(c, { activa: !c.activa })">{{ c.activa ? 'Baja' : 'Activar' }}</button>
            </div>
          </div>
          <div class="mt-3 flex flex-wrap gap-1.5">
            <button
              v-for="(nombre, clave) in AMENIDADES"
              :key="clave"
              class="chip !h-8 !text-[13px]"
              :aria-pressed="c[`tiene_${clave}`]"
              @click="cambiarCuarto(c, { [`tiene_${clave}`]: !c[`tiene_${clave}`] })"
            >
              {{ nombre }}
            </button>
          </div>
          <p class="mt-3 text-[13.5px] leading-snug text-[var(--texto-2)]">
            <template v-if="nombresDe(c).length">{{ nombresDe(c).join(' · ') }}</template>
            <span v-else class="text-[var(--texto-3)]">Sin equipo registrado.</span>
          </p>
        </div>
      </div>
    </template>

    <!-- Catálogo de equipo -->
    <template v-else-if="pestana === 'equipo'">
      <form class="tarjeta mt-5 grid gap-3 p-5 md:grid-cols-[1fr_220px_auto]" @submit.prevent="agregarEquipo">
        <input v-model="nuevoEquipo.nombre" class="campo" placeholder="Ej.: Consola de videojuegos" maxlength="60" />
        <select v-model="nuevoEquipo.categoria" class="campo">
          <option v-for="c in categorias" :key="c.nombre" :value="c.nombre">{{ c.nombre }}</option>
          <option value="__otra">Otra categoría…</option>
        </select>
        <button class="boton boton-primario" :disabled="nuevoEquipo.nombre.trim().length < 2 || (nuevoEquipo.categoria === '__otra' && nuevoEquipo.otraCategoria.trim().length < 2)">
          Agregar
        </button>
        <input v-if="nuevoEquipo.categoria === '__otra'" v-model="nuevoEquipo.otraCategoria" class="campo md:col-span-3" placeholder="Nombre de la categoría" maxlength="40" />
      </form>
      <p class="mt-2 text-[13px] text-[var(--texto-3)]">Lo que desactives deja de salir en los checklists nuevos; lo ya revisado se conserva.</p>

      <section v-for="c in categorias" :key="c.nombre" class="mt-6">
        <p class="seccion mb-2">{{ c.nombre }}</p>
        <div class="tarjeta divide-y divide-[var(--linea)]">
          <div v-for="e in c.equipos" :key="e.id" class="flex items-center justify-between gap-3 px-4 py-3" :class="e.activo ? '' : 'opacity-50'">
            <span class="font-semibold">{{ e.nombre }}</span>
            <div class="flex items-center gap-2">
              <button class="grid h-9 w-9 place-items-center rounded-full text-[var(--texto-3)]" aria-label="Renombrar" @click="renombrar(e)">
                <Icono :path="mdiPencilOutline" :size="18" />
              </button>
              <button class="chip !h-8 !text-[13px]" :aria-pressed="e.activo" @click="cambiarEquipo(e, { activo: !e.activo })">
                {{ e.activo ? 'Activo' : 'Inactivo' }}
              </button>
            </div>
          </div>
          <p v-if="!c.equipos.length" class="px-4 py-3 text-sm text-[var(--texto-3)]">Nada en esta categoría todavía.</p>
        </div>
      </section>
    </template>

    <!-- Personal -->
    <template v-else>
      <div class="mt-6 flex justify-end"><button class="boton boton-primario boton-chico" @click="alta = true">Dar de alta</button></div>
      <div class="tarjeta mt-4 divide-y divide-[var(--linea)]">
        <div v-for="p in gente" :key="p.id" class="flex items-center justify-between gap-3 p-4">
          <div><p class="font-semibold">{{ p.nombre }}</p><p class="text-sm text-[var(--texto-3)]">{{ ROLES[p.rol] }} · {{ nombreSucursal(p.sucursal_id) }}</p></div>
        </div>
      </div>
    </template>

    <!-- Equipo de un cuarto -->
    <Hoja v-if="editando.cuarto" :titulo="`Cuarto ${editando.cuarto.numero}`" :etiqueta="`${corto(sucursal?.nombre)} · ¿qué tiene?`" @cerrar="editando.cuarto = null">
      <p class="mb-4 text-[14px] text-[var(--texto-2)]">Toca lo que tiene este cuarto. Cada cosa aparecerá en su checklist.</p>
      <section v-for="c in categorias.filter((x) => x.equipos.some((e) => e.activo))" :key="c.nombre" class="mb-4">
        <p class="seccion mb-2">{{ c.nombre }}</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="e in c.equipos.filter((x) => x.activo)"
            :key="e.id"
            class="chip"
            :aria-pressed="editando.seleccion.has(e.id)"
            @click="alternar(e.id)"
          >
            {{ e.nombre }}
          </button>
        </div>
      </section>
      <button class="boton boton-primario mt-2 w-full" :disabled="ocupado" @click="guardarEquipo">
        Guardar · {{ editando.seleccion.size }} {{ editando.seleccion.size === 1 ? 'cosa' : 'cosas' }}
      </button>
    </Hoja>

    <Hoja v-if="alta" titulo="Nueva persona" etiqueta="Personal" @cerrar="alta = false">
      <form class="space-y-3" @submit.prevent="darAlta">
        <input v-model="persona.nombre" class="campo" placeholder="Nombre completo" required />
        <input v-model="persona.email" type="email" class="campo" placeholder="Correo" required />
        <input v-model="persona.password" type="text" class="campo" placeholder="Contraseña (mínimo 10)" minlength="10" required />
        <select v-model="persona.rol" class="campo">
          <option v-for="(nombre, clave) in ROLES" :key="clave" :value="clave">{{ nombre }}</option>
        </select>
        <select v-if="['gerente', 'ama_llaves'].includes(persona.rol)" v-model="persona.sucursal_id" class="campo" required>
          <option :value="null" disabled>Sucursal</option>
          <option v-for="s in perfil.sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
        <button class="boton boton-primario w-full" :disabled="ocupado">Crear cuenta</button>
      </form>
    </Hoja>
  </div>
</template>
