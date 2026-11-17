// PDF del documento de producto, con la imagen de CometaX Company.
//
//   node docs/producto/generar.cjs
//
// A diferencia de generar-pdfs.cjs, aquí no se arma nada: documento-de-producto.html
// ya trae la portada y las aperturas de sección, y usa la misma hoja pdf-cometax.css
// (así se ve igual en el navegador y en el PDF). Este script solo pone el pie de
// página, cuenta las hojas y escribe docs/pdf/Picasso-Documento-de-producto.pdf.
// Necesita Playwright y Google Chrome (PLAYWRIGHT=/ruta/a/node_modules/playwright si
// no está en FleetOS) y conexión para las fuentes.

const path = require('node:path')
const fs = require('node:fs')

const { chromium } = require(
  process.env.PLAYWRIGHT || path.join(process.env.HOME, 'Documents/GitHub/FleetOS/node_modules/playwright'),
)

const ORIGEN = path.join(__dirname, 'documento-de-producto.html')
const SALIDA = path.join(__dirname, '..', 'pdf', 'Picasso-Documento-de-producto.pdf')
const LOGO = fs.readFileSync(path.join(__dirname, '..', 'img', 'cometax-logo.svg'), 'utf8').trim()
const PIE = 'CometaX Company · Documento de producto · Motel Picasso'

// El mismo pie que los demás PDF: logo, nombre del documento y «n / total».
// Las cajas de margen de @page solo aceptan imágenes, por eso el logo va en data URI.
function reglasDePagina() {
  const svg = LOGO.replace('fill="currentColor"', 'fill="#9a9a9a"').replace('<svg ', '<svg width="14" height="11" ')
  const logo = `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`
  const caja = 'font-family: Barlow, sans-serif; font-size: 7pt; color: #9a9a9a; border-top: 1px solid #e2e2e2; vertical-align: top; padding-top: 6px; margin-top: 0.3in;'
  return `
    @page {
      size: letter;
      margin: 0.55in 0.6in 0.75in;
      @bottom-left { content: url("${logo}") "  ${PIE}"; ${caja} }
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

const contarPaginas = (pdf) => (pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length

;(async () => {
  fs.mkdirSync(path.dirname(SALIDA), { recursive: true })
  const navegador = await chromium.launch({ channel: 'chrome' })
  try {
    const pagina = await navegador.newPage()
    await pagina.emulateMedia({ media: 'print', colorScheme: 'light' })
    const errores = []
    pagina.on('pageerror', (e) => errores.push(e.message))
    pagina.on('requestfailed', (r) => errores.push('no cargó ' + r.url()))
    await pagina.goto('file://' + ORIGEN, { waitUntil: 'networkidle' })
    await pagina.addStyleTag({ content: reglasDePagina() })
    await pagina.evaluate(() => document.fonts.ready)
    await pagina.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0), null, { timeout: 15000 })

    const opciones = { printBackground: true, preferCSSPageSize: true }
    const total = contarPaginas(await pagina.pdf(opciones))
    await pagina.evaluate((n) => { document.querySelector('.pie-portada .paginas').textContent = `1 / ${n}` }, total)
    await pagina.pdf({ ...opciones, path: SALIDA })
    console.log(`${path.basename(SALIDA)} · ${total} págs.${errores.length ? '  ⚠ ' + errores.join(' | ') : ''}`)
  } finally {
    await navegador.close()
  }
})()
