# Picasso Inspecciones — Documentación

La documentación completa (con diagramas, capturas y listas de QA) vive en
`docs/documentacion.html` y publicada en https://claude.ai/artifact/DUPCfdfJkLB26t4iXwFLtQ
(privada: se comparte desde su menú Compartir).

Contenido:

1. **Resumen** — qué es, para quién, pila y estado.
2. **Arquitectura** — PWA → Caddy (HTTPS) → API JFast (módulos `sucursal` e
   `inspeccion`) → PostgreSQL 16, Redis 7 y disco privado de fotos; puertos.
3. **Módulos y código** — dónde vive cada cosa, capas y chequeos de calidad.
4. **Base de datos** — diagrama entidad-relación, diccionario de las 21 tablas y migraciones.
5. **Roles y permisos** — matriz ama / gerente / propietarios / admin.
6. **Reglas de negocio** — las del documento de la dirección, interruptores por sucursal e indicadores.
7. **Flujos** — de la falla al cierre (secuencia) y estados del folio.
8. **API** — rutas agrupadas.
9. **Requerimientos de servidor** — mínimo y recomendado, crecimiento estimado, software, respaldos y monitoreo.
10. **Variables de entorno**, **Despliegue** paso a paso y **Seguridad** (cubierto / pendiente).
11. **Guía de usuario** por puesto, con capturas.
12. **Listas de QA** (46 casos) con casillas.
13. **Pendientes** y **Glosario**.

## PDF

`docs/pdf/` tiene la documentación en PDF con la imagen de CometaX Company (tamaño
carta, mismo estilo que el catálogo de servicios de CometaX):

- `Picasso-Documentacion-completa.pdf`: todo en un solo archivo.
- `Picasso-01-Arquitectura.pdf`: resumen, modelo C4 con logos (contexto, contenedores, componentes), módulo por módulo, flujos, API y arquitectura técnica y escalamiento (más carga, otros clientes, apps de huéspedes).
- `Picasso-02-Base-de-datos.pdf`: diagrama entidad-relación, diccionario y migraciones.
- `Picasso-03-Roles-y-reglas.pdf`: permisos por puesto, reglas de negocio e indicadores.
- `Picasso-04-Servidor-y-despliegue.pdf`: requerimientos, variables, despliegue (con Caddyfile de producción), operación y mantenimiento, seguridad y pendientes.
- `Picasso-05-Guia-de-usuario.pdf`: guía por puesto y glosario.
- `Picasso-06-Listas-de-QA.pdf`: casos con casillas Pasa/Falla y renglón de notas, para llenar a mano.
- **Manual de usuario** (de `docs/manual-usuario.html`, capturas reales en `docs/img/manual/`): `Picasso-Manual-de-usuario.pdf` completo y uno por puesto: `Picasso-Manual-Gerente.pdf`, `-Ama-de-llaves.pdf`, `-Propietarios.pdf` y `-Administracion.pdf`. Solo esos: `node docs/generar-pdfs.cjs Manual`.

- **Producto y entrega** (para la dirección de Picasso): `Picasso-Documento-de-producto.pdf` (de `docs/producto/`, `node docs/producto/generar.cjs`), `Picasso-Folleto-CometaX.pdf` y `Picasso-De-un-vistazo.pdf` (de `docs/marketing/`, `node docs/marketing/generar.cjs`). Los mensajes clave están en `docs/producto/mensajes-clave.md` y los textos para mandarlos (correo y WhatsApp) en `docs/marketing/textos-de-envio.md`. Esas dos notas son internas: no se publican.

Todo está publicado para pruebas en https://2.25.196.39:9631 (`docs/index.html` es la entrada).

Salen del contenido de `docs/documentacion.html` con la hoja `docs/pdf-cometax.css`. Los logos de
las tecnologías están en `docs/img/tech/` (Simple Icons 13.21.0, con su color de marca; `jfast.svg` es el de JFastFramework).
Si se cambia la página, se regeneran con `node docs/generar-pdfs.cjs` (necesita
Playwright y Chrome; ver el encabezado del script). La versión y la fecha de las
portadas están arriba del script.

Para retomar el trabajo técnico: `README.md` (cómo correrlo) (las cuentas de prueba salen de `picasso/scripts/sembrar.py`).
