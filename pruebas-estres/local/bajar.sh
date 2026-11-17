#!/usr/bin/env bash
# Borra la copia de estrés: contenedores, base, fotos y Redis del proyecto
# picasso-estres. No toca el Picasso de desarrollo (:9800) ni el VPS.
# Para empezar de cero entre corridas: ./bajar.sh && ./levantar.sh
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
"$AQUI/compose.sh" down -v --remove-orphans
