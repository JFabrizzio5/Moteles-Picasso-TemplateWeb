#!/usr/bin/env bash
# En el SERVIDOR de prueba, después de una corrida de estrés: regresa la base
# al respaldo de foto-base.sh y borra las fotos que subió la prueba.
#
#   ssh <usuario>@<servidor> <ruta-en-el-servidor>/Picasso/pruebas-estres/servidor/restaurar-base.sh
#   ... restaurar-base.sh respaldos-estres/base-20261112-140000.dump   (uno en particular)
#
# La API se detiene unos segundos. Lo que esté en la caché de Redis (panel,
# indicadores) se renueva solo en 5 minutos.
set -euo pipefail
cd "$(dirname "$0")/../.."

ARCHIVO=${1:-$(ls -t respaldos-estres/base-*.dump 2>/dev/null | head -1)}
[ -n "$ARCHIVO" ] && [ -f "$ARCHIVO" ] || { echo "No hay respaldo: corre foto-base.sh antes de la prueba."; exit 1; }
echo "Restaurando $ARCHIVO"

docker compose stop picasso-worker picasso
docker compose exec -T picasso-database dropdb -U app --if-exists app
docker compose exec -T picasso-database createdb -U app app
docker compose exec -T picasso-database pg_restore -U app -d app --no-owner < "$ARCHIVO"
docker compose start picasso

# Las fotos de la prueba: todo lo que llegó al disco después de la marca.
docker compose exec -T picasso sh -c \
  'test -f /app/storage/.antes-de-estres && find /app/storage -type f -newer /app/storage/.antes-de-estres ! -name .antes-de-estres -print -delete | wc -l' \
  | xargs -I{} echo "Fotos de la prueba borradas: {}"
docker compose start picasso-worker

docker compose exec -T picasso-database psql -U app -d app -Atc \
  "select 'revisiones: ' || count(*) from revisiones union all select 'folios: ' || count(*) from incidencias"
