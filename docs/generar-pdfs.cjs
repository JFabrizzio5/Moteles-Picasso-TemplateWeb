// Genera los PDF de la documentación con la imagen de CometaX Company, a partir
// del contenido de documentacion.html (y del manual de usuario, manual-usuario.html)
// y la hoja de estilos pdf-cometax.css.
//
//   node docs/generar-pdfs.cjs            todos
//   node docs/generar-pdfs.cjs Manual     solo los que llevan «Manual» en el nombre
//
// Necesita Playwright y Google Chrome instalados. Si Playwright no está en este
// proyecto, se indica dónde está con PLAYWRIGHT=/ruta/a/node_modules/playwright.
// Los diagramas (mermaid) y las fuentes se bajan de internet: hace falta conexión.
// Salen en docs/pdf/: uno con todo y uno por tema; del manual, uno completo y uno por puesto.

const path = require('node:path')
const fs = require('node:fs')

const { chromium } = require(
  process.env.PLAYWRIGHT || path.join(process.env.HOME, 'Documents/GitHub/FleetOS/node_modules/playwright'),
)

const ORIGEN = path.join(__dirname, 'documentacion.html')
const MANUAL = path.join(__dirname, 'manual-usuario.html')
const ESTILOS = path.join(__dirname, 'pdf-cometax.css')
const SALIDA = path.join(__dirname, 'pdf')
const LOGO = fs.readFileSync(path.join(__dirname, 'img/cometax-logo.svg'), 'utf8').trim()

const EMPRESA = 'CometaX Company'
// Franja «Construido con» de la portada (archivos en img/tech/).
const PILA = ['vuedotjs', 'vite', 'tailwindcss', 'pwa', 'python', 'fastapi', 'jfast', 'sqlalchemy', 'pydantic', 'postgresql', 'redis', 'docker', 'caddy', 'ubuntu']
const CLIENTE = 'Motel Picasso'
const VERSION = '0.1'
const FECHA = '17 de noviembre de 2026'
const MES = 'noviembre 2026'

const FUENTES =
  'https://fonts.googleapis.com/css2?family=Archivo+Black&family=Barlow+Condensed:wght@600;700;800&family=Barlow:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap'

// Paleta de los diagramas: la del catálogo de CometaX.
const TEMA_DIAGRAMAS = {
  css: FUENTES,
  fuente: 'Barlow',
  colores: {
    fondo: '#ffffff', caja: '#f3f0eb', tinta: '#141414', borde: '#6e6e6e', linea: '#3d3d3d',
    suave: '#f6eaea', grupo: '#faf8f5', grupoBorde: '#e2e2e2', acento: '#6e1014',
  },
}

// Cifras de la portada y texto de cierre: los de la documentación técnica salvo
// que el documento traiga los suyos.
const CIFRAS = [
  ['6', 'Sucursales', 'Lerma, Toluca, Circuito, Churubusco, Periférico y Vaqueritos'],
  ['4', 'Puestos', 'Ama de llaves, gerente, propietarios y administración'],
  ['54', 'Puntos de checklist', '25 del gerente y 29 de ama de llaves, más el equipo de cada cuarto'],
  ['29', 'Tablas', 'PostgreSQL 16, con migraciones de Alembic'],
]
const CIFRAS_MANUAL = [
  ['6', 'Sucursales', 'De Lerma a Vaqueritos'],
  ['4', 'Puestos', 'Cada uno ve lo suyo'],
  ['54', 'Puntos', '25 del gerente y 29 de ama de llaves'],
  ['5', 'Pasos de un folio', 'De la falla a su cierre'],
]
const CIERRE = (doc) =>
  `Documento elaborado por ${EMPRESA} para ${CLIENTE}. Describe la versión ${VERSION} del sistema al ${doc.fecha || FECHA}: una demo que corre en local con datos de ejemplo y que todavía no está desplegada en un servidor.`
const CIERRE_MANUAL = (doc) =>
  `Manual elaborado por ${EMPRESA} para el personal de ${CLIENTE}. Corresponde a la versión ${VERSION} de la app al ${doc.fecha}. Las pantallas usan datos de ejemplo: los nombres, cuartos y folios que aparecen no son reales.`
const MANUAL_BASE = { origen: MANUAL, fecha: '17 de noviembre de 2026', cifras: CIFRAS_MANUAL, cierre: CIERRE_MANUAL }

const DOCUMENTOS = [
  {
    archivo: 'Picasso-Documentacion-completa.pdf',
    nombre: 'Documentación del sistema',
    titulo: 'Documentación del sistema',
    texto: 'Arquitectura, base de datos, reglas, finanzas, servidor, guía de usuario y listas de QA de la app de inspecciones de mantenimiento y limpieza de las seis sucursales.',
    secciones: null,
  },
  {
    archivo: 'Picasso-01-Arquitectura.pdf',
    nombre: 'Arquitectura',
    titulo: 'Arquitectura del sistema',
    texto: 'Modelo C4 con logos, módulo por módulo, el flujo de una falla hasta su cierre, las rutas de la API y cómo crece el sistema para más carga, otros clientes y apps de huéspedes.',
    secciones: ['resumen', 'arquitectura', 'modulos', 'flujos', 'api', 'escala'],
  },
  {
    archivo: 'Picasso-07-Finanzas.pdf',
    nombre: 'Finanzas',
    titulo: 'Finanzas',
    texto: 'Ingresos leídos cada noche de Kairos, gastos desglosados con comprobante y ligados a folios, auditoría, exportación a contabilidad y reporte PDF: módulo, tablas, tarea nocturna, permisos y rutas.',
    secciones: ['finanzas'],
  },
  {
    archivo: 'Picasso-02-Base-de-datos.pdf',
    nombre: 'Base de datos',
    titulo: 'Base de datos',
    texto: 'Diagrama entidad-relación, diccionario de tablas y migraciones de PostgreSQL.',
    secciones: ['datos'],
  },
  {
    archivo: 'Picasso-03-Roles-y-reglas.pdf',
    nombre: 'Roles y reglas',
    titulo: 'Roles y reglas de negocio',
    texto: 'Quién puede hacer qué en la app, las reglas que el sistema hace cumplir, los interruptores por sucursal y cómo se calculan los indicadores.',
    secciones: ['roles', 'reglas'],
  },
  {
    archivo: 'Picasso-04-Servidor-y-despliegue.pdf',
    nombre: 'Servidor y despliegue',
    titulo: 'Servidor y despliegue',
    texto: 'Requerimientos de servidor, crecimiento estimado, variables de entorno, instalación paso a paso, operación diaria, seguridad y pendientes antes de producción.',
    secciones: ['servidor', 'entorno', 'despliegue', 'operacion', 'seguridad', 'pendientes'],
  },
  {
    archivo: 'Picasso-05-Guia-de-usuario.pdf',
    nombre: 'Guía de usuario',
    titulo: 'Guía de usuario',
    texto: 'Qué hace cada puesto en la app (ama de llaves, gerente, propietarios y administración), paso a paso y con capturas.',
    secciones: ['guia', 'glosario'],
  },
  {
    archivo: 'Picasso-06-Listas-de-QA.pdf',
    nombre: 'Listas de QA',
    titulo: 'Listas de QA',
    texto: 'Casos de prueba por área, con casilla de Pasa o Falla y renglón para notas. Se imprimen y se llenan a mano antes de liberar.',
    secciones: ['qa'],
  },
  {
    ...MANUAL_BASE,
    archivo: 'Picasso-Manual-de-usuario.pdf',
    nombre: 'Manual de usuario',
    titulo: 'Manual de usuario',
    texto: 'Cómo se usa la app de inspecciones, paso a paso y con pantallas reales: gerente, ama de llaves, propietarios, administración y finanzas, qué hacer sin señal y problemas comunes.',
    secciones: null,
  },
  {
    ...MANUAL_BASE,
    archivo: 'Picasso-Manual-Gerente.pdf',
    nombre: 'Manual del gerente',
    titulo: 'Manual del gerente',
    texto: 'Revisar cuartos, marcar lo que está mal con foto, decidir la renta, llevar cada folio hasta cerrarlo con la foto de la reparación y registrar los gastos de la sucursal.',
    secciones: ['primeros', 'gerente', 'finanzas', 'sin-senal', 'problemas'],
  },
  {
    ...MANUAL_BASE,
    archivo: 'Picasso-Manual-Ama-de-llaves.pdf',
    nombre: 'Manual de ama de llaves',
    titulo: 'Manual de ama de llaves',
    texto: 'Revisar el cuarto al terminar de limpiar: tocar solo lo que está mal, con foto, y enviarlo al gerente. También sin señal.',
    secciones: ['primeros', 'ama', 'sin-senal', 'problemas'],
  },
  {
    ...MANUAL_BASE,
    archivo: 'Picasso-Manual-Propietarios.pdf',
    nombre: 'Manual de propietarios',
    titulo: 'Manual de propietarios',
    texto: 'Las seis sucursales en una sola vista: avance de revisiones, folios abiertos, cuartos sin rentar, indicadores, finanzas y los reportes en PDF.',
    secciones: ['primeros', 'propietarios', 'finanzas', 'problemas'],
  },
  {
    ...MANUAL_BASE,
    archivo: 'Picasso-Manual-Administracion.pdf',
    nombre: 'Manual de administración',
    titulo: 'Manual de administración',
    texto: 'Reglas de cada sucursal, alta de cuartos y de su equipo, catálogo de equipo, alta del personal y gastos para contabilidad.',
    secciones: ['primeros', 'admin', 'finanzas', 'problemas'],
  },
  {
    ...MANUAL_BASE,
    archivo: 'Picasso-Manual-Finanzas.pdf',
    nombre: 'Manual de finanzas',
    titulo: 'Manual de finanzas',
    texto: 'Registrar gastos cosa por cosa con su comprobante, cargarlos a folios, ver los ingresos de Kairos, exportar los gastos a contabilidad, auditarlos e imprimir el reporte.',
    secciones: ['primeros', 'finanzas', 'problemas'],
  },
]

// Logo para el pie de página (las cajas de margen de @page solo aceptan imágenes).
function logoComoImagen(color) {
  const svg = LOGO.replace('fill="currentColor"', `fill="${color}"`).replace('<svg ', '<svg width="14" height="11" ')
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`
}

function reglasDePagina(doc) {
  const caja = `font-family: Barlow, sans-serif; font-size: 7pt; color: #9a9a9a; border-top: 1px solid #e2e2e2; vertical-align: top; padding-top: 6px; margin-top: 0.3in;`
  return `
    @page {
      size: letter;
      margin: 0.55in 0.6in 0.75in;
      @bottom-left { content: url("${logoComoImagen('#9a9a9a')}") "  ${EMPRESA} · ${doc.nombre} · ${CLIENTE}"; ${caja} }
      @bottom-center { content: ""; ${caja} }
      @bottom-right { content: counter(page) " / " counter(pages); ${caja} }
    }
    @page :first {
      margin: 0;
      @bottom-left { content: none; border: 0; }
      @bottom-center { content: none; border: 0; }
      @bottom-right { content: none; border: 0; }
    }`
}

async function armar(pagina, doc) {
  const cifras = doc.cifras || CIFRAS
  const cierre = (doc.cierre || CIERRE)(doc)
  const { origen, cifras: _cifras, cierre: _cierre, fecha, ...plano } = doc
  await pagina.evaluate(
    ({ doc, LOGO, EMPRESA, CLIENTE, VERSION, MES, PILA, cifras, cierre }) => {
      const logo = (clase) => LOGO.replace('<svg ', `<svg class="${clase}" aria-hidden="true" `)

      // Solo las secciones de este documento, numeradas desde 01.
      const partes = [...document.querySelectorAll('section.parte')].filter((s) => !doc.secciones || doc.secciones.includes(s.id))
      const indice = []
      partes.forEach((s, i) => {
        const n = String(i + 1).padStart(2, '0')
        const etiqueta = s.querySelector(':scope > .etiqueta')
        const h2 = s.querySelector(':scope > h2')
        const tema = etiqueta?.textContent.trim() || s.id
        const subtemas = [...s.querySelectorAll('h3, .qa-grupo')].map((h) => h.textContent.trim())
        indice.push({ n, tema, titulo: h2?.textContent.trim() || '', subtemas })
        const cabeza = document.createElement('div')
        cabeza.className = 'cabeza-int'
        cabeza.innerHTML = `<span class="sec-num">${n}</span><div class="sec-tit"><span class="sec-tema">${tema}</span></div><div class="sec-marca">${logo('logo-sec')}<small>${CLIENTE} · Inspecciones</small></div>`
        if (h2) cabeza.querySelector('.sec-tit').appendChild(h2)
        etiqueta?.remove()
        s.prepend(cabeza)
      })

      // Encabezado de tabla que se repite en cada hoja.
      for (const tabla of document.querySelectorAll('table')) {
        const primera = tabla.querySelector('tr')
        if (!primera || tabla.tHead || !primera.querySelector('th')) continue
        tabla.createTHead().appendChild(primera)
      }
      // Las imágenes con carga diferida no se bajarían al imprimir.
      for (const img of document.querySelectorAll('img')) img.loading = 'eager'

      const portada = `
        <section class="portada">
          <header class="hero">
            <div class="hero-top">
              <div class="marca">${logo('logo-cx')}<span class="nombre">COMETAX<small>cometax.click</small></span></div>
              <div class="cliente"><span class="para">Preparado para</span><img src="img/logo.svg" alt="${CLIENTE}"><span class="sub">Sistema de inspecciones · ${MES}</span></div>
            </div>
            <h1>${doc.titulo}</h1>
            <div class="hero-pie"><p>${doc.texto}</p><div class="pastilla">Versión <span>${VERSION}</span></div></div>
            <div class="hero-stack"><span class="rot">Construido con</span>${PILA.map((t) => `<img src="img/tech/${t}.svg" alt="${t}">`).join('')}</div>
          </header>
          <div class="cuerpo">
            <div class="seccion"><div class="num">${String(indice.length).padStart(2, '0')}</div><div class="titulo">Contenido</div></div>
            <ol class="contenido${indice.length < 3 ? ' una-col' : indice.length > 8 ? ' tres-col' : ''}">
              ${indice.map((x) => `<li><span class="n">${x.n}</span><span class="t">${x.tema}</span><span class="d">${x.titulo}${indice.length <= 6 && x.subtemas.length ? ' — ' + x.subtemas.join(' · ') : ''}</span></li>`).join('')}
            </ol>
            <div class="ficha">
              <div><span class="rotulo">Cliente</span><b>${CLIENTE}</b><span class="extra">Lerma, Toluca, Circuito, Churubusco, Periférico y Vaqueritos</span></div>
              <div><span class="rotulo">Proyecto</span><b>App de inspecciones</b><span class="extra">Mantenimiento y limpieza por cuarto</span></div>
              <div><span class="rotulo">Elaboró</span><b>${EMPRESA}</b><span class="extra">cometax.click</span></div>
            </div>
            ${indice.length <= 6 ? `
            <div class="cifras">
              ${cifras.map(([n, b, extra]) => `<div><span class="cifra">${n}</span><b>${b}</b><span class="extra">${extra}</span></div>`).join('')}
            </div>` : ''}
          </div>
          <div class="cierre">
            <div class="t">${EMPRESA}</div>
            <p>${cierre}</p>
            <div class="lema"><b>CometaX — Tecnología diseñada para resolver, evolucionar y escalar.</b><span>${logo('logo-cx')}cometax.click</span></div>
          </div>
          <footer class="pie-portada"><span>${logo('logo-chico')}${EMPRESA} · ${doc.nombre} · ${CLIENTE}</span><span class="paginas">1</span></footer>
        </section>`

      // Cuerpo nuevo: portada (con el cierre de CometaX abajo) y secciones. Se van los estilos de la página web;
      // se queda #estilo-pdf, la hoja que una página trae solo para su PDF (la del manual).
      document.querySelectorAll('head > style:not(#estilo-pdf)').forEach((e) => e.remove())
      const main = document.createElement('main')
      main.className = 'doc'
      partes.forEach((s) => main.appendChild(s))
      document.body.className = ''
      document.body.innerHTML = portada
      document.body.appendChild(main)
      document.title = `${doc.titulo} · ${CLIENTE} · ${EMPRESA}`
    },
    { doc: plano, LOGO, EMPRESA, CLIENTE, VERSION, MES, PILA, cifras, cierre },
  )
  await pagina.addStyleTag({ path: ESTILOS })
  await pagina.addStyleTag({ content: reglasDePagina(doc) })
  await pagina.evaluate(() => document.fonts.ready)
  await pagina.waitForFunction(() => [...document.images].every((i) => i.complete))
}

// Chrome escribe un objeto /Type /Page por hoja.
const contarPaginas = (pdf) => (pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length

;(async () => {
  fs.mkdirSync(SALIDA, { recursive: true })
  const navegador = await chromium.launch({ channel: 'chrome' })
  try {
    const filtro = process.argv[2]
    for (const doc of DOCUMENTOS.filter((d) => !filtro || d.archivo.includes(filtro))) {
      const pagina = await navegador.newPage()
      await pagina.emulateMedia({ media: 'print', colorScheme: 'light' })
      await pagina.addInitScript((tema) => { window.TEMA_DIAGRAMAS = tema }, TEMA_DIAGRAMAS)
      const errores = []
      pagina.on('pageerror', (e) => errores.push(e.message))
      await pagina.goto('file://' + (doc.origen || ORIGEN), { waitUntil: 'networkidle' })
      if (await pagina.$('.diagrama')) await pagina.waitForSelector('html[data-diagramas="listos"]', { timeout: 30000 })
      const diagramas = await pagina.evaluate((ids) =>
        [...document.querySelectorAll('section.parte')].filter((s) => !ids || ids.includes(s.id)).flatMap((s) => [...s.querySelectorAll('.diagrama')]).map((d) => !!d.querySelector('svg')),
      doc.secciones)
      if (diagramas.includes(false)) errores.push(`diagramas sin dibujar: ${diagramas.filter((x) => !x).length}`)
      await armar(pagina, doc)

      // Dos pasadas: la primera cuenta las hojas para el pie de la portada.
      const opciones = { printBackground: true, preferCSSPageSize: true }
      const total = contarPaginas(await pagina.pdf(opciones))
      await pagina.evaluate((n) => { document.querySelector('.pie-portada .paginas').textContent = `1 / ${n}` }, total)
      await pagina.pdf({ ...opciones, path: path.join(SALIDA, doc.archivo) })
      console.log(`${doc.archivo} · ${total} págs.${errores.length ? '  ⚠ ' + errores.join(' | ') : ''}`)
      await pagina.close()
    }
  } finally {
    await navegador.close()
  }
})()
