"""Gastos de ejemplo para la demo: desglosados, de cada gerente y algunos en folios.

Sirven para enseñar Finanzas y la auditoría (quién gasta más, en qué, y el
mismo artículo a precios distintos). Se reconocen por la nota «Dato de
ejemplo»: al correrlo otra vez se borran y se crean de nuevo.

    docker compose exec -e PYTHONPATH=/app picasso python scripts/gastos_demo.py
"""

from __future__ import annotations

import asyncio
import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from jfastframework.plugins.builtin.database import DatabaseSettings

from modules.finanzas.enums import CategoriaGasto, FormaPago
from modules.finanzas.models import Actor, GastoCrear, PartidaCrear
from modules.finanzas.repositories import FinanzasRepository
from modules.finanzas.services import FolioLigado, GastosService, Sucursal, hoy
from modules.inspeccion import public as inspeccion_publica
from modules.sucursal import public as sucursal_publica
from shared.enums import Rol

NOTA = "Dato de ejemplo"

# (concepto, categoría, proveedor, forma de pago, [(artículo, unidad, precio base)], ¿a folio?)
COMPRAS: list[tuple[str, CategoriaGasto, str, FormaPago, list[tuple[str, str, float]], bool]] = [
    (
        "Fruta y verdura para room service",
        CategoriaGasto.FRUTAS_VERDURAS,
        "Mercado de abastos",
        FormaPago.EFECTIVO,
        [
            ("Lechuga orejona", "pza", 15),
            ("Jitomate saladet", "kg", 28),
            ("Limón", "kg", 32),
            ("Plátano", "kg", 22),
            ("Fresa", "kg", 60),
        ],
        False,
    ),
    (
        "Agua y refrescos para cuartos",
        CategoriaGasto.BEBIDAS,
        "Abarrotes Don Pepe",
        FormaPago.EFECTIVO,
        [("Agua natural 600 ml", "pza", 3.5), ("Refresco de cola 355 ml", "pza", 11)],
        False,
    ),
    (
        "Material de limpieza de la semana",
        CategoriaGasto.LIMPIEZA,
        "Distribuidora La Esponja",
        FormaPago.TRANSFERENCIA,
        [
            ("Cloro 1 L", "pza", 19),
            ("Jabón líquido para manos", "lt", 38),
            ("Bolsa para basura grande", "paquete", 45),
        ],
        False,
    ),
    (
        "Amenidades de cuarto",
        CategoriaGasto.AMENIDADES,
        "Hotelera del Centro",
        FormaPago.TRANSFERENCIA,
        [("Shampoo en sobre", "pza", 2.2), ("Jabón de tocador", "pza", 1.9)],
        False,
    ),
    (
        "Refacciones para reparar el cuarto",
        CategoriaGasto.MANTENIMIENTO,
        "Ferretería La Tuerca",
        FormaPago.EFECTIVO,
        [
            ("Silicón transparente", "pza", 85),
            ("Foco LED 9 W", "pza", 42),
            ("Broca para concreto 1/4", "pza", 30),
            ("Taquete de plástico", "pza", 2.5),
        ],
        True,
    ),
    (
        "Cambio de regadera",
        CategoriaGasto.MANTENIMIENTO,
        "Plomería Rápida",
        FormaPago.EFECTIVO,
        [
            ("Regadera cromada", "pza", 340),
            ("Cinta teflón", "pza", 12),
            ("Mano de obra del plomero", "servicio", 450),
        ],
        True,
    ),
]


async def main() -> None:
    random.seed(17)
    engine = create_async_engine(DatabaseSettings().dsn.get_secret_value())
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await session.execute(text("DELETE FROM gastos WHERE nota = :n"), {"n": NOTA})
        sucursales = await sucursal_publica.sucursales(session, tenant_id=None)
        gerentes = {
            sid: (uid, nombre)
            for uid, nombre, sid in (
                await session.execute(
                    text("SELECT user_id, nombre, sucursal_id FROM personal WHERE rol = 'gerente'")
                )
            ).all()
        }

        async def buscar_folio(incidencia_id: int) -> FolioLigado | None:
            f = await inspeccion_publica.incidencia(session, incidencia_id)
            if f is None:
                return None
            return FolioLigado(f.id, f.folio, f.titulo, f.sucursal_id, f.habitacion_numero)

        class SinArchivos:
            async def liga(self, llave: str) -> str:
                return ""

        service = GastosService(
            FinanzasRepository(session),
            [Sucursal(s.id, s.clave, s.nombre) for s in sucursales],
            SinArchivos(),  # type: ignore[arg-type]
            buscar_folio,
        )
        creados = 0
        for s in sucursales:
            uid, nombre = gerentes.get(s.id, (f"demo-{s.clave}", f"Gerente {s.nombre}"))
            actor = Actor(uid, nombre, Rol.GERENTE, s.id)
            abiertos = [
                i
                for (i,) in (
                    await session.execute(
                        text(
                            "SELECT id FROM incidencias WHERE sucursal_id = :s "
                            "AND estado IN ('reportada','en_atencion') ORDER BY id"
                        ),
                        {"s": s.id},
                    )
                ).all()
            ]
            # Cada casa compra un poco más caro o más barato: eso es lo que ve la contadora.
            factor = random.choice([0.9, 1.0, 1.0, 1.15, 1.35])
            for semana in range(3):
                for concepto, cat, proveedor, forma, articulos, a_folio in COMPRAS:
                    if random.random() < 0.25:
                        continue
                    partidas = [
                        PartidaCrear(
                            descripcion=nombre_art,
                            cantidad=Decimal(
                                random.choice(
                                    [1, 2, 3, 5, 10, 12, 24] if unidad != "servicio" else [1]
                                )
                            ),
                            unidad=unidad,
                            precio_unitario=Decimal(
                                str(round(base * factor * random.uniform(0.95, 1.08), 2))
                            ),
                        )
                        for nombre_art, unidad, base in articulos
                        if unidad == "servicio" or random.random() < 0.85
                    ] or [
                        PartidaCrear(
                            descripcion=articulos[0][0],
                            cantidad=Decimal(1),
                            unidad=articulos[0][1],
                            precio_unitario=Decimal(str(articulos[0][2])),
                        )
                    ]
                    folios = (
                        random.sample(abiertos, k=min(len(abiertos), random.choice([1, 1, 2])))
                        if a_folio and abiertos
                        else []
                    )
                    await service.crear(
                        actor,
                        GastoCrear(
                            fecha=hoy() - timedelta(days=semana * 7 + random.randint(0, 5)),
                            categoria=cat,
                            concepto=concepto,
                            proveedor=proveedor,
                            forma_pago=forma,
                            partidas=partidas,
                            nota=NOTA,
                            incidencia_ids=folios,
                        ),
                    )
                    creados += 1
        await session.commit()
        print(f"{creados} gastos de ejemplo en {len(sucursales)} sucursales.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
