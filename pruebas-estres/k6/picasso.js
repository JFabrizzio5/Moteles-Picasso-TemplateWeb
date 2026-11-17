// Pruebas de carga y estrés de Picasso con k6. Se corre con ../correr.sh;
// el README de la carpeta explica cada escenario y cómo leer el resultado.
//
// Cada usuario virtual hace lo que hace una persona en la app:
//   gerente      tablero → revisión (fallas con foto, lo demás bien, enviar)
//                → folios (avance, foto de reparación, cierre) → renta → PDF
//   ama          tablero → revisión de 29 puntos → enviar
//   propietario  panel → indicadores → folios → revisiones → PDF de grupo
//
// Todo lo que escribe lleva «[estrés]» en el texto. Solo contra una base de
// prueba: servidor/foto-base.sh la guarda antes y restaurar-base.sh la deja
// como estaba.

import http from 'k6/http'
import { check, fail, group, sleep } from 'k6'
import exec from 'k6/execution'
import { Counter, Rate } from 'k6/metrics'

const URL = (__ENV.URL || 'https://2.25.196.39:9630').replace(/\/$/, '')
const API = (__ENV.API || `${URL}/api`).replace(/\/$/, '')
const CLAVE = __ENV.PICASSO_CLAVE
const ESCENARIO = __ENV.ESCENARIO || 'humo'
// Multiplica las pausas entre acciones: 1 es el ritmo de una persona; en
// estrés y pico se acortan para apretar más con los mismos usuarios.
const PAUSA = Number(__ENV.PAUSA || ({ estres: 0.15, pico: 0.3 }[ESCENARIO] ?? 1))
// Solo para resistencia: minutos que dura (el token vive 15; ver README).
const DURACION = Number(__ENV.DURACION || 12)
const FOTO = open('./foto.jpg', 'b') // 239 KB, lo que manda el celular
// En humo cada camino se recorre siempre (falla, foto, cierre, renta, PDF),
// para saber que el guion completo funciona antes de cargar.
const SIEMPRE = ESCENARIO === 'humo'
const toca = (p) => SIEMPRE || Math.random() < p

const SUCURSALES = ['ler', 'tol', 'cir', 'chu', 'per', 'vaq']
const JSON_H = { 'Content-Type': 'application/json' }

// Dos usuarios del mismo puesto en el mismo cuarto comparten la revisión
// abierta; si uno la envía, al otro la API le contesta 422 «ya se cerró».
// Igual con los folios: varios «gerentes» virtuales de la misma sucursal ven
// el mismo folio, uno lo cierra y al otro le contestan «ya no está abierto».
// Es la API haciendo bien su trabajo: se cuenta aparte, no como error.
const CHOQUE = /ya se cerró|ya no está abierto/
const choques = new Counter('choques_misma_revision')
const erroresNegocio = new Rate('errores_de_negocio')

// -- escenarios ---------------------------------------------------------------

const personas = (exec_, extra) => ({ exec: exec_, gracefulStop: '30s', ...extra })

const ESCENARIOS = {
  // ¿Funciona el guion? Una vuelta de cada puesto.
  humo: {
    gerentes: personas('gerente', { executor: 'per-vu-iterations', vus: 1, iterations: 1, maxDuration: '5m' }),
    amas: personas('ama', { executor: 'per-vu-iterations', vus: 1, iterations: 1, maxDuration: '5m' }),
    propietarios: personas('propietario', { executor: 'per-vu-iterations', vus: 1, iterations: 1, maxDuration: '5m' }),
  },
  // Un cambio de turno normal en las seis sucursales, a ritmo de persona.
  carga: {
    gerentes: personas('gerente', { executor: 'constant-vus', vus: 6, duration: '10m' }),
    amas: personas('ama', { executor: 'constant-vus', vus: 12, duration: '10m' }),
    propietarios: personas('propietario', { executor: 'constant-vus', vus: 2, duration: '10m' }),
  },
  // Sube por escalones hasta que algo cede. Se detiene solo si los errores
  // pasan del 10 %.
  estres: {
    gerentes: personas('gerente', {
      executor: 'ramping-vus',
      startVUs: 2,
      stages: [
        { duration: '1m', target: 6 },
        { duration: '2m', target: 15 },
        { duration: '2m', target: 30 },
        { duration: '2m', target: 50 },
        { duration: '2m', target: 75 },
        { duration: '1m', target: 0 },
      ],
    }),
    amas: personas('ama', {
      executor: 'ramping-vus',
      startVUs: 4,
      stages: [
        { duration: '1m', target: 12 },
        { duration: '2m', target: 30 },
        { duration: '2m', target: 60 },
        { duration: '2m', target: 100 },
        { duration: '2m', target: 150 },
        { duration: '1m', target: 0 },
      ],
    }),
    propietarios: personas('propietario', {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '3m', target: 3 },
        { duration: '4m', target: 6 },
        { duration: '2m', target: 10 },
        { duration: '1m', target: 0 },
      ],
    }),
  },
  // Entran todos a la vez (inicio de turno o la señal que regresa y la cola
  // del celular que se vacía de golpe).
  pico: {
    amas: personas('ama', {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: 120 },
        { duration: '2m', target: 120 },
        { duration: '30s', target: 0 },
      ],
    }),
    gerentes: personas('gerente', {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: 40 },
        { duration: '2m', target: 40 },
        { duration: '30s', target: 0 },
      ],
    }),
  },
  // Carga normal sostenida, para ver si algo crece (memoria, conexiones).
  resistencia: {
    gerentes: personas('gerente', { executor: 'constant-vus', vus: 6, duration: `${DURACION}m` }),
    amas: personas('ama', { executor: 'constant-vus', vus: 12, duration: `${DURACION}m` }),
    propietarios: personas('propietario', { executor: 'constant-vus', vus: 2, duration: `${DURACION}m` }),
  },
}

// ESCALA multiplica cuántos usuarios hay en cada escenario (humo no cambia):
// con 0.2 queda la quinta parte. Sirve para probar sin que la carga crezca de
// más, por ejemplo en una Mac o en un servidor compartido.
const ESCALA = Number(__ENV.ESCALA || 1)

function escalar(escenarios) {
  const n = (x) => (x > 0 ? Math.max(1, Math.round(x * ESCALA)) : 0)
  for (const s of Object.values(escenarios)) {
    if (s.vus) s.vus = n(s.vus)
    if (s.startVUs) s.startVUs = Math.round(s.startVUs * ESCALA)
    if (s.stages) s.stages = s.stages.map((e) => ({ ...e, target: n(e.target) }))
  }
  return escenarios
}

// Minutos que dura cada escenario sin contar la bajada: el token de acceso
// (15 min) tiene que alcanzar, porque se pide una sola vez en setup().
const MINUTOS = { humo: 5, carga: 10, estres: 10, pico: 3, resistencia: DURACION }

if (!ESCENARIOS[ESCENARIO]) {
  throw new Error(`Escenario desconocido: ${ESCENARIO} (${Object.keys(ESCENARIOS).join(', ')})`)
}

// Objetivos propuestos por CometaX (se ajustan con lo que diga el piloto):
// leer en menos de 0.8 s, guardar en menos de 1.5 s, subir una foto en menos
// de 3 s y armar un PDF en menos de 5 s, el 95 % de las veces.
export const options = {
  scenarios: ESCENARIO === 'humo' ? ESCENARIOS.humo : escalar(ESCENARIOS[ESCENARIO]),
  thresholds: {
    http_req_failed: [
      'rate<0.01',
      { threshold: 'rate<0.10', abortOnFail: true, delayAbortEval: '30s' },
    ],
    checks: ['rate>0.99'],
    errores_de_negocio: ['rate<0.01'],
    'http_req_duration{tipo:lectura}': ['p(95)<800'],
    'http_req_duration{tipo:escritura}': ['p(95)<1500'],
    'http_req_duration{tipo:foto}': ['p(95)<3000'],
    'http_req_duration{tipo:pdf}': ['p(95)<5000'],
    'http_req_duration{tipo:estatico}': ['p(95)<500'],
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  setupTimeout: '2m',
}

// -- preparación: una entrada por cuenta ----------------------------------------

function tokensDeFichas() {
  // correr.sh los pasa ya hechos (fichas.py): así dos corridas seguidas no
  // gastan 26 de las 20 entradas por IP que la API deja cada 5 minutos.
  if (!__ENV.FICHAS) return null
  const f = JSON.parse(__ENV.FICHAS)
  const quedan = f.vence - Date.now() / 1000
  if (MINUTOS[ESCENARIO] * 60 > quedan - 30) fail('Los tokens de fichas.py ya no alcanzan; vuelve a correr.')
  return f.tokens
}

export function setup() {
  const correos = ['propietario@picasso.mx']
  for (const s of SUCURSALES) correos.push(`gerente.${s}@picasso.mx`, `ama.${s}@picasso.mx`)

  let tokens = tokensDeFichas()
  if (!tokens) tokens = entrarConTodas(correos)
  return { tokens, cuartos: cuartosPorSucursal(tokens) }
}

function entrarConTodas(correos) {
  if (!CLAVE) fail('Falta PICASSO_CLAVE: correr.sh la toma de picasso/scripts/sembrar.py.')
  const tokens = {}
  let vidaMin = Infinity
  for (const correo of correos) {
    const r = http.post(`${API}/auth/login`, JSON.stringify({ email: correo, password: CLAVE }), {
      headers: JSON_H,
      tags: { name: 'POST /auth/login', tipo: 'entrada' },
    })
    if (r.status === 429) {
      fail('La API frenó las entradas (429): son 20 por IP cada 5 minutos. Espera 5 minutos y vuelve a correr.')
    }
    if (r.status !== 200) fail(`No pude entrar como ${correo}: ${r.status} ${String(r.body).slice(0, 200)}`)
    const d = r.json()
    tokens[correo] = d.access_token || (d.tokens && d.tokens.access_token)
    vidaMin = Math.min(vidaMin, Number(d.expires_in || (d.tokens && d.tokens.expires_in) || 900))
  }
  if (MINUTOS[ESCENARIO] * 60 > vidaMin - 30) {
    fail(
      `El escenario dura ${MINUTOS[ESCENARIO]} min y el token ${Math.round(vidaMin / 60)}. ` +
        'Para una resistencia más larga, sube JFAST_AUTH_ACCESS_LIFETIME_MINUTES en el servidor de prueba (README).',
    )
  }
  return tokens
}

// Los cuartos de cada sucursal, del tablero de su gerente.
function cuartosPorSucursal(tokens) {
  const cuartos = {}
  for (const s of SUCURSALES) {
    const r = http.get(`${API}/tablero`, {
      headers: { Authorization: `Bearer ${tokens[`gerente.${s}@picasso.mx`]}` },
      tags: { name: 'GET /tablero', tipo: 'lectura' },
    })
    if (r.status !== 200) fail(`Tablero de ${s}: ${r.status}`)
    cuartos[s] = r.json().map((h) => h.habitacion_id)
    if (!cuartos[s].length) fail(`La sucursal ${s} no tiene cuartos: ¿se sembró la base?`)
  }
  return cuartos
}

// -- ayudas --------------------------------------------------------------------

function pausa(min, max) {
  sleep((min + Math.random() * (max - min)) * PAUSA)
}

function ok(r, nombre, esperados = [200]) {
  return check(r, { [`${nombre} → ${esperados.join('/')}`]: (x) => esperados.includes(x.status) })
}

function pedir(metodo, ruta, h, nombre, tipo, cuerpo, aceptar422 = false) {
  const params = { headers: h, tags: { name: nombre, tipo } }
  if (aceptar422) params.responseCallback = http.expectedStatuses({ min: 200, max: 299 }, 422)
  const r = http.request(metodo, `${API}${ruta}`, cuerpo === undefined ? null : JSON.stringify(cuerpo), params)
  if (r.status === 422 && aceptar422) {
    if (CHOQUE.test(String(r.body))) choques.add(1)
    else erroresNegocio.add(1)
  } else if (r.status >= 200 && r.status < 300) {
    erroresNegocio.add(0)
  }
  return r
}

const leer = (ruta, h, nombre) => {
  const r = pedir('GET', ruta, h, nombre, 'lectura')
  ok(r, nombre)
  return r
}

function foto(ruta, h, nombre, campos = {}) {
  const r = http.post(`${API}${ruta}`, { foto: http.file(FOTO, 'foto.jpg', 'image/jpeg'), ...campos }, {
    headers: { Authorization: h.Authorization },
    tags: { name: nombre, tipo: 'foto' },
    responseCallback: http.expectedStatuses({ min: 200, max: 299 }, 422),
  })
  if (r.status === 422 && CHOQUE.test(String(r.body))) choques.add(1)
  else ok(r, nombre, [201])
  return r
}

function pdf(ruta, h, nombre) {
  const r = http.get(`${API}${ruta}`, { headers: h, tags: { name: nombre, tipo: 'pdf' }, timeout: '60s' })
  check(r, { [`${nombre} es PDF`]: (x) => x.status === 200 && String(x.body).startsWith('%PDF') })
  return r
}

function encabezados(data, correo) {
  return { ...JSON_H, Authorization: `Bearer ${data.tokens[correo]}` }
}

// Cada usuario virtual queda fijo en una sucursal y un cuarto, para que dos
// del mismo puesto no se pisen la revisión mientras no pasen de 72.
function lugar(data) {
  const n = exec.vu.idInTest - 1
  const s = SUCURSALES[n % SUCURSALES.length]
  const cuartos = data.cuartos[s]
  return { s, cuarto: cuartos[Math.floor(n / SUCURSALES.length) % cuartos.length] }
}

function abrirApp() {
  // La primera vuelta de cada persona abre la PWA (index + JS); luego la
  // tiene en caché el service worker.
  if (exec.vu.iterationInScenario !== 0) return
  const r = http.get(`${URL}/`, { tags: { name: 'GET / (PWA)', tipo: 'estatico' } })
  ok(r, 'GET / (PWA)')
  const js = String(r.body).match(/\/assets\/index-[\w-]+\.js/)
  if (js) http.get(`${URL}${js[0]}`, { tags: { name: 'GET /assets/index.js', tipo: 'estatico' } })
}

function sello() {
  return `[estrés] ${ESCENARIO} vu${exec.vu.idInTest}-${exec.vu.iterationInScenario}`
}

// -- la revisión de un cuarto (gerente o ama) ------------------------------------

function revisar(h, cuarto) {
  const r = pedir('POST', '/revisiones', h, 'POST /revisiones', 'escritura', { habitacion_id: cuarto })
  if (!ok(r, 'POST /revisiones', [201])) return
  const rev = r.json()
  const pendientes = rev.puntos.filter((p) => p.resultado === 'sin_revisar')
  pausa(2, 5)

  // Un día normal: la mayoría de los cuartos sin fallas, algunos con una o dos.
  const nFallas = SIEMPRE ? 1 : Math.random() < 0.6 ? 0 : Math.random() < 0.7 ? 1 : 2
  const fallas = []
  for (let i = 0; i < nFallas && pendientes.length; i++) {
    fallas.push(pendientes.splice(Math.floor(Math.random() * pendientes.length), 1)[0])
  }
  for (const p of fallas) {
    const g = pedir('PUT', `/revisiones/${rev.id}/puntos/${p.codigo}`, h, 'PUT /revisiones/{id}/puntos/{codigo}',
      'escritura', { resultado: 'falla', observacion: `${sello()}: ${p.titulo}` }, true)
    if (g.status === 422) return
    ok(g, 'PUT punto (falla)')
    pausa(3, 8)
    if (toca(0.7)) foto(`/revisiones/${rev.id}/puntos/${p.codigo}/fotos`, h, 'POST foto de punto')
    pausa(2, 5)
  }

  // «Lo demás está bien» si la sucursal lo permite; si no, punto por punto.
  const rb = pedir('POST', `/revisiones/${rev.id}/resto-bien`, h, 'POST /revisiones/{id}/resto-bien', 'escritura',
    undefined, true)
  if (rb.status === 422 && String(rb.body).includes('uno por uno')) {
    erroresNegocio.add(0) // es la regla de la sucursal, no un error
    for (const p of pendientes) {
      const g = pedir('PUT', `/revisiones/${rev.id}/puntos/${p.codigo}`, h, 'PUT /revisiones/{id}/puntos/{codigo}',
        'escritura', { resultado: 'bien' }, true)
      if (g.status === 422) return
      ok(g, 'PUT punto (bien)')
      pausa(0.5, 2)
    }
  } else if (rb.status === 422) {
    return
  } else {
    ok(rb, 'POST resto-bien')
  }
  pausa(1, 3)
  const c = pedir('POST', `/revisiones/${rev.id}/completar`, h, 'POST /revisiones/{id}/completar', 'escritura',
    undefined, true)
  if (c.status !== 422) ok(c, 'POST completar')
}

// -- personas -------------------------------------------------------------------

export function gerente(data) {
  const { s, cuarto } = lugar(data)
  const h = encabezados(data, `gerente.${s}@picasso.mx`)
  abrirApp()
  group('tablero', () => {
    leer('/perfil', h, 'GET /perfil')
    leer('/tablero', h, 'GET /tablero')
    pausa(2, 5)
  })
  group('revisión', () => revisar(h, cuarto))
  group('folios', () => {
    const r = leer('/incidencias?estado=abiertas', h, 'GET /incidencias')
    const lista = r.status === 200 ? r.json() : []
    if (!lista.length) return
    const f = lista[Math.floor(Math.random() * lista.length)]
    leer(`/incidencias/${f.id}`, h, 'GET /incidencias/{id}')
    pausa(3, 8)
    if (toca(0.5)) {
      const a = pedir('POST', `/incidencias/${f.id}/avances`, h, 'POST /incidencias/{id}/avances', 'escritura',
        { nota: `${sello()}: se revisó` }, true)
      if (a.status === 422) return // otro gerente virtual lo cerró
      ok(a, 'POST avance')
    }
    if (toca(0.2)) {
      // Para cerrar, la API pide la foto de la reparación del gerente.
      foto(`/incidencias/${f.id}/fotos`, h, 'POST foto de reparación', { tipo: 'reparacion' })
      pausa(2, 4)
      const c = pedir('POST', `/incidencias/${f.id}/cerrar`, h, 'POST /incidencias/{id}/cerrar', 'escritura',
        { correccion: `${sello()}: quedó corregido` }, true)
      if (c.status !== 422) ok(c, 'POST cerrar folio')
    }
  })
  if (toca(0.1)) {
    group('renta', () => {
      const r = pedir('POST', `/habitaciones/${cuarto}/renta`, h, 'POST /habitaciones/{id}/renta', 'escritura',
        { puede_rentarse: true, motivo: `${sello()}: revisado` })
      ok(r, 'POST renta', [201])
    })
  }
  if (toca(0.1)) group('reporte', () => pdf(`/reportes/habitacion/${cuarto}.pdf`, h, 'GET PDF de cuarto'))
  pausa(5, 15)
}

export function ama(data) {
  const { s, cuarto } = lugar(data)
  const h = encabezados(data, `ama.${s}@picasso.mx`)
  abrirApp()
  group('tablero', () => {
    leer('/tablero', h, 'GET /tablero')
    pausa(2, 5)
  })
  group('revisión', () => revisar(h, cuarto))
  pausa(5, 15)
}

export function propietario(data) {
  const h = encabezados(data, 'propietario@picasso.mx')
  abrirApp()
  group('panel', () => {
    leer('/panel', h, 'GET /panel')
    pausa(3, 10)
    leer('/indicadores', h, 'GET /indicadores')
    pausa(3, 10)
  })
  group('folios', () => {
    leer('/incidencias?estado=abiertas', h, 'GET /incidencias')
    pausa(3, 10)
    const semana = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10)
    leer(`/revisiones?desde=${semana}`, h, 'GET /revisiones')
  })
  if (toca(0.15)) group('reporte', () => pdf('/reportes/grupo.pdf', h, 'GET PDF de grupo'))
  pausa(10, 30)
}
