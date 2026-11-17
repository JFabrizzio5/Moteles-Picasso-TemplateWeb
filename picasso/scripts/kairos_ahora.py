"""Correr ya la lectura nocturna de Kairos, sin esperar a las 04:30.

Hace exactamente lo que la tarea `finanzas.importar_noche`: relee los últimos
días de cada motel y avanza el historial un tramo. Útil la primera vez o tras
cambiar la IP de un motel. Las credenciales salen del entorno
(PICASSO_KAIROS_USUARIO / PICASSO_KAIROS_CLAVE), como en el worker.

En el servidor:
    docker compose exec -e PYTHONPATH=/app picasso python scripts/kairos_ahora.py
    docker compose exec -e PYTHONPATH=/app picasso python scripts/kairos_ahora.py --vueltas 10

`--vueltas N` repite el tramo del historial N veces (cada vuelta, hasta
PICASSO_KAIROS_HISTORIAL_POR_NOCHE días por motel).
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from jfastframework.plugins.builtin.database import DatabaseSettings

from modules.finanzas.repositories import FinanzasRepository
from modules.finanzas.tasks import importar_noche


async def main(vueltas: int) -> None:
    engine = create_async_engine(DatabaseSettings().dsn.get_secret_value())
    try:
        for vuelta in range(1, vueltas + 1):
            async with AsyncSession(engine, expire_on_commit=False) as session:
                await importar_noche({}, session)
                await session.commit()
                for f in await FinanzasRepository(session).fuentes():
                    print(
                        f"[{vuelta}] {f.sucursal_clave} ({f.nombre_kairos}): "
                        f"primer día {f.primer_dia or '¿?'}, "
                        f"historial desde {f.historial_desde or '—'}"
                        + (f" — {f.ultimo_error}" if f.ultimo_error else " — ok")
                    )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vueltas", type=int, default=1)
    asyncio.run(main(parser.parse_args().vueltas))
