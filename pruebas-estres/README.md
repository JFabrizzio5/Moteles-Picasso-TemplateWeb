# Pruebas de carga y estrés

Dos herramientas, una para cada pregunta:

| Pregunta | Herramienta | Escribe datos |
|---|---|---|
| ¿Hasta cuántas consultas aguanta? | `lecturas.sh` → `jfast bench` (viene con JFast) | No |
| ¿Aguanta al personal trabajando de verdad (revisiones, fotos, folios, PDF)? | `correr.sh` → k6 (`k6/picasso.js`) | Sí |

k6 corre en Docker (`grafana/k6:2.3.0`, con tope de 1 CPU y 384 MB): no hay
nada que instalar. `jfast bench` viene en el entorno de la API
(`picasso/.venv`).

## Dónde se corre: la copia en Docker

Por omisión todo va contra una **copia de Picasso en Docker en la Mac**
(`local/`): proyecto `picasso-estres`, con su propia base, fotos y Redis.
Usa los mismos compose de producción más `local/docker-compose.estres.yml`,
que le pone topes:

| Contenedor | CPU | Memoria |
|---|---|---|
| API (2 procesos) | 2 | 768 MB |
| Worker | 0.5 | 384 MB |
| PostgreSQL | 1.5 | 768 MB |
| Redis | 0.25 | 128 MB |
| Caddy | 0.5 | 128 MB |

Con esos topes, el resultado equivale a un servidor chico de 2 vCPU y nada se
come la Mac. La red va en una subred fija (`10.231.0.0/24`), porque Docker en
esta Mac ya no tiene subredes libres.

```bash
cd pruebas-estres
./local/levantar.sh           # construye, levanta y siembra (http://127.0.0.1:9850)
./lecturas.sh                 # solo consultas, por escalones 1, 4, 16 y 64
./correr.sh humo              # una vuelta de cada puesto: ¿funciona el guion?
./correr.sh carga             # un cambio de turno normal, 10 min
ESCALA=0.2 ./correr.sh estres # sube hasta que algo cede, 10 min (aquí, al 20 %)
ESCALA=0.25 ./correr.sh pico  # entran todos de golpe, 3 min (aquí, al 25 %)
./correr.sh resistencia       # carga normal sostenida (DURACION=12 min)
./local/bajar.sh              # borra la copia: contenedores, base y fotos
```

`ESCALA` multiplica cuántos usuarios hay (humo no cambia): con 0.2 queda la
quinta parte. Así se prueba sin que la carga crezca de más. Para empezar con
la base limpia entre corridas: `./local/bajar.sh && ./local/levantar.sh`.

Otros destinos, solo si se piden por nombre: `vps` (el de prueba,
`https://2.25.196.39:9630`), `local` (la API de desarrollo en `:9800`) o una
URL, que además pide `CONFIRMO=si` porque la prueba escribe datos.

### Si alguna vez se corre en el VPS

Antes de una corrida que escribe en el VPS, guarda la base; al terminar,
regrésala a como estaba:

```bash
ssh <usuario>@<servidor> <ruta-en-el-servidor>/Picasso/pruebas-estres/servidor/foto-base.sh
ESCALA=0.2 ./correr.sh estres vps
ssh <usuario>@<servidor> <ruta-en-el-servidor>/Picasso/pruebas-estres/servidor/restaurar-base.sh
```

`restaurar-base.sh` detiene la API unos segundos, restaura el respaldo más
reciente y borra las fotos que llegaron después de la marca. Probado el
2026-11-12: la base regresó a 134 revisiones y 28 folios, y se borraron las
5 fotos de la prueba.

## Qué simula cada persona

| Puesto | Qué hace en cada vuelta |
|---|---|
| Gerente | Abre la PWA (solo la 1.ª vuelta), perfil y tablero → revisión de su cuarto: de 0 a 2 fallas, foto en el 70 %, «lo demás bien» (o punto por punto si la sucursal lo pide) y enviar → folios: ve uno, avance en el 50 %, foto de reparación y cierre en el 20 % → decisión de renta en el 10 % → PDF del cuarto en el 10 % |
| Ama de llaves | Tablero → revisión de 29 puntos con el mismo reparto de fallas y fotos → enviar |
| Propietarios | Panel → indicadores → folios abiertos → revisiones de la semana → PDF de grupo en el 15 % |

- Entre acciones hay pausas de persona (de 2 a 15 s). `PAUSA` las multiplica: en `estres` va a 0.15 y en `pico` a 0.3.
- En `humo` se recorren todos los caminos siempre: falla, foto, cierre de folio, renta y los dos PDF.
- La foto (`k6/foto.jpg`) pesa 239 KB, lo que manda el celular después de comprimir.
- Todo lo que se escribe lleva `[estrés]` en el texto.

| Escenario | Gerentes | Amas | Propietarios | Duración |
|---|---|---|---|---|
| humo | 1 | 1 | 1 | 1 vuelta |
| carga | 6 | 12 | 2 | 10 min |
| estres | 2 → 75 | 4 → 150 | 1 → 10 | 10 min, por escalones de 2 min |
| pico | 0 → 40 en 15 s | 0 → 120 en 15 s | 0 | 3 min |
| resistencia | 6 | 12 | 2 | `DURACION` (12 min) |

La carga real que se espera es de unas 720 revisiones al día y menos de una
petición por segundo. `estres` y `pico` van muy por encima a propósito.

## Objetivos (los umbrales de k6)

Son una propuesta de CometaX y se ajustan con lo que mida el piloto. Se cumplen
si el 95 % de las peticiones queda debajo de:

| Tipo | p95 |
|---|---|
| Consulta (`lectura`) | 0.8 s |
| Guardar (`escritura`) | 1.5 s |
| Subir foto (`foto`) | 3 s |
| PDF (`pdf`) | 5 s |
| PWA (`estatico`) | 0.5 s |

También: menos del 1 % de errores y más del 99 % de los `checks` bien. Si los
errores pasan del 10 %, k6 se detiene solo después de 30 s, porque ya se
encontró el límite.

## Cómo leer el resultado

Cada corrida deja una carpeta en `resultados/<fecha>-<escenario>-<destino>/`:

- `salida.txt`: el resumen de k6, con cada umbral en ✓ o ✗ y los tiempos por tipo.
- `resumen.json`: lo mismo, para comparar corridas.
- `reporte.html`: las gráficas de toda la corrida. k6 no lo genera cuando la corrida es muy corta, como `humo`.

En `estres`, el número que importa es cuántos usuarios había cuando el p95 o
los errores cruzaron su umbral: hasta ahí llega un servidor de ese tamaño. En
`lecturas.sh`, `jfast bench` lo dice en una línea («Broke at…» o «Did not
break up to…») y revisa `/ready` después de cada escalón para decir qué
dependencia cedió (base, Redis).

Hay dos métricas propias:
- `choques_misma_revision`: dos usuarios del mismo puesto en el mismo cuarto. Con más de 72 por puesto pasa: uno envía la revisión y al otro la API le contesta «ya se cerró». Es esperado y no cuenta como error.
- `errores_de_negocio`: cualquier otro 422. Debe quedar en 0.

## Cuidados

- **Solo contra una base de prueba.** La prueba crea revisiones, folios y fotos. Nunca contra la base real de Picasso.
- **El VPS es compartido con otro sistema en producción.** Por eso las pruebas van contra la copia en Docker. `docker-compose.vps.yml` le pone topes a Picasso: la API con 2 CPU y 2 procesos, el worker con 1, Postgres con 2 y Redis con 0.5, más su memoria. Si alguna vez se corre ahí, que sea con `ESCALA` baja y en horas tranquilas.
- **Desde dónde se corre.** Desde la Mac o desde otro servidor, nunca desde el mismo VPS: el generador le quitaría CPU a lo que se mide. Si la red de la Mac es lenta, el límite que se ve puede ser la subida de fotos. Para separar eso, corre `lecturas.sh`, que no sube nada.
- **Entradas.** La API deja 20 entradas por IP cada 5 minutos y cada corrida usa 13 cuentas. `fichas.py` entra una vez y reutiliza los tokens (en `resultados/.fichas.json`, legible solo por tu usuario) mientras les quede vida. Si aun así sale «429», espera 5 minutos. La contraseña sale de `PICASSO_CLAVE_DEMO` (la misma de `picasso/scripts/sembrar.py`) y no se imprime.
- **Token de 15 minutos.** Ningún escenario dura más que el token. Para una `resistencia` de una hora, sube `JFAST_AUTH_ACCESS_LIFETIME_MINUTES=90` en `picasso/.env` del servidor de prueba (`docker compose up -d picasso`), corre `DURACION=60 ./correr.sh resistencia` y regrésalo a 15 al terminar.
- **Lo que no se mide.**
  - La entrada al sistema bajo carga: el límite por IP lo impide desde una sola máquina. Es argon2, unos 100 ms por entrada; un cambio de turno son unas 20.
  - La cola sin señal del celular: k6 no ejecuta el service worker. `pico` simula su efecto, todos enviando a la vez.
  - El navegador: tiempos de pantalla y fotos comprimidas en el teléfono.

## Lo que ya se corrió

### 2026-11-12, copia en Docker (topes de la tabla de arriba)

| Corrida | Usuarios | Peticiones | Errores | p95 consulta | p95 guardar | p95 foto | p95 PDF |
|---|---|---|---|---|---|---|---|
| `humo` | 3 | 37 | 0 | 61 ms | 45 ms | 27 ms | 101 ms |
| `carga` (10 min) | 20 | 2,770 (4.4/s) | 0 | 53 ms | 41 ms | 33 ms | 128 ms |
| `estres`, `ESCALA=0.2` (10 min) | hasta 47 | 17,176 (28/s) | 0 | 27 ms | 26 ms | 25 ms | 225 ms |
| `estres`, `ESCALA=0.5` (10 min) | hasta 118 | 44,216 (73/s; ~160/s en el minuto más alto) | 0 | 52 ms | 47 ms | 60 ms | 291 ms |
| `pico`, `ESCALA=0.25` (3 min) | 40 de golpe | 4,589 (27/s) | 0 | 21 ms | 21 ms | 22 ms | 125 ms |

- `lecturas.sh` (1, 4, 8 y 16 clientes): no se rompió. Llega a unas 400 consultas por segundo con 4 clientes y de ahí ya no sube: es el techo de 2 CPU. Con 16 clientes el p99 fue de 207 ms.
- **CPU de la API por corrida** (de 200 % posibles, muestreado cada 10 s):

  | Corrida | Promedio | Máximo |
  |---|---|---|
  | `lecturas.sh` | 108 % | 206 % (sus 2 CPU llenos) |
  | `carga` | 5 % | 15 % |
  | `estres` al 20 % | 19 % | 48 % |
  | `pico` al 25 % | 18 % | 34 % |
  | `estres` al 50 % (toda la corrida) | 38 % | 134 % |
  | `estres` al 50 % (minuto más alto, 115 usuarios, ~160 pet/s) | 79 % | 134 % |

  (En el estrés al 50 % hubo además un pico suelto de 158 % al arrancar: son los 13 inicios de sesión de `fichas.py`, porque revisar una contraseña cuesta CPU a propósito. No es carga de la prueba.)

  PostgreSQL: 7 % de promedio y 27 % de máximo en el estrés al 20 %; 32 % y 58 % en el minuto más alto del estrés al 50 %. Memoria máxima: API 362 MB de 768, PostgreSQL 174 MB, worker 93 MB, Redis 9 MB, Caddy 45 MB. Lo primero que se acaba es el CPU de la API (solo las consultas lo llenaron), no la base ni la memoria.
- **Capacidad:** medido, el trabajo mezclado (escrituras, fotos y PDF) aguantó **unas 160 peticiones por segundo durante un minuto** sin errores, con p99 de 165 ms y la API a un 40 % de sus 2 CPU. Estimado, no medido: el techo de ese trabajo mezclado andaría entre 300 y 400 por segundo, lo mismo que llenó los 2 CPU con solo consultas. Ese techo no se buscó, por no subir la escala de más.
- **Lo que se encontró:** en el primer `pico` falló 1 de 4,535 peticiones. Era un avance sobre un folio que otro «gerente» virtual de la misma sucursal acababa de cerrar. La API contestó bien («El folio ya no está abierto.»); el guion ahora lo cuenta como choque y no como error. Al repetir el `pico` salió con 0 errores.
- **Cómo leerlo:** con 20 personas a ritmo normal, la API usa una fracción de sus 2 CPU. La carga real esperada es de menos de una petición por segundo, y el estrés al 50 % llegó a unas 160 por segundo con p95 de 0.29 s en los PDF y de 0.06 s en lo demás. Ojo: dentro de Docker no hay red de por medio. Desde un celular hay que sumar la latencia de la red, que en el VPS fue de unos 100 a 200 ms.
- Sin correr: `resistencia` y el estrés al 100 %. Ninguna se ha corrido contra el VPS.
- En el estrés al 50 % hubo 533 choques: dos «personas» virtuales sobre la misma revisión. La API los rechazó como debe, y no cuentan como error.

### 2026-11-12, VPS (solo humo, antes de pasar a Docker)

- `lecturas.sh` con escalones 1 y 4 (5 s): no se rompió. Con 4 clientes el p99 fue de 670 ms.
- `humo` completo: 37 peticiones y 0 errores. p95: consultas 0.20 s, escrituras 0.19 s, fotos 0.71 s, PDF 0.32 s.
