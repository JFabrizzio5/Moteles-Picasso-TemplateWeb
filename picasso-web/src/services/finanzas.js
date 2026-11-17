// Ingresos (leídos de Kairos cada noche) y gastos (capturados aquí).
import api from '@/services/api.js'

const datos = (promesa) => promesa.then((r) => r.data)

export const resumen = (params) => datos(api.get('/finanzas/resumen', { params }))
export const serie = (params) => datos(api.get('/finanzas/serie', { params }))
export const ingresos = (params) => datos(api.get('/finanzas/ingresos', { params }))
export const tarifas = (params) => datos(api.get('/finanzas/tarifas', { params }))
export const fuentes = () => datos(api.get('/finanzas/fuentes'))
export const importar = (cuerpo) => datos(api.post('/finanzas/importar', cuerpo))

export const gastos = (params) => datos(api.get('/gastos', { params }))
export const analisisGastos = (params) => datos(api.get('/gastos/analisis', { params }))
/** Una página de gastos con el total del filtro (encabezados X-Total-*). */
export async function gastosPagina(params) {
  const r = await api.get('/gastos', { params })
  return { lista: r.data, total: Number(r.headers['x-total-count'] || r.data.length), importe: Number(r.headers['x-total-importe'] || 0) }
}
export const gasto = (id) => datos(api.get(`/gastos/${id}`))
export const crearGasto = (cuerpo) => datos(api.post('/gastos', cuerpo))
export const actualizarGasto = (id, cuerpo) => datos(api.patch(`/gastos/${id}`, cuerpo))
export const ligarFolio = (id, incidenciaId) => datos(api.post(`/gastos/${id}/incidencias/${incidenciaId}`))
export const desligarFolio = (id, incidenciaId) => datos(api.delete(`/gastos/${id}/incidencias/${incidenciaId}`))
export const costosFolios = (params) => datos(api.get('/gastos/costos-folios', { params }))
export const anularGasto = (id) => datos(api.post(`/gastos/${id}/anular`))
export const quitarComprobante = (id, archivoId) => datos(api.delete(`/gastos/${id}/archivos/${archivoId}`))

export function subirComprobante(id, archivo) {
  const forma = new FormData()
  forma.append('archivo', archivo, archivo.name || 'comprobante')
  return datos(api.post(`/gastos/${id}/archivos`, forma))
}

async function bajar(ruta, cuerpo, nombre) {
  const r = await api.post(ruta, cuerpo, { responseType: 'blob', timeout: 120000 })
  const url = URL.createObjectURL(r.data)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  setTimeout(() => URL.revokeObjectURL(url), 60000)
  return Number(r.headers['x-gastos'] || r.headers['x-xml'] || 0)
}

/** Excel con las columnas de la plantilla de movimientos de E-Cont. */
export const exportarEcont = (cuerpo, nombre) => bajar('/gastos/econt', cuerpo, nombre)
/** ZIP con los XML de factura, para la importación de CFDI de E-Cont. */
export const exportarXml = (cuerpo, nombre) => bajar('/gastos/econt-xml', cuerpo, nombre)

/** Un error de blob trae el JSON adentro: se lee para mostrar el mensaje. */
export async function mensajeDeBlob(error) {
  const blob = error?.response?.data
  if (blob instanceof Blob) {
    try {
      const j = JSON.parse(await blob.text())
      return j.detail?.message || j.detail || j.message || null
    } catch {
      return null
    }
  }
  return null
}
