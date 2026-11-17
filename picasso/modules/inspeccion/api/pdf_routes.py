"""Descargas PDF: los cuatro reportes de la sección 07 del documento.

Mismo token y mismos permisos que las rutas JSON: el PDF es otra forma de ver
lo que la pantalla ya enseña a quien lo pide.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from jfastframework.plugins.builtin.auth import require_auth
from jfastframework.plugins.builtin.database import DbSession

from ..models import Actor
from ..repositories import InspeccionRepository
from ..services import Pdf, PdfService, periodo
from .routes import _archivos, get_actor

router = APIRouter(prefix="/reportes", tags=["reportes"], dependencies=[Depends(require_auth)])

PDF: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/pdf": {}}, "description": "El reporte en PDF."}
}


async def pdfs(request: Request, session: DbSession) -> PdfService:
    return PdfService(InspeccionRepository(session), _archivos(request))


def _descarga(pdf: Pdf) -> Response:
    # RFC 5987: `filename` en ASCII para clientes viejos, `filename*` con acentos.
    disposicion = (
        f"attachment; filename=\"{pdf.nombre_ascii}\"; filename*=UTF-8''{quote(pdf.nombre)}"
    )
    return Response(
        content=pdf.datos,
        media_type="application/pdf",
        headers={"Content-Disposition": disposicion, "Cache-Control": "no-store"},
    )


@router.get("/revision/{revision_id}.pdf", responses=PDF, summary="Reporte por inspección")
async def pdf_revision(
    revision_id: int,
    actor: Actor = Depends(get_actor),
    service: PdfService = Depends(pdfs),
) -> Response:
    return _descarga(await service.revision(actor, revision_id))


@router.get("/incidencia/{incidencia_id}.pdf", responses=PDF, summary="Reporte por incidencia")
async def pdf_incidencia(
    incidencia_id: int,
    actor: Actor = Depends(get_actor),
    service: PdfService = Depends(pdfs),
) -> Response:
    return _descarga(await service.incidencia(actor, incidencia_id))


@router.get("/habitacion/{habitacion_id}.pdf", responses=PDF, summary="Reporte por habitación")
async def pdf_habitacion(
    habitacion_id: int,
    actor: Actor = Depends(get_actor),
    service: PdfService = Depends(pdfs),
) -> Response:
    return _descarga(await service.habitacion(actor, habitacion_id))


@router.get("/grupo.pdf", responses=PDF, summary="Reporte por sucursal y grupo")
async def pdf_grupo(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: PdfService = Depends(pdfs),
) -> Response:
    return _descarga(await service.grupo(actor, periodo(desde, hasta)))
