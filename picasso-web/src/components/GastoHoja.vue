<script setup>
// Registrar o corregir un gasto, cosa por cosa. El total no se escribe: es la
// suma de las partidas (cantidad × precio), para poder auditar qué se compró.
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { mdiClose, mdiDeleteOutline, mdiLinkVariant, mdiPaperclip, mdiPlus } from '@mdi/js'

import ElegirFolios from '@/components/ElegirFolios.vue'
import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { CATEGORIAS_GASTO, FORMAS_PAGO, hoyISO, mensajeError, pesos, TIPOS_OPERACION } from '@/lib/formato.js'
import * as finanzas from '@/services/finanzas.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const props = defineProps({
  /** Para corregir uno que ya existe. */
  gasto: { type: Object, default: null },
  /** Para registrarlo desde un folio: { id, folio, titulo, sucursal_id, habitacion_numero }. */
  folio: { type: Object, default: null },
})
const emit = defineEmits(['cerrar', 'guardado', 'eliminado'])
const perfil = usePerfilStore()
const avisos = useToast()

const UNIDADES = ['pza', 'kg', 'g', 'lt', 'ml', 'caja', 'paquete', 'bolsa', 'm', 'servicio']
const nuevaPartida = (categoria = '') => ({ descripcion: '', cantidad: 1, unidad: 'pza', precio_unitario: '', categoria })

const g = props.gasto
const form = reactive({
  sucursal_id: g?.sucursal_id ?? props.folio?.sucursal_id ?? perfil.miSucursal?.id ?? '',
  fecha: g?.fecha ?? hoyISO(),
  categoria: g?.categoria ?? (props.folio ? 'mantenimiento' : ''),
  concepto: g?.concepto ?? (props.folio ? `${props.folio.titulo} · ${props.folio.folio}` : ''),
  proveedor: g?.proveedor ?? '',
  forma_pago: g?.forma_pago ?? 'efectivo',
  tipo_operacion: g?.tipo_operacion ?? 'gasto',
  referencia: g?.referencia ?? '',
  rfc_proveedor: g?.rfc_proveedor ?? '',
  banco: g?.banco ?? '',
  nota: g?.nota ?? '',
  partidas: g?.partidas?.length
    ? g.partidas.map((p) => ({ ...p, cantidad: Number(p.cantidad), precio_unitario: Number(p.precio_unitario) }))
    : [nuevaPartida()],
})
const masDatos = ref(Boolean(g?.rfc_proveedor || g?.banco || g?.referencia || g?.tipo_operacion !== 'gasto' && g))
const archivos = ref([])
const guardando = ref(false)

// Folios de incidencia a los que se carga el gasto (varios, de la misma sucursal).
const folios = ref(
  g?.incidencias?.length
    ? [...g.incidencias]
    : props.folio
      ? [{ incidencia_id: props.folio.id, folio: props.folio.folio, titulo: props.folio.titulo, habitacion_numero: props.folio.habitacion_numero ?? '' }]
      : [],
)
const eligiendo = ref(false)
const sucursalNombre = computed(() => perfil.sucursales?.find((s) => s.id === Number(form.sucursal_id))?.nombre ?? '')
function quitarFolio(id) {
  folios.value = folios.value.filter((f) => f.incidencia_id !== id)
}
// Otra sucursal, otros folios: los elegidos dejan de valer.
watch(
  () => form.sucursal_id,
  (nueva, vieja) => {
    if (vieja && nueva !== vieja) folios.value = []
  },
)
onMounted(async () => {
  await perfil.cargar().catch(() => {})
  if (!form.sucursal_id && perfil.miSucursal) form.sucursal_id = perfil.miSucursal.id
})

const importe = (p) => Math.round(Number(p.cantidad || 0) * Number(p.precio_unitario || 0) * 100) / 100
const total = computed(() => form.partidas.reduce((s, p) => s + importe(p), 0))
const partidasListas = computed(() =>
  form.partidas.every((p) => p.descripcion.trim().length >= 3 && Number(p.cantidad) > 0 && Number(p.precio_unitario) > 0),
)
const listo = computed(
  () =>
    form.sucursal_id &&
    form.fecha &&
    form.categoria &&
    form.concepto.trim().length >= 3 &&
    form.proveedor.trim().length >= 2 &&
    partidasListas.value &&
    total.value > 0,
)

function agregarPartida() {
  form.partidas.push(nuevaPartida())
}
function quitarPartida(i) {
  if (form.partidas.length > 1) form.partidas.splice(i, 1)
}
function elegirArchivos(e) {
  archivos.value = [...archivos.value, ...e.target.files]
  e.target.value = ''
}
const arrastrando = ref(false)
function soltar(e) {
  arrastrando.value = false
  archivos.value = [...archivos.value, ...(e.dataTransfer?.files ?? [])]
}

// Papelera: el gasto deja de contar en todo, pero queda quién lo eliminó y por qué.
const eliminando = ref(false)
const motivo = ref('')
const bloqueadoPorExportado = computed(() => Boolean(g?.exportado_en) && !perfil.veTodas)
async function eliminar() {
  guardando.value = true
  try {
    const r = await finanzas.eliminarGasto(g.id, motivo.value.trim())
    avisos.success(`${r.folio} se fue a la papelera. Administración lo puede restaurar.`)
    emit('eliminado', r)
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    guardando.value = false
  }
}

async function guardar() {
  guardando.value = true
  const cuerpo = {
    sucursal_id: perfil.veTodas ? Number(form.sucursal_id) : undefined,
    fecha: form.fecha,
    categoria: form.categoria,
    concepto: form.concepto.trim(),
    proveedor: form.proveedor.trim(),
    forma_pago: form.forma_pago,
    tipo_operacion: form.tipo_operacion,
    referencia: form.referencia.trim() || null,
    rfc_proveedor: form.rfc_proveedor.trim() || null,
    banco: form.banco.trim() || null,
    nota: form.nota.trim() || null,
    incidencia_ids: folios.value.map((f) => f.incidencia_id),
    partidas: form.partidas.map((p) => ({
      descripcion: p.descripcion.trim(),
      cantidad: Number(p.cantidad),
      unidad: p.unidad,
      precio_unitario: Number(p.precio_unitario),
      categoria: p.categoria || null,
    })),
  }
  try {
    let r = g ? await finanzas.actualizarGasto(g.id, { ...cuerpo, sucursal_id: undefined }) : await finanzas.crearGasto(cuerpo)
    for (const a of archivos.value) r = await finanzas.subirComprobante(r.id, a)
    avisos.success(g ? 'Gasto corregido.' : `Gasto ${r.folio} registrado por ${pesos(r.importe)}.`)
    emit('guardado', r)
  } catch (e) {
    avisos.error(mensajeError(e))
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <Hoja :titulo="g ? 'Corregir gasto' : 'Registrar gasto'" :etiqueta="g?.folio || folio?.folio || 'Egresos'" @cerrar="emit('cerrar')">
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-3">
        <div v-if="!g" class="col-span-2">
          <label class="mb-1.5 block text-sm font-semibold">Sucursal</label>
          <!-- El gerente registra en la suya; quien ve todas elige. -->
          <select v-model="form.sucursal_id" class="campo" :disabled="Boolean(folio) || !perfil.veTodas">
            <option value="" disabled>Elige la sucursal</option>
            <option v-for="s in perfil.sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Fecha de pago</label>
          <input v-model="form.fecha" type="date" class="campo" :max="hoyISO()" />
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Forma de pago</label>
          <select v-model="form.forma_pago" class="campo">
            <option v-for="f in FORMAS_PAGO" :key="f.valor" :value="f.valor">{{ f.texto }}</option>
          </select>
        </div>
        <div class="col-span-2">
          <label class="mb-1.5 block text-sm font-semibold">¿Para qué fue?</label>
          <input v-model="form.concepto" class="campo" maxlength="200" placeholder="Reparar el aire de la 108 · Fruta para room service" />
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Categoría</label>
          <select v-model="form.categoria" class="campo">
            <option value="" disabled>Elige</option>
            <option v-for="c in CATEGORIAS_GASTO" :key="c.valor" :value="c.valor">{{ c.texto }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Proveedor o tienda</label>
          <input v-model="form.proveedor" class="campo" maxlength="120" placeholder="Ferretería Lerma" />
        </div>
      </div>

      <!-- Desglose: cosa por cosa -->
      <section class="rounded-[14px] border border-[var(--linea)] p-3">
        <div class="mb-2 flex items-baseline justify-between">
          <p class="text-sm font-semibold">Qué se compró, cosa por cosa</p>
          <p class="text-[12px] text-[var(--texto-3)]">No basta «Verdulería»</p>
        </div>
        <div v-for="(p, i) in form.partidas" :key="i" class="partida">
          <input v-model="p.descripcion" class="campo campo-chico col-span-6" maxlength="120" :placeholder="i === 0 ? 'Ej. Lechuga orejona' : 'Artículo'" :aria-label="`Artículo ${i + 1}`" />
          <input v-model="p.cantidad" type="number" min="0" step="any" inputmode="decimal" class="campo campo-chico col-span-2" aria-label="Cantidad" />
          <select v-model="p.unidad" class="campo campo-chico col-span-2" aria-label="Unidad">
            <option v-for="u in UNIDADES" :key="u" :value="u">{{ u }}</option>
          </select>
          <button type="button" class="col-span-2 grid place-items-center text-[var(--texto-3)] disabled:opacity-30" :disabled="form.partidas.length === 1" aria-label="Quitar" @click="quitarPartida(i)">
            <Icono :path="mdiDeleteOutline" :size="20" />
          </button>
          <div class="col-span-6 flex items-center gap-2">
            <span class="text-[12px] text-[var(--texto-3)]">$ c/u</span>
            <input v-model="p.precio_unitario" type="number" min="0" step="any" inputmode="decimal" class="campo campo-chico" placeholder="0.00" aria-label="Precio unitario" />
          </div>
          <select v-model="p.categoria" class="campo campo-chico col-span-4" aria-label="Categoría de la partida">
            <option value="">Igual que el gasto</option>
            <option v-for="c in CATEGORIAS_GASTO" :key="c.valor" :value="c.valor">{{ c.texto }}</option>
          </select>
          <p class="col-span-2 self-center text-right text-sm font-semibold tabular-nums">{{ pesos(importe(p)) }}</p>
        </div>
        <div class="mt-2 flex items-center justify-between">
          <button type="button" class="boton boton-suave boton-chico" @click="agregarPartida">
            <Icono :path="mdiPlus" :size="18" /> Otra cosa
          </button>
          <p class="text-[15px]">Total <strong class="ml-1 text-[18px] tabular-nums">{{ pesos(total) }}</strong></p>
        </div>
      </section>

      <!-- Folios de mantenimiento -->
      <div>
        <div class="mb-1.5 flex items-baseline justify-between">
          <label class="text-sm font-semibold">Folios de incidencia (opcional)</label>
          <span v-if="folios.length" class="text-[12px] text-[var(--texto-3)]">{{ folios.length }} vinculado{{ folios.length === 1 ? '' : 's' }}</span>
        </div>
        <ul v-if="folios.length" class="mb-2 space-y-1.5">
          <li v-for="f in folios" :key="f.incidencia_id" class="flex items-center justify-between gap-2 rounded-[10px] bg-[var(--superficie-2)] px-3 py-2">
            <!-- Al folio: corrigiendo, se cierra la hoja; registrando, se abre aparte para no perder lo capturado. -->
            <RouterLink
              :to="`/folios/${f.incidencia_id}`"
              :target="g ? undefined : '_blank'"
              class="min-w-0 flex-1 text-[13.5px] hover:underline"
              :title="g ? 'Ir a la incidencia' : 'Abrir la incidencia en otra pestaña'"
              @click="g && emit('cerrar')"
            >
              <span class="folio-codigo">{{ f.folio }} ↗</span>
              <span class="block truncate">{{ f.titulo }}<template v-if="f.habitacion_numero"> · Hab. {{ f.habitacion_numero }}</template></span>
            </RouterLink>
            <button type="button" class="shrink-0 text-[var(--texto-3)]" :aria-label="`Quitar ${f.folio}`" @click="quitarFolio(f.incidencia_id)">
              <Icono :path="mdiClose" :size="18" />
            </button>
          </li>
        </ul>
        <button type="button" class="boton boton-borde w-full" :disabled="!form.sucursal_id" @click="eligiendo = true">
          <Icono :path="mdiLinkVariant" :size="18" /> {{ folios.length ? 'Cambiar folios vinculados' : 'Vincular folios' }}
        </button>
        <p v-if="!form.sucursal_id" class="mt-1 text-[12px] text-[var(--texto-3)]">Elige primero la sucursal.</p>
      </div>
      <ElegirFolios
        v-if="eligiendo"
        :sucursal-id="form.sucursal_id"
        :sucursal-nombre="sucursalNombre"
        :elegidos="folios"
        @cerrar="eligiendo = false"
        @listo="(lista) => ((folios = lista), (eligiendo = false))"
      />

      <!-- Comprobantes: recuadro para arrastrar o tocar -->
      <div>
        <p class="mb-1.5 text-sm font-semibold">Comprobante</p>
        <label
          class="soltar"
          :class="{ encima: arrastrando }"
          @dragenter.prevent="arrastrando = true"
          @dragover.prevent="arrastrando = true"
          @dragleave.prevent="arrastrando = false"
          @drop.prevent="soltar"
        >
          <Icono :path="mdiPaperclip" :size="30" class="text-[var(--vino-texto)]" />
          <span class="text-[15px] font-semibold">Sube el PDF, la foto del ticket o el XML de la factura</span>
          <span class="text-[13px] text-[var(--texto-3)]">Arrástralo aquí o toca para elegirlo · hasta 8 MB</span>
          <input type="file" class="sr-only" multiple accept="image/*,application/pdf,.pdf,.xml,text/xml" @change="elegirArchivos" />
        </label>
        <ul v-if="archivos.length" class="mt-2 space-y-1 text-[13.5px] text-[var(--texto-2)]">
          <li v-for="(a, i) in archivos" :key="i" class="flex items-center justify-between gap-2 rounded-[10px] bg-[var(--superficie-2)] px-3 py-2">
            <span class="truncate">{{ a.name }}</span>
            <button class="shrink-0 text-[var(--texto-3)]" @click="archivos.splice(i, 1)">Quitar</button>
          </li>
        </ul>
        <p v-if="g?.archivos?.length" class="mt-1 text-[12px] text-[var(--texto-3)]">Ya tiene {{ g.archivos.length }} comprobante(s).</p>
      </div>

      <button type="button" class="text-sm font-semibold text-[var(--texto-2)] underline underline-offset-4" @click="masDatos = !masDatos">
        {{ masDatos ? 'Ocultar información adicional' : 'Información adicional (factura, RFC, banco)' }}
      </button>
      <div v-if="masDatos" class="grid grid-cols-2 gap-3">
        <div>
          <label class="mb-1.5 block text-sm font-semibold">#Factura o referencia</label>
          <input v-model="form.referencia" class="campo" maxlength="40" placeholder="A-1234" />
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">RFC del proveedor</label>
          <input v-model="form.rfc_proveedor" class="campo uppercase" maxlength="13" placeholder="XAXX010101000" />
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Tipo de operación</label>
          <select v-model="form.tipo_operacion" class="campo">
            <option v-for="t in TIPOS_OPERACION" :key="t.valor" :value="t.valor">{{ t.texto }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-semibold">Banco</label>
          <input v-model="form.banco" class="campo" maxlength="40" placeholder="Opcional" />
        </div>
        <div class="col-span-2">
          <label class="mb-1.5 block text-sm font-semibold">Nota</label>
          <textarea v-model="form.nota" rows="2" class="campo" maxlength="1000" />
        </div>
      </div>

      <button class="boton boton-vino w-full" :disabled="guardando || !listo" @click="guardar">
        {{ guardando ? 'Guardando…' : g ? 'Guardar cambios' : `Registrar ${pesos(total)}` }}
      </button>
      <p v-if="!partidasListas" class="text-center text-[12px] text-[var(--texto-3)]">Cada cosa lleva nombre, cantidad y precio.</p>

      <!-- Papelera: solo para un gasto que ya existe. -->
      <div v-if="g" class="border-t border-[var(--linea)] pt-4">
        <p v-if="bloqueadoPorExportado" class="text-[13px] text-[var(--texto-3)]">
          Este gasto ya se mandó a contabilidad. Si hay que quitarlo, pídeselo a administración.
        </p>
        <button v-else-if="!eliminando" class="boton boton-suave boton-chico w-full text-[var(--falla)]" @click="eliminando = true">
          <Icono :path="mdiDeleteOutline" :size="18" /> Eliminar este gasto
        </button>
        <div v-else class="rounded-[14px] border border-[var(--falla)] p-4">
          <p class="text-sm font-semibold">¿Por qué se elimina?</p>
          <p class="mt-1 text-[12.5px] text-[var(--texto-3)]">
            Se va a la papelera: deja de contar en listas, reportes y exportes, pero queda quién lo eliminó y el motivo.
          </p>
          <textarea
            v-model="motivo"
            rows="2"
            maxlength="300"
            class="campo mt-3"
            aria-label="Motivo para eliminar"
            placeholder="Lo capturé dos veces, era de otra sucursal…"
          />
          <div class="mt-3 flex gap-2">
            <button class="boton boton-suave boton-chico flex-1" :disabled="guardando" @click="eliminando = false">Cancelar</button>
            <button
              class="boton boton-alerta boton-chico flex-1"
              :disabled="guardando || motivo.trim().length < 5"
              @click="eliminar"
            >
              Mandar a la papelera
            </button>
          </div>
        </div>
      </div>
    </div>
  </Hoja>
</template>

<style scoped>
.partida {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 6px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--linea);
}
.campo-chico {
  min-height: 42px;
  padding: 8px 10px;
  font-size: 14px;
}
.soltar {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 150px;
  padding: 20px;
  text-align: center;
  border: 2px dashed var(--linea-fuerte);
  border-radius: 14px;
  background: var(--superficie);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.soltar:hover,
.soltar.encima {
  border-color: var(--vino);
  background: var(--vino-suave);
}
select.campo-chico {
  padding-right: 26px;
  background-position: right 6px center;
}
</style>
