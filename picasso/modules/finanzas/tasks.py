"""Trabajo de fondo de finanzas: leer Kairos cada noche.

- `finanzas.importar_noche` (cron, 04:30 de CDMX): vuelve a leer los últimos
  días de cada motel (por si recepción corrigió algo) y avanza el rellenado del
  historial un tramo por noche.
- `finanzas.importar`: lo encola la pantalla de administración para volver a
  leer un rango a mano.
- `finanzas.importar_cuartos`: da de alta los cuartos de cada motel con su tipo
  (Suite, Jacuzzi, Jacuzzi y sauna…), sacado de las tarifas con que se rentaron.

Lo corre `jfast worker` (scheduler = true en jfast.toml). Un Kairos que no
responde no detiene a los demás: queda anotado en su fuente y se reintenta la
noche siguiente.
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any

from jfastframework.tasks import TaskSession, task

from modules.sucursal import public as sucursal_publica

from .models import FuenteKairos
from .repositories import FinanzasRepository
from .services import (
    ClienteKairos,
    ImportadorKairos,
    KairosError,
    Sucursal,
    TipoCuarto,
    ahora,
    credenciales,
    dias_entre,
    hoy,
)

log = logging.getLogger("picasso.finanzas")

#: Días hacia atrás que se vuelven a leer cada noche.
DIAS_A_RELEER = 3
#: Días del historial que se traen por noche y por motel.
HISTORIAL_POR_NOCHE = int(os.environ.get("PICASSO_KAIROS_HISTORIAL_POR_NOCHE", "150"))
#: Desde cuándo el historial trae tarifas y cada renta; antes, solo el resumen del día.
DETALLE_DESDE = date.fromisoformat(os.environ.get("PICASSO_KAIROS_DETALLE_DESDE", "2025-01-01"))


async def _importador(session: TaskSession) -> tuple[FinanzasRepository, ImportadorKairos] | None:
    repo = FinanzasRepository(session)
    try:
        usuario, clave = credenciales()
    except KairosError as e:
        # Sin credenciales no hay nada que reintentar: se anota y se sale sin error,
        # para que la cola no lo mande tres veces a los trabajos muertos.
        log.warning("%s", e)
        for fuente in await repo.fuentes(solo_activas=True):
            fuente.ultima_corrida = ahora()
            fuente.ultimo_error = str(e)[:300]
        return None
    sucursales = {
        s.clave: Sucursal(s.id, s.clave, s.nombre)
        for s in await sucursal_publica.sucursales(session, tenant_id=None)
    }

    def fabrica(fuente: FuenteKairos) -> ClienteKairos:
        return ClienteKairos(fuente.url_base, usuario=usuario, clave=clave)

    return repo, ImportadorKairos(repo, sucursales, fabrica, al_terminar_dia=session.commit)


@task("finanzas.importar_noche", cron="30 4 * * *", timezone="America/Mexico_City")
async def importar_noche(payload: dict[str, Any], session: TaskSession) -> None:
    listo = await _importador(session)
    if listo is None:
        return
    repo, importador = listo
    ayer = hoy() - timedelta(days=1)
    dias = dias_entre(ayer - timedelta(days=DIAS_A_RELEER - 1), ayer)
    for fuente in await repo.fuentes(solo_activas=True):
        r = await importador.importar(fuente, dias)
        await session.commit()
        h = await importador.rellenar_historial(
            fuente, max_dias=HISTORIAL_POR_NOCHE, detalle_desde=DETALLE_DESDE
        )
        await session.commit()
        log.info(
            "Kairos %s: %s días leídos, %s del historial%s",
            fuente.sucursal_clave,
            r.dias,
            h.dias,
            f" — {'; '.join(r.errores + h.errores)}" if r.errores or h.errores else "",
        )


@task("finanzas.importar")
async def importar(payload: dict[str, Any], session: TaskSession) -> None:
    listo = await _importador(session)
    if listo is None:
        return
    repo, importador = listo
    desde = date.fromisoformat(payload["desde"])
    hasta = date.fromisoformat(payload["hasta"])
    clave = payload.get("sucursal_clave")
    detalle = bool(payload.get("detalle", True))
    for fuente in await repo.fuentes(solo_activas=True):
        if clave and fuente.sucursal_clave != clave:
            continue
        r = await importador.importar(fuente, dias_entre(desde, hasta), detalle=detalle)
        await session.commit()
        log.info(
            "Kairos %s (a mano): %s días%s",
            fuente.sucursal_clave,
            r.dias,
            f" — {r.errores}" if r.errores else "",
        )


async def sincronizar_cuartos(
    session: TaskSession, clave: str, tipos: dict[str, TipoCuarto]
) -> sucursal_publica.SincronizacionDTO | None:
    """Pasa a Picasso los cuartos leídos de Kairos (alta y corrección, nunca baja)."""
    sucursal = next(
        (s for s in await sucursal_publica.sucursales(session, tenant_id=None) if s.clave == clave),
        None,
    )
    if sucursal is None:
        return None
    return await sucursal_publica.sincronizar_habitaciones(
        session,
        tenant_id=None,
        sucursal_id=sucursal.id,
        cuartos=[
            sucursal_publica.CuartoKairosDTO(
                numero=numero,
                tipo=t.tipo,
                seccion=t.seccion,
                tiene_jacuzzi=t.tiene_jacuzzi,
                tiene_sauna=t.tiene_sauna,
                tiene_alberca=t.tiene_alberca,
                tiene_terraza=t.tiene_terraza,
            )
            for numero, t in tipos.items()
        ],
    )


@task("finanzas.importar_cuartos")
async def importar_cuartos(payload: dict[str, Any], session: TaskSession) -> None:
    listo = await _importador(session)
    if listo is None:
        return
    repo, importador = listo
    claves = set(payload.get("claves") or [])
    for fuente in await repo.fuentes(solo_activas=True):
        if claves and fuente.sucursal_clave not in claves:
            continue
        try:
            tipos = await importador.tipos_de_cuarto(
                fuente, dias=int(payload.get("dias", 14)), muestras=int(payload.get("muestras", 2))
            )
        except KairosError as e:
            log.warning("Kairos %s (cuartos): %s", fuente.sucursal_clave, e)
            continue
        r = await sincronizar_cuartos(session, fuente.sucursal_clave, tipos)
        await session.commit()
        if r is not None:
            log.info(
                "Kairos %s: %s cuartos nuevos, %s corregidos, %s igual; solo en Picasso: %s",
                fuente.sucursal_clave,
                len(r.nuevos),
                len(r.actualizados),
                r.sin_cambio,
                ", ".join(r.solo_en_picasso) or "ninguno",
            )
