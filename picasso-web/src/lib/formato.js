// Fechas, nombres y colores de estado. Todo en hora de CDMX y en español.

const ZONA = 'America/Mexico_City'

const fechaCorta = new Intl.DateTimeFormat('es-MX', { timeZone: ZONA, day: '2-digit', month: 'short' })
const horaCorta = new Intl.DateTimeFormat('es-MX', { timeZone: ZONA, hour: '2-digit', minute: '2-digit', hour12: false })
const fechaLarga = new Intl.DateTimeFormat('es-MX', { timeZone: ZONA, day: 'numeric', month: 'long', year: 'numeric' })
const diaClave = new Intl.DateTimeFormat('en-CA', { timeZone: ZONA, year: 'numeric', month: '2-digit', day: '2-digit' })

const limpiar = (s) => s.replace('.', '')

export function fecha(iso) {
  return iso ? limpiar(fechaCorta.format(new Date(iso))) : '—'
}
export function hora(iso) {
  return iso ? horaCorta.format(new Date(iso)) : ''
}
export function fechaHora(iso) {
  return iso ? `${fecha(iso)}, ${hora(iso)}` : '—'
}
export function fechaTexto(iso) {
  return iso ? fechaLarga.format(new Date(iso)) : '—'
}
/** AAAA-MM-DD de hoy (o de hace n días) en CDMX. */
export function hoyISO(menosDias = 0) {
  return diaClave.format(new Date(Date.now() - menosDias * 86400000))
}
export function esHoy(iso) {
  return iso && diaClave.format(new Date(iso)) === hoyISO()
}
export function relativo(iso) {
  if (!iso) return ''
  const minutos = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutos < 1) return 'ahora'
  if (minutos < 60) return `hace ${minutos} min`
  const horas = Math.round(minutos / 60)
  if (horas < 24) return `hace ${horas} h`
  const dias = Math.round(horas / 24)
  return dias === 1 ? 'ayer' : `hace ${dias} días`
}

export const ROLES = {
  admin: 'Administración',
  propietario: 'Propietarios',
  gerente: 'Gerente',
  ama_llaves: 'Ama de llaves',
}

export const RESULTADOS = [
  { valor: 'bien', texto: 'Bien', clase: 'estado-bien' },
  { valor: 'falla', texto: 'Falla', clase: 'estado-falla' },
  { valor: 'no_aplica', texto: 'No aplica', clase: 'estado-na' },
  { valor: 'sin_revisar', texto: 'Sin revisar', clase: 'estado-pendiente' },
]
export const RESULTADO = Object.fromEntries(RESULTADOS.map((r) => [r.valor, r]))

export const ESTADOS_FOLIO = {
  reportada: { texto: 'Reportada', clase: 'estado-falla' },
  en_atencion: { texto: 'En atención', clase: 'estado-na' },
  cerrada: { texto: 'Cerrada', clase: 'estado-bien' },
  anulada: { texto: 'Anulada', clase: 'estado-pendiente' },
}

export const PRIORIDADES = {
  alta: 'Prioridad alta',
  media: 'Prioridad media',
  baja: 'Prioridad baja',
}

/** Orden y color de cada prioridad (filtro, tabla de estado y franja de la tarjeta). */
export const PRIORIDAD_LISTA = [
  { valor: 'alta', texto: 'Alta', color: 'var(--falla)' },
  { valor: 'media', texto: 'Media', color: 'var(--na-solido)' },
  { valor: 'baja', texto: 'Baja', color: 'var(--texto-3)' },
]
export const PRIORIDAD = Object.fromEntries(PRIORIDAD_LISTA.map((p) => [p.valor, p]))

export const AMENIDADES = {
  jacuzzi: 'Jacuzzi',
  alberca: 'Alberca',
  sauna: 'Sauna',
  terraza: 'Terraza',
}

export function porcentaje(valor) {
  return valor === null || valor === undefined ? '—' : `${Math.round(valor * 100)} %`
}

/** Solo el nombre propio de la sucursal: "Picasso Lerma" → "Lerma". */
export function corto(nombre) {
  return (nombre || '').replace(/^Picasso\s+/i, '')
}

export function mensajeError(error) {
  if (!error?.response) return 'Sin conexión. Revisa la señal e inténtalo otra vez.'
  const detalle = error.response.data?.detail
  if (Array.isArray(detalle)) return detalle.map((d) => d.msg).join('. ')
  return detalle || error.message || 'Algo salió mal.'
}

/** "hoy 17:29", "ayer 16:33" o "10 nov, 16:33": la hora de un chequeo de un vistazo. */
export function cuando(iso) {
  if (!iso) return '—'
  const dia = diaClave.format(new Date(iso))
  if (dia === hoyISO()) return `hoy ${hora(iso)}`
  if (dia === hoyISO(1)) return `ayer ${hora(iso)}`
  return fechaHora(iso)
}

// -- finanzas ---------------------------------------------------------------------

/** Una fecha sin hora («2026-11-16») como «16-nov», sin correrla por la zona horaria. */
export function dia(iso) {
  if (!iso) return ''
  const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number)
  return fecha(new Date(y, m - 1, d).toISOString().slice(0, 10) + 'T12:00:00')
}

const MONEDA = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 2 })
const MONEDA_CERRADA = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 })

/** «$12,345.50»; con `cerrado`, sin centavos (para tarjetas grandes). */
export function pesos(valor, cerrado = false) {
  const n = Number(valor ?? 0)
  return (cerrado ? MONEDA_CERRADA : MONEDA).format(Number.isFinite(n) ? n : 0)
}

// Mismas opciones que la plantilla de movimientos del sistema contable.
export const FORMAS_PAGO = [
  { valor: 'efectivo', texto: 'Efectivo' },
  { valor: 'transferencia', texto: 'Transferencia' },
  { valor: 'debito', texto: 'Débito' },
  { valor: 'cheque', texto: 'Cheque' },
  { valor: 'domiciliacion', texto: 'Domiciliación' },
  { valor: 'compensacion', texto: 'Compensación' },
  { valor: 'falta_de_CFDI', texto: 'Falta de CFDI' },
]
export const FORMA_PAGO = Object.fromEntries(FORMAS_PAGO.map((f) => [f.valor, f.texto]))

export const TIPOS_OPERACION = [
  { valor: 'gasto', texto: 'Gasto' },
  { valor: 'compra', texto: 'Compra' },
  { valor: 'proveedores', texto: 'Proveedores' },
  { valor: 'nomina', texto: 'Nómina' },
  { valor: 'impuestos', texto: 'Impuestos (CFDI)' },
  { valor: 'gasto_compra_sin_cfdi', texto: 'Gasto/Compra (Sin CFDI)' },
  { valor: 'no_deducible', texto: 'No deducible' },
  { valor: 'otro', texto: 'Otro' },
]

export const CATEGORIAS_GASTO = [
  { valor: 'mantenimiento', texto: 'Mantenimiento y reparaciones' },
  { valor: 'limpieza', texto: 'Limpieza y lavandería' },
  { valor: 'amenidades', texto: 'Amenidades e insumos de cuarto' },
  { valor: 'frutas_verduras', texto: 'Frutas y verduras' },
  { valor: 'abarrotes', texto: 'Abarrotes' },
  { valor: 'bebidas', texto: 'Bebidas' },
  { valor: 'cocina_bar', texto: 'Insumos de cocina y bar' },
  { valor: 'servicios', texto: 'Luz, agua, gas e internet' },
  { valor: 'nomina', texto: 'Nómina y personal' },
  { valor: 'administracion', texto: 'Administración' },
  { valor: 'otro', texto: 'Otro' },
]
export const CATEGORIA_GASTO = Object.fromEntries(CATEGORIAS_GASTO.map((c) => [c.valor, c.texto]))
