// Las fotos del celular pesan 3-6 MB. Se reducen a 1600 px de lado y JPEG 80 %
// (unos 300 KB) antes de subir: en un cuarto con mala señal es la diferencia
// entre subirla o no.

const LADO = 1600

export async function comprimir(archivo) {
  if (!archivo?.type?.startsWith('image/')) {
    throw new Error('Elige una foto.')
  }
  let imagen
  try {
    imagen = await createImageBitmap(archivo, { imageOrientation: 'from-image' })
  } catch {
    // Formatos que el navegador no decodifica (HEIC en algunos Android): se sube tal cual.
    return archivo
  }
  const escala = Math.min(1, LADO / Math.max(imagen.width, imagen.height))
  const lienzo = document.createElement('canvas')
  lienzo.width = Math.round(imagen.width * escala)
  lienzo.height = Math.round(imagen.height * escala)
  lienzo.getContext('2d').drawImage(imagen, 0, 0, lienzo.width, lienzo.height)
  imagen.close?.()
  const blob = await new Promise((listo) => lienzo.toBlob(listo, 'image/jpeg', 0.8))
  return blob ? new File([blob], 'foto.jpg', { type: 'image/jpeg' }) : archivo
}

export function formularioFoto(archivo, extra = {}) {
  const datos = new FormData()
  datos.append('foto', archivo, archivo.name || 'foto.jpg')
  for (const [clave, valor] of Object.entries(extra)) {
    if (valor !== undefined && valor !== null) datos.append(clave, valor)
  }
  return datos
}
