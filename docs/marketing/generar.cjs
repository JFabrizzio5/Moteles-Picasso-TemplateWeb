// Imprime el folleto de entrega y la hoja «De un vistazo» con la imagen de
// CometaX Company. Las hojas ya vienen armadas en tamaño carta en el HTML
// (folleto.css sobre ../pdf-cometax.css), así que aquí solo se imprimen.
//
//   node docs/marketing/generar.cjs
//
// Salen docs/pdf/Picasso-Folleto-CometaX.pdf, docs/pdf/Picasso-De-un-vistazo.pdf
// y, para mandar por WhatsApp, docs/marketing/Picasso-De-un-vistazo.png.
// Necesita Playwright y Google Chrome (PLAYWRIGHT=/ruta/a/node_modules/playwright
// si no está en FleetOS) y conexión para las fuentes de Google.

const path = require('node:path')
const fs = require('node:fs')

const { chromium } = require(
  process.env.PLAYWRIGHT || path.join(process.env.HOME, 'Documents/GitHub/FleetOS/node_modules/playwright'),
)

const PDF = path.join(__dirname, '..', 'pdf')
const DOCUMENTOS = [
  { origen: 'folleto.html', pdf: 'Picasso-Folleto-CometaX.pdf' },
  { origen: 'de-un-vistazo.html', pdf: 'Picasso-De-un-vistazo.pdf', png: 'Picasso-De-un-vistazo.png' },
]

const contarPaginas = (pdf) => (pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length

;(async () => {
  fs.mkdirSync(PDF, { recursive: true })
  const navegador = await chromium.launch({ channel: 'chrome' })
  try {
    for (const doc of DOCUMENTOS) {
      const pagina = await navegador.newPage({ viewport: { width: 1000, height: 1300 }, deviceScaleFactor: 2 })
      const errores = []
      pagina.on('pageerror', (e) => errores.push(e.message))
      pagina.on('requestfailed', (r) => errores.push(`no cargó ${r.url().split('/').slice(-2).join('/')}`))
      await pagina.emulateMedia({ media: 'print', colorScheme: 'light' })
      await pagina.goto('file://' + path.join(__dirname, doc.origen), { waitUntil: 'networkidle' })
      await pagina.waitForSelector('html[data-iconos="listos"]')
      await pagina.evaluate(() => document.fonts.ready)
      await pagina.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0))

      // Una hoja que se desborda saldría partida en dos páginas.
      const desbordes = await pagina.evaluate(() =>
        [...document.querySelectorAll('.hoja')].map((h, i) => (h.scrollHeight > h.clientHeight + 1 ? i + 1 : 0)).filter(Boolean),
      )
      if (desbordes.length) errores.push(`hojas desbordadas: ${desbordes.join(', ')}`)

      const pdf = await pagina.pdf({ path: path.join(PDF, doc.pdf), printBackground: true, preferCSSPageSize: true })
      if (doc.png) {
        await pagina.emulateMedia({ media: 'screen' })
        await pagina.addStyleTag({ content: 'html,body{background:#fff!important;padding:0!important} .hoja{margin:0!important;box-shadow:none!important;border-radius:0!important}' })
        await pagina.locator('.hoja').first().screenshot({ path: path.join(__dirname, doc.png) })
      }
      console.log(`${doc.pdf} · ${contarPaginas(pdf)} págs.${errores.length ? '  ⚠ ' + errores.join(' | ') : ''}`)
      await pagina.close()
    }
  } finally {
    await navegador.close()
  }
})()
