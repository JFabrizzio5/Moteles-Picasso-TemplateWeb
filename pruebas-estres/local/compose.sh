#!/usr/bin/env bash
# `docker compose` del entorno de estrés en la Mac (proyecto picasso-estres).
#   ./compose.sh ps
#   ./compose.sh logs picasso --tail 50
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../.." && pwd)"
cd "$RAIZ"
exec docker compose -p picasso-estres --env-file "$AQUI/.env" \
  -f docker-compose.yml -f docker-compose.prod.yml -f "$AQUI/docker-compose.estres.yml" "$@"
