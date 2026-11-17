#!/usr/bin/env bash
# Levanta la copia de Picasso para pruebas de estrés en Docker (la Mac) y le
# pone los datos de ejemplo de scripts/sembrar.py si está vacía.
#
#   ./levantar.sh                 → http://127.0.0.1:9850
#   ../correr.sh humo docker      → la prueba
#   ./bajar.sh                    → la borra (base, fotos y Redis de la copia)
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"

# Contraseñas propias de esta copia, generadas una vez y fuera de git.
if [ ! -f "$AQUI/.env" ]; then
  umask 077
  cat > "$AQUI/.env" <<EOF
# Copia de estrés en la Mac (generado por levantar.sh).
PICASSO_DOMINIO=:80
PICASSO_DATABASE_PASSWORD=$(openssl rand -hex 32)
PICASSO_REDIS_PASSWORD=$(openssl rand -hex 32)
EOF
fi

"$AQUI/compose.sh" up -d --build

printf "Esperando a la API"
for _ in $(seq 1 60); do
  estado=$(docker inspect -f '{{.State.Health.Status}}' picasso-estres-picasso-1 2>/dev/null || echo nada)
  [ "$estado" = healthy ] && break
  printf "."
  sleep 3
done
echo " $estado"
[ "$estado" = healthy ] || { "$AQUI/compose.sh" logs picasso --tail 30; exit 1; }

hay=$("$AQUI/compose.sh" exec -T picasso-database psql -U app -d app -Atc "select count(*) from sucursales")
if [ "$hay" = 0 ]; then
  echo "Sembrando los datos de ejemplo (un minuto)..."
  "$AQUI/compose.sh" exec -T -e PYTHONPATH=/app picasso python scripts/sembrar.py
fi
echo "Listo: http://127.0.0.1:9850 · prueba con: ../correr.sh humo docker"
