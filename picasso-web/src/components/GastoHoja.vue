<script setup>
// Registrar o corregir un gasto, cosa por cosa. El total no se escribe: es la
// suma de las partidas (cantidad × precio), para poder auditar qué se compró.
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { mdiDeleteOutline, mdiPaperclip, mdiPlus } from '@mdi/js'

import Hoja from '@/components/Hoja.vue'
import Icono from '@/components/Icono.vue'
import { useToast } from '@/composables/useToast.js'
import { CATEGORIAS_GASTO, FORMAS_PAGO, hoyISO, mensajeError, pesos, TIPOS_OPERACION } from '@/lib/formato.js'
import * as finanzas from '@/services/finanzas.js'
import * as picasso from '@/services/picasso.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const props = defineProps({
  /** Para corregir uno que ya existe. */
  gasto: { type: Object, default: null },
  /** Para registrarlo desde un folio: { id, folio, titulo, sucursal_id }. */
  folio: { type: Object, default: null },
})
const emit = defineEmits(['cerrar', 'guardado'])
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
  incidencia_id: g?.incidencia_id ?? props.folio?.id ?? null,
  partidas: g?.partidas?.length
    ? g.partidas.map((p) => ({ ...p, cantidad: Number(p.cantidad), precio_unitario: Number(p.precio_unitario) }))
    : [nuevaPartida()],
})
const masDatos = ref(Boolean(g?.rfc_proveedor || g?.banco || g?.referencia || g?.tipo_operacion !== 'gasto' && g))
const archivos = ref([])
const guardando = ref(false)

// Folios de la sucursal para ligar el gasto (los abiertos primero).
const folios = ref([])
const folioElegido = computed(() => folios.value.find((f) => f.id === form.incidencia_id))
async function cargarFolios() {
  if (!form.sucursal_id) return (folios.value = [])
  try {
    folios.value = await picasso.folios({ estado: 'todas', sucursal_id: form.sucursal_id })
  } catch {
    folios.value = []
  }
}
watch(() => form.sucursal_id, cargarFolios)
onMounted(async () => {
  await perfil.cargar().catch(() => {})
  if (!form.sucursal_id && perfil.miSucursal) form.sucursal_id = perfil.miSucursal.id
  cargarFolios()
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
    incidencia_id: form.incidencia_id || (g ? 0 : null),
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
        <div v-if="perfil.veTodas && !g" class="col-span-2">
          <label class="mb-1.5 block text-sm font-semibold">Sucursal</label>
          <select v-model="form.sucursal_id" class="campo" :disabled="Boolean(folio)">
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

      <!-- Folio de mantenimiento -->
      <div>
        <label class="mb-1.5 block text-sm font-semibold">Folio de incidencia (opcional)</label>
        <select v-model="form.incidencia_id" class="campo" :disabled="Boolean(folio)">
          <option :value="null">Sin folio</option>
          <option v-if="folio && !folioElegido" :value="folio.id">{{ folio.folio }} · {{ folio.titulo }}</option>
          <option v-for="f in folios" :key="f.id" :value="f.id">{{ f.folio }} · {{ f.titulo }} · Hab. {{ f.habitacion_numero }}</option>
        </select>
      </div>

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
