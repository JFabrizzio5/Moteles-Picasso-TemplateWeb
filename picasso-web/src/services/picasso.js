// Todas las llamadas al backend de Picasso, en un solo lugar.
import api from '@/services/api.js'
import { formularioFoto } from '@/lib/fotos.js'

const datos = (promesa) => promesa.then((r) => r.data)

export const perfil = () => datos(api.get('/perfil'))
export const sucursales = () => datos(api.get('/sucursales'))
export const habitaciones = (sucursalId, todas = false) =>
  datos(api.get(`/sucursales/${sucursalId}/habitaciones`, { params: { todas } }))

export const tablero = (sucursalId) => datos(api.get('/tablero', { params: { sucursal_id: sucursalId } }))
export const abrirRevision = (habitacionId) => datos(api.post('/revisiones', { habitacion_id: habitacionId }))
export const revision = (id) => datos(api.get(`/revisiones/${id}`))
export const revisiones = (params) => datos(api.get('/revisiones', { params }))
export const guardarPunto = (id, codigo, cuerpo) => datos(api.put(`/revisiones/${id}/puntos/${codigo}`, cuerpo))
export const fotoDePunto = (id, codigo, archivo) =>
  datos(api.post(`/revisiones/${id}/puntos/${codigo}/fotos`, formularioFoto(archivo)))
export const quitarFoto = (id, evidenciaId) => datos(api.delete(`/revisiones/${id}/fotos/${evidenciaId}`))
export const completar = (id) => datos(api.post(`/revisiones/${id}/completar`))

export const decidirRenta = (habitacionId, cuerpo) => datos(api.post(`/habitaciones/${habitacionId}/renta`, cuerpo))
export const expediente = (habitacionId) => datos(api.get(`/habitaciones/${habitacionId}/expediente`))

export const folios = (params) => datos(api.get('/incidencias', { params }))
export const conteoFolios = (params) => datos(api.get('/incidencias/conteo', { params }))
export const folio = (id) => datos(api.get(`/incidencias/${id}`))
export const actualizarFolio = (id, cuerpo) => datos(api.patch(`/incidencias/${id}`, cuerpo))
export const avance = (id, nota) => datos(api.post(`/incidencias/${id}/avances`, { nota }))
export const fotoDeFolio = (id, archivo, tipo, nota) =>
  datos(api.post(`/incidencias/${id}/fotos`, formularioFoto(archivo, { tipo, nota })))
export const cerrarFolio = (id, correccion) => datos(api.post(`/incidencias/${id}/cerrar`, { correccion }))

export const panel = (params) => datos(api.get('/panel', { params }))
export const indicadores = (params) => datos(api.get('/indicadores', { params }))

export const actualizarSucursal = (id, cuerpo) => datos(api.patch(`/sucursales/${id}`, cuerpo))
export const crearHabitacion = (sucursalId, cuerpo) => datos(api.post(`/sucursales/${sucursalId}/habitaciones`, cuerpo))
export const actualizarHabitacion = (id, cuerpo) => datos(api.patch(`/habitaciones/${id}`, cuerpo))
export const personal = () => datos(api.get('/personal'))
export const crearPersonal = (cuerpo) => datos(api.post('/personal', cuerpo))

// Reportes en PDF. Van con la sesión (Bearer), así que no sirve un <a href>:
// se bajan como archivo y se entregan al navegador para guardar o abrir.
export async function descargarPdf(ruta, nombre) {
  const respuesta = await api.get(ruta, { responseType: 'blob', timeout: 120000 })
  const url = URL.createObjectURL(respuesta.data)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}

// "Lo demás está bien": los puntos sin tocar pasan a Bien (quedan marcados en bloque).
export const restoBien = (id) => datos(api.post(`/revisiones/${id}/resto-bien`))

// Catálogo de equipo de cuarto (Netflix, sillón, minibar…) y lo que tiene cada cuarto.
export const equipos = () => datos(api.get('/equipos'))
export const crearEquipo = (cuerpo) => datos(api.post('/equipos', cuerpo))
export const actualizarEquipo = (id, cuerpo) => datos(api.patch(`/equipos/${id}`, cuerpo))
export const asignarEquipos = (habitacionId, equipoIds) =>
  datos(api.put(`/habitaciones/${habitacionId}/equipos`, { equipo_ids: equipoIds }))
