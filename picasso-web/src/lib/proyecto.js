// Material del proyecto (documentación, manual y video promocional).
// Vive en el sitio de la documentación (VITE_DOCS_URL, ver .env.vps). Sin esa
// variable no aparece nada: el build para Picasso no la lleva.

const BASE = (import.meta.env.VITE_DOCS_URL ?? '').replace(/\/+$/, '')

export const HAY_MATERIAL = !!BASE

export const MATERIAL = {
  documentacion: `${BASE}/`,
  manual: `${BASE}/manual-usuario.html`,
  video: {
    vertical: `${BASE}/video/Picasso-Inspecciones-9x16.mp4?v=20261117`,
    horizontal: `${BASE}/video/Picasso-Inspecciones-16x9.mp4?v=20261117`,
    portadaVertical: `${BASE}/video/portada-9x16.jpg`,
    portadaHorizontal: `${BASE}/video/portada-16x9.jpg`,
  },
}
