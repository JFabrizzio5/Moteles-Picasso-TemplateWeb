"""Trabajo de fondo de finanzas: leer Kairos cada noche.

- `finanzas.importar_noche` (cron, 04:30 de CDMX): vuelve a leer los últimos
  días de cada motel (por si recepción corrigió algo) y avanza el rellenado del
  historial un tramo por noche.
- `finanzas.importar`: lo encola la pantalla de administración para volver a
  leer un rango a mano.

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
