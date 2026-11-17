#!/usr/bin/env bash
# Corre un escenario de k6 contra Picasso. k6 va en Docker: no se instala nada.
#
#   ./correr.sh humo docker           contra la copia en Docker (local/levantar.sh)
#   ./correr.sh humo vps              contra el VPS de prueba (2.25.196.39:9630)
#   ./correr.sh carga local           contra la API de desarrollo de la Mac (:9800)
#   CONFIRMO=si ./correr.sh estres https://otro-servidor
#
# Escenarios: humo, carga, estres, pico, resistencia (ver README.md).
# Variables opcionales: PAUSA (ritmo), DURACION (minutos de resistencia) y
# ESCALA (multiplica cuántos usuarios: 0.2 = la quinta parte).
# El resultado queda en resultados/<fecha>-<escenario>-<destino>/.
set -euo pipefail
cd "$(dirname "$0")"

K6_IMAGEN=grafana/k6:2.3.0
ESCENARIO=${1:-humo}
DESTINO=${2:-docker}   # el VPS solo si se pide por nombre

case "$ESCENARIO" in
  humo|carga|estres|pico|resistencia) ;;
  *) echo "Escenario desconocido: $ESCENARIO (humo, carga, estres, pico, resistencia)"; exit 2 ;;
esac

RED=""
case "$DESTINO" in
  docker)
    # La copia de local/levantar.sh: k6 entra por la red de compose y
    # fichas.py, desde la Mac, por el puerto 9850.
    URL=http://caddy
    API=$URL/api
    API_MAC=http://127.0.0.1:9850/api
    RED=picasso-estres_default
    docker network inspect "$RED" >/dev/null 2>&1 || { echo "No está levantada: corre local/levantar.sh"; exit 2; }
    ;;
  vps)
    URL=${URL:-https://2.25.196.39:9630}
    API=${API:-$URL/api}
    ;;
  local)
    # La API de desarrollo, sin Caddy: /storage y la API en el mismo origen.
    URL=${URL:-http://host.docker.internal:9800}
    API=${API:-$URL}
    ;;
  *)
    URL=$DESTINO
    API=${API:-$URL/api}
    if [ "${CONFIRMO:-}" != si ]; then
      echo "Esto escribe revisiones, fotos y folios en $URL."
      echo "Si es un servidor de prueba: CONFIRMO=si $0 $ESCENARIO $DESTINO"
      exit 2
    fi
    DESTINO=otro
    ;;
esac

# Los tokens de las 13 cuentas los da fichas.py (reutiliza los de la corrida
# anterior mientras sirvan) y van a k6 por variable de entorno: no se imprimen.
# La API de la Mac se ve como host.docker.internal desde k6 y como 127.0.0.1
# desde aquí.
case "$ESCENARIO" in   # minutos que dura cada uno (lo mismo que MINUTOS en k6)
  humo) MINUTOS=5 ;; carga|estres) MINUTOS=10 ;; pico) MINUTOS=3 ;; resistencia) MINUTOS=${DURACION:-12} ;;
esac
API_MAC=${API_MAC:-${API/host.docker.internal/127.0.0.1}}
FICHAS=$(python3 fichas.py "$API_MAC" "$MINUTOS")
export FICHAS URL API ESCENARIO
export PAUSA=${PAUSA:-} DURACION=${DURACION:-} ESCALA=${ESCALA:-}

SALIDA="resultados/$(date +%Y-%m-%d_%H%M)-$ESCENARIO-$DESTINO"
mkdir -p "$SALIDA"
echo "Escenario $ESCENARIO contra $URL → $SALIDA"

# k6 también con tope, para que el generador no se coma la máquina.
docker run --rm -i \
  --cpus 1 --memory 384m \
  ${RED:+--network "$RED"} \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/k6:/scripts:ro" \
  -v "$PWD/$SALIDA:/resultados" \
  -e URL -e API -e ESCENARIO -e FICHAS -e PAUSA -e DURACION -e ESCALA \
  -e K6_WEB_DASHBOARD=true \
  -e K6_WEB_DASHBOARD_EXPORT=/resultados/reporte.html \
  "$K6_IMAGEN" run --summary-export=/resultados/resumen.json /scripts/picasso.js \
  2>&1 | tee "$SALIDA/salida.txt"
