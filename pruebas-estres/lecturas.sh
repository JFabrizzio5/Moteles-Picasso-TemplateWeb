#!/usr/bin/env bash
# Solo lecturas, por escalones de concurrencia, con `jfast bench` (viene con
# JFast). Dice en qué escalón se rompe y qué dependencia cedió (/ready).
# No escribe nada, así que se puede correr sin respaldar la base.
#
#   ./lecturas.sh docker           contra la copia en Docker (local/levantar.sh)
#   ./lecturas.sh vps              contra el VPS de prueba
#   ./lecturas.sh local            contra la API de la Mac (:9800)
#   PASOS=1,8,32,64,128 SEGUNDOS=20 ./lecturas.sh
#
# Además deja el mismo escenario como script de k6 en resultados/.
set -euo pipefail
cd "$(dirname "$0")"

DESTINO=${1:-docker}   # el VPS solo si se pide por nombre
case "$DESTINO" in
  docker) API=${API:-http://127.0.0.1:9850/api} ;;
  vps) API=${API:-https://2.25.196.39:9630/api} ;;
  local) API=${API:-http://127.0.0.1:9800} ;;
  *) API=$DESTINO ;;
esac
PASOS=${PASOS:-1,4,16,64}
SEGUNDOS=${SEGUNDOS:-15}

# El token del propietario (ve las seis sucursales) sale de fichas.py, que
# reutiliza los de la última corrida; va por variable de entorno, no a pantalla.
JFAST_BENCH_TOKEN=$(python3 fichas.py "$API" 10 | python3 -c 'import json,sys; print(json.load(sys.stdin)["tokens"]["propietario@picasso.mx"])')
export JFAST_BENCH_TOKEN

SALIDA="resultados/$(date +%Y-%m-%d_%H%M)-lecturas-$DESTINO"
mkdir -p "$SALIDA"
SEMANA=$(python3 -c 'import datetime as d; print(d.date.today() - d.timedelta(days=7))')

../picasso/.venv/bin/jfast bench "$API" \
  -r "GET /panel" \
  -r "GET /indicadores" \
  -r "GET /tablero?sucursal_id=1" \
  -r "GET /incidencias?estado=abiertas" \
  -r "GET /revisiones?desde=$SEMANA" \
  -r "GET /sucursales" \
  -c "$PASOS" -d "$SEGUNDOS" \
  --max-p99-ms 800 \
  --k6 "$SALIDA/lecturas-k6.js" \
  2>&1 | tee "$SALIDA/salida.txt"
