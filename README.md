# Picasso · Inspecciones

App de reportes de mantenimiento y limpieza para las seis sucursales de Motel
Picasso, según el documento "Reportes Mantenimiento y Limpieza Picasso":
checklist de gerente (25 puntos) y de ama de llaves (29), folios de incidencia
con evidencia y historial, decisión de renta del gerente y panel de propietarios.

- `picasso/`: API en JFastFramework 0.1.0a12 (FastAPI + Postgres + Redis), puerto 9800.
  Módulos `sucursal` (sucursales, habitaciones, personal) e `inspeccion`
  (revisiones, folios, renta, reportes). Cuentas y roles con el plugin `accounts`;
  fotos en el disco privado del plugin `storage` (ligas firmadas que caducan).
- `picasso-web/`: Vue 3 + Vite, puerto 9810. Es una **PWA** (se instala desde el
  navegador, abre sin barra, cachea la app). Estética de motelpicasso.mx: barra
  negra con su logo, Barlow Semi Condensed, Open Sans y coral #FE7877.

Reportes PDF (reportlab, con la marca): `/reportes/revision/{id}.pdf`,
`/reportes/incidencia/{id}.pdf`, `/reportes/habitacion/{id}.pdf` y
`/reportes/grupo.pdf?desde&hasta`, con los mismos permisos que las pantallas.
Código en `picasso/modules/inspeccion/services/pdf/`.

Las cuentas de prueba las crea `picasso/scripts/sembrar.py`, con la contraseña de `PICASSO_CLAVE_DEMO`. En los builds de demo (`npm run dev` y
`npm run movil`) la entrada trae accesos de un toque por puesto (`VITE_DEMO`).

## Correr en local

```bash
# Datos (docker compose no pudo crear su red en esta Mac: "all predefined
# address pools have been fully subnetted", así que van en la red por defecto)
docker start picasso-database picasso-cache

# API
cd picasso && .venv/bin/jfast exec -- .venv/bin/jfast serve

# Front
cd picasso-web && npm run dev
```

Primera vez: `cd picasso && .venv/bin/jfast exec -- .venv/bin/alembic upgrade head`
y luego, con la API arriba, `PYTHONPATH=. .venv/bin/jfast exec -- .venv/bin/python scripts/sembrar.py`
(datos de ejemplo; no son reales).

Chequeos: `cd picasso && .venv/bin/ruff check . && .venv/bin/mypy . && .venv/bin/pytest -q && .venv/bin/jfast contracts check`.

## Equipo de cada cuarto

Catálogo configurable (Ajustes → Catálogo de equipo): Entretenimiento (Televisión,
Netflix, YouTube…), Mobiliario especial (sillón tántrico, potro, columpio…), Confort y
Baño. La administración marca qué tiene cada cuarto (Ajustes → Cuartos → Equipo) y cada
cosa entra al checklist de ese cuarto en la sección «Equipo del cuarto»: el gerente
revisa que funcione y la ama que esté limpio. Datos de ejemplo:
`scripts/equipo_demo.py` (también crea la cuenta de administración de la demo).

## Folios por prioridad

En Folios hay chips de prioridad (alta, media, baja) con su conteo y la tabla
«Estado por prioridad» (filas: prioridad; columnas: reportadas, en atención,
cerradas, todas): cada número filtra el listado. La prioridad va en la dirección
(`?prioridad=alta`) igual que los demás filtros, y cada tarjeta lleva una franja del
color de su prioridad. El panel de propietarios desglosa las abiertas por prioridad.
API: `GET /incidencias?prioridad=` y `GET /incidencias/conteo` (folios por estado y
prioridad con los mismos filtros de sucursal, fecha y búsqueda, sin el tope de 300 del
listado). Los folios nacen en prioridad media; la cambia el gerente en el folio.

## Reglas del documento y dónde viven

Todas en `picasso/modules/inspeccion/validations/inspeccion_validation.py`:
Sin revisar nunca cuenta como Bien; No aplica pide motivo (y si la habitación no
tiene jacuzzi/alberca/sauna/terraza, el sistema lo marca solo); Falla pide
observación y abre folio `PIC-<SUC>-000001` o se vincula al abierto de la misma
falla en ese cuarto; para enviar/terminar no puede quedar nada sin revisar; solo
el gerente decide la renta y cierra, y cerrar exige foto de reparación tomada por
el gerente y la explicación. El historial solo se agrega.

**Reglas sin confirmar**, como interruptor por sucursal en Ajustes (admin):
- Frecuencia del gerente: diaria / cada 2 / cada 3 días (el documento dice "diaria o cada dos días").
- Exigibles de ama de llaves: una por limpieza (cada revisión abierta debe enviarse) o una por cuarto al día.
- Checklist «solo lo que está mal» (por defecto): se toca únicamente lo que falla y al
  terminar lo demás queda Bien; si se apaga, cada punto lleva ✓/✗. La hora del último
  chequeo de cada cuarto sale en el inicio, en el checklist y en el panel. El documento pide revisar punto por punto, así
  que esos puntos quedan como `en_bloque` y salen así en pantalla y en el PDF.

## Celular: PWA ahora, Capacitor después

La PWA ya cubre cámara (`capture="environment"`), instalación y uso con poca
señal (cada punto se guarda al tocarlo; sin señal queda en cola y se reintenta).
Si después hace falta tienda de apps, cámara forzada (sin galería) o push en
iPhone sin instalar, el mismo `picasso-web` se envuelve con Capacitor sin reescribir.

Para probar en un teléfono: `npm run movil` en `picasso-web` compila la app y la
sirve en :9811 con `/api` y `/storage` redirigidos a la API, todo en una sola
dirección. En la misma Wi-Fi se abre `http://<IP de la Mac>:9811`. Así funciona
todo menos instalarla como app: eso pide HTTPS (un túnel o un servidor con
certificado).

En pantalla grande, la entrada y Perfil muestran un **código QR** para abrir la app en el
celular (`components/QrCelular.vue`, librería `qrcode` cargada solo ahí). Apunta a
`/login` del mismo sitio que se está viendo. La presentación y el índice de la
documentación usan un QR fijo (`docs/img/qr-app.svg`, `docs/presentacion/assets/qr-app.svg`)
hacia la app del VPS; si cambia la dirección, se regenera con
`node -e "require('./picasso-web/node_modules/qrcode').toFile('docs/img/qr-app.svg', '<url>/login', {type:'svg', margin:0})"`.

## Prueba en el VPS de prueba (desde 2026-11-12)

- App: https://2.25.196.39:9630 · Documentación: https://2.25.196.39:9631 ·
  Presentación (landing 3D para los dueños): https://2.25.196.39:9631/presentacion/
- La app del VPS se compila en modo `vps` (`picasso-web/.env.vps`): como producción, pero
  con los **accesos de demo de un toque** (las 14 cuentas de ejemplo) y, en la entrada y en
  Perfil, el bloque «Conoce el proyecto» (video, documentación y manual, servidos desde :9631).
  La contraseña de demo queda en el JS: solo para este servidor de prueba.
- `admin.demo@picasso.mx` no la crea `sembrar.py` sino `scripts/equipo_demo.py`; en el VPS se
  dio de alta a mano el 2026-11-16 (solo la cuenta, sin el equipo de los cuartos).
- Está en `<ruta-en-el-servidor>/Picasso` del VPS compartido, con los datos de
  `scripts/sembrar.py` (la contraseña de las cuentas de demo va en `PICASSO_CLAVE_DEMO`
  y en `VITE_DEMO_CLAVE`; no está en el repo).
- Usa los tres compose: el `.env` del servidor fija
  `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml:docker-compose.vps.yml`.
- El HTTPS lo pone el Caddy del servidor, que ya tiene el certificado de la
  IP: pedir otro para la misma IP gastaría el límite semanal de Let's Encrypt.
  Su Caddyfile pasa 9630 y 9631 al Caddy de Picasso por la red `picasso-proxy`.
  Los respaldos de sus archivos quedaron como `*.antes-picasso-20261112*`.
- Por compartir servidor con otro sistema en producción, Picasso tiene topes de
  CPU y memoria (ver `docker-compose.vps.yml`).

Para subir cambios:

```bash
# front: compilar aparte (picasso-web/dist lo usa el túnel de npm run movil)
cd picasso-web && npx vite build --mode vps --outDir /tmp/picasso-dist && cd ..
rsync -az --delete -e ssh /tmp/picasso-dist/ <usuario>@<servidor>:<ruta-en-el-servidor>/Picasso/picasso-web/dist/
# API: subir el código y reconstruir (las migraciones corren solas al arrancar)
rsync -az -e ssh --exclude .venv --exclude storage --exclude .env picasso/ <usuario>@<servidor>:<ruta-en-el-servidor>/Picasso/picasso/
ssh <usuario>@<servidor> 'cd <ruta-en-el-servidor>/Picasso && docker compose up -d --build'
# documentación, video y presentación (docs/presentacion/): sin las notas internas (*.md) ni los generadores (*.cjs)
rsync -az --delete -e ssh --exclude '*.md' --exclude '*.cjs' docs/ <usuario>@<servidor>:<ruta-en-el-servidor>/Picasso/docs/
```

Volver a sembrar dentro del contenedor necesita `/app` en el `PYTHONPATH`:
`docker compose exec -e PYTHONPATH=/app picasso python scripts/sembrar.py`.

## Pruebas de estrés

En `pruebas-estres/` (ver su README): `jfast bench` para las consultas y k6 en
Docker para el trabajo real del personal (revisiones con fotos, folios, PDF).
Escenarios `humo`, `carga`, `estres`, `pico` y `resistencia`. Por omisión van
contra una copia en Docker con topes de CPU y memoria (`pruebas-estres/local/`,
http://127.0.0.1:9850), no contra el VPS.

## Pendiente

- Habitaciones y personal reales (hoy 101–112 inventadas por sucursal).
- Servidor definitivo con dominio y respaldo automático de la base y de `storage/`.
- Notificaciones (ej. al gerente cuando el ama de llaves envía con fallas).
