#!/usr/bin/env bash
# En el SERVIDOR de prueba, antes de una corrida de estrés: guarda la base y
# marca la hora para saber qué fotos llegaron después.
#
#   ssh <usuario>@<servidor> <ruta-en-el-servidor>/Picasso/pruebas-estres/servidor/foto-base.sh
#
# Después: restaurar-base.sh deja la base y las fotos como estaban.
set -euo pipefail
cd "$(dirname "$0")/../.."   # la carpeta del proyecto (donde está el .env)

mkdir -p respaldos-estres
chmod 700 respaldos-estres
ARCHIVO="respaldos-estres/base-$(date +%Y%m%d-%H%M%S).dump"

docker compose exec -T picasso-database pg_dump -U app -Fc app > "$ARCHIVO"
docker compose exec -T picasso touch /app/storage/.antes-de-estres

echo "Base guardada en $ARCHIVO ($(du -h "$ARCHIVO" | cut -f1))."
docker compose exec -T picasso-database psql -U app -d app -Atc \
  "select 'revisiones: ' || count(*) from revisiones union all select 'folios: ' || count(*) from incidencias"
