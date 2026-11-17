"""Dar de alta los cuartos de cada motel con su tipo, leídos de Kairos.

Kairos no enseña un catálogo de cuartos en su vista móvil: el tipo de cada uno
(Suite, Jacuzzi, Jacuzzi y sauna, Pent house) y si es de motel o de hotel salen
de la tarifa con que se rentó. Este script lee las rentas de los últimos días,
pide el detalle de un par por cuarto y deja los cuartos en Picasso:

- alta del cuarto que falta;
- al que ya existe le corrige tipo, sección, jacuzzi y sauna;
- no borra ni da de baja nada (un cuarto sin rentas puede estar en obra): solo
  lo reporta. Alberca, terraza y equipo se quedan como los dejó administración.

En el servidor, con las credenciales de Kairos en el entorno:
    docker compose exec -e PYTHONPATH=/app picasso python scripts/kairos_cuartos.py
    docker compose exec -e PYTHONPATH=/app picasso python scripts/kairos_cuartos.py VAQ --dias 21

Sin credenciales, desde un archivo con las tarifas ya leídas (por ejemplo, desde
la sesión de Kairos de alguien en el navegador):
    ... python scripts/kairos_cuartos.py --archivo cuartos.json
    # cuartos.json = {"VAQ": {"101": ["MOTEL JACUZZI SAUNA", ...], "102": [...]}}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from jfastframework.plugins.builtin.database import DatabaseSettings

from modules.finanzas.services import tipo_mayoritario
from modules.finanzas.tasks import importar_cuartos, sincronizar_cuartos


async def desde_archivo(session: AsyncSession, datos: dict[str, dict[str, list[str]]]) -> None:
    for clave, cuartos in datos.items():
        tipos = {n: t for n, lista in cuartos.items() if (t := tipo_mayoritario(lista))}
        r = await sincronizar_cuartos(session, clave, tipos)  # type: ignore[arg-type]
        if r is None:
            print(f"{clave}: no hay esa sucursal en Picasso")
            continue
        print(
            f"{clave}: {len(r.nuevos)} nuevos, {len(r.actualizados)} corregidos, "
            f"{r.sin_cambio} igual"
            + (
                f"; solo en Picasso (no se tocaron): {', '.join(r.solo_en_picasso)}"
                if r.solo_en_picasso
                else ""
            )
        )


async def main(claves: list[str], dias: int, archivo: Path | None) -> None:
    engine = create_async_engine(DatabaseSettings().dsn.get_secret_value())
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            if archivo:
                await desde_archivo(session, json.loads(archivo.read_text()))  # noqa: ASYNC240
            else:
                await importar_cuartos({"claves": claves, "dias": dias}, session)  # type: ignore[arg-type]
            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("claves", nargs="*", help="VAQ, TOL… (sin nada: todos los moteles)")
    parser.add_argument("--dias", type=int, default=14)
    parser.add_argument("--archivo", type=Path)
    a = parser.parse_args()
    asyncio.run(main(a.claves, a.dias, a.archivo))
