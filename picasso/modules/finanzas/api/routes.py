"""HTTP del módulo finanzas: ingresos de Kairos y gastos de Picasso."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status

from jfastframework.auth import Principal
from jfastframework.errors import ForbiddenError, ValidationError
from jfastframework.plugins.builtin.auth import require_auth
from jfastframework.plugins.builtin.database import DbSession
from jfastframework.queues import Job

from modules.inspeccion import public as inspeccion_publica
from modules.sucursal import public as sucursal_publica

from ..models import (
    Actor,
    AnalisisGastos,
    ExportarEcont,
    FuenteActualizar,
    FuenteRead,
    GastoActualizar,
    GastoCrear,
    GastoRead,
    ImportarIngresos,
    IngresoDiaRead,
    ResumenFinanzas,
    TarifaRead,
)
from ..repositories import FinanzasRepository
from ..services import Comprobantes, FolioLigado, GastosService, IngresosService, Sucursal, hoy
from ..validations import exigir_finanzas, exigir_quien_ve_todas, rango

router = APIRouter(tags=["finanzas"], dependencies=[Depends(require_auth)])


async def get_actor(session: DbSession, caller: Principal = Depends(require_auth)) -> Actor:
    perfil = await sucursal_publica.perfil_de(
        session, tenant_id=None, user_id=caller.subject, roles=caller.roles
    )
    if perfil is None:
        raise ForbiddenError("Esta cuenta no tiene un puesto asignado.")
    actor = Actor(
        user_id=perfil.user_id, nombre=perfil.nombre, rol=perfil.rol, sucursal_id=perfil.sucursal_id
    )
    exigir_finanzas(actor)
    return actor


async def _sucursales(session: DbSession) -> list[Sucursal]:
    return [
        Sucursal(s.id, s.clave, s.nombre)
        for s in await sucursal_publica.sucursales(session, tenant_id=None)
    ]


async def ingresos(session: DbSession) -> IngresosService:
    return IngresosService(FinanzasRepository(session), await _sucursales(session))


async def gastos(request: Request, session: DbSession) -> GastosService:
    storage = request.app.state.jfast.require("storage")

    async def buscar_folio(incidencia_id: int) -> FolioLigado | None:
        f = await inspeccion_publica.incidencia(session, incidencia_id)
        return None if f is None else FolioLigado(f.id, f.folio, f.titulo, f.sucursal_id)

    return GastosService(
        FinanzasRepository(session),
        await _sucursales(session),
        Comprobantes(storage.disk("private")),
        buscar_folio,
    )


def _periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    fin = hasta or hoy() - timedelta(days=1)
    inicio = desde or fin.replace(day=1)
    rango(inicio, fin)
    return inicio, fin


# -- ingresos -------------------------------------------------------------------


@router.get("/finanzas/resumen", response_model=ResumenFinanzas, summary="Ingresos contra gastos")
async def resumen(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    sucursal_id: int | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: IngresosService = Depends(ingresos),
) -> ResumenFinanzas:
    inicio, fin = _periodo(desde, hasta)
    return await service.resumen(actor, desde=inicio, hasta=fin, sucursal_id=sucursal_id)


@router.get("/finanzas/ingresos", response_model=list[IngresoDiaRead], summary="Ingresos por día")
async def ingresos_por_dia(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    sucursal_id: int | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: IngresosService = Depends(ingresos),
) -> list[IngresoDiaRead]:
    inicio, fin = _periodo(desde, hasta)
    filas = await service.dias(actor, desde=inicio, hasta=fin, sucursal_id=sucursal_id)
    return [IngresoDiaRead.model_validate(f, from_attributes=True) for f in filas]


@router.get("/finanzas/tarifas", response_model=list[TarifaRead], summary="Rentas por tarifa")
async def tarifas(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    sucursal_id: int | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: IngresosService = Depends(ingresos),
) -> list[TarifaRead]:
    inicio, fin = _periodo(desde, hasta)
    return await service.tarifas(actor, desde=inicio, hasta=fin, sucursal_id=sucursal_id)


@router.get("/finanzas/fuentes", response_model=list[FuenteRead], summary="Kairos de cada motel")
async def fuentes(session: DbSession, actor: Actor = Depends(get_actor)) -> list[FuenteRead]:
    exigir_quien_ve_todas(actor)
    filas = await FinanzasRepository(session).fuentes()
    return [FuenteRead.model_validate(f, from_attributes=True) for f in filas]


@router.patch(
    "/finanzas/fuentes/{fuente_id}", response_model=FuenteRead, summary="Cambiar un Kairos"
)
async def actualizar_fuente(
    fuente_id: int,
    payload: FuenteActualizar,
    session: DbSession,
    actor: Actor = Depends(get_actor),
) -> FuenteRead:
    exigir_quien_ve_todas(actor)
    fila = await FinanzasRepository(session).fuente(fuente_id)
    if payload.url_base is not None:
        fila.url_base = payload.url_base.rstrip("/")
    if payload.activo is not None:
        fila.activo = payload.activo
    await session.flush()
    return FuenteRead.model_validate(fila, from_attributes=True)


@router.post(
    "/finanzas/importar",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Volver a leer Kairos en un rango",
)
async def importar(
    payload: ImportarIngresos, request: Request, actor: Actor = Depends(get_actor)
) -> dict[str, str]:
    exigir_quien_ve_todas(actor)
    rango(payload.desde, payload.hasta, max_dias=120)
    if payload.hasta >= hoy() + timedelta(days=1):
        raise ValidationError("Solo se leen días que ya pasaron o el de hoy.")
    queue = request.app.state.jfast.require("queue")
    job_id = await queue.enqueue(
        Job(
            task="finanzas.importar",
            payload={
                "desde": payload.desde.isoformat(),
                "hasta": payload.hasta.isoformat(),
                "sucursal_clave": payload.sucursal_clave,
                "detalle": payload.detalle,
            },
        )
    )
    return {"trabajo": job_id}


# -- gastos -----------------------------------------------------------------------


@router.get("/gastos", response_model=list[GastoRead], summary="Gastos")
async def listar_gastos(
    sucursal_id: int | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    incidencia_id: int | None = Query(None),
    sin_incidencia: bool = Query(False),
    categoria: str | None = Query(None, max_length=20),
    buscar: str | None = Query(None, max_length=60),
    incluir_anulados: bool = Query(False),
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> list[GastoRead]:
    return await service.listar(
        actor,
        sucursal_id=sucursal_id,
        desde=desde,
        hasta=hasta,
        incidencia_id=incidencia_id,
        sin_incidencia=sin_incidencia,
        categoria=categoria,
        buscar=buscar,
        incluir_anulados=incluir_anulados,
    )


@router.post(
    "/gastos",
    response_model=GastoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar gasto",
)
async def crear_gasto(
    payload: GastoCrear,
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> GastoRead:
    return await service.crear(actor, payload)


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/gastos/analisis", response_model=AnalisisGastos, summary="Auditar gastos")
async def analisis_gastos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    sucursal_id: int | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> AnalisisGastos:
    inicio, fin = _periodo(desde, hasta)
    return await service.analisis(actor, desde=inicio, hasta=fin, sucursal_id=sucursal_id)


# Antes de /gastos/{gasto_id}: si no, «econt» se tomaría por un id.
@router.post("/gastos/econt", summary="Excel de movimientos para E-Cont")
async def exportar_econt(
    pedido: ExportarEcont,
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> Response:
    contenido, n = await service.exportar_excel(actor, pedido)
    nombre = f"Gastos-Picasso-E-Cont-{hoy().isoformat()}.xlsx"
    return Response(
        contenido,
        media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"', "X-Gastos": str(n)},
    )


@router.post("/gastos/econt-xml", summary="XML de las facturas para E-Cont")
async def exportar_econt_xml(
    pedido: ExportarEcont,
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> Response:
    contenido, n = await service.exportar_xml(actor, pedido)
    nombre = f"Facturas-Picasso-{hoy().isoformat()}.zip"
    return Response(
        contenido,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"', "X-Xml": str(n)},
    )


@router.get("/gastos/{gasto_id}", response_model=GastoRead, summary="Un gasto")
async def detalle_gasto(
    gasto_id: int,
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> GastoRead:
    return await service.detalle(actor, gasto_id)


@router.patch("/gastos/{gasto_id}", response_model=GastoRead, summary="Corregir o ligar un gasto")
async def actualizar_gasto(
    gasto_id: int,
    payload: GastoActualizar,
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> GastoRead:
    return await service.actualizar(actor, gasto_id, payload)


@router.post("/gastos/{gasto_id}/anular", response_model=GastoRead, summary="Anular un gasto")
async def anular_gasto(
    gasto_id: int,
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> GastoRead:
    return await service.anular(actor, gasto_id)


@router.post("/gastos/{gasto_id}/archivos", response_model=GastoRead, summary="Subir comprobante")
async def subir_comprobante(
    gasto_id: int,
    archivo: UploadFile = File(...),
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> GastoRead:
    datos = await archivo.read()
    return await service.subir(actor, gasto_id, datos, archivo.filename or "", archivo.content_type)


@router.delete(
    "/gastos/{gasto_id}/archivos/{archivo_id}",
    response_model=GastoRead,
    summary="Quitar comprobante",
)
async def quitar_comprobante(
    gasto_id: int,
    archivo_id: int,
    actor: Actor = Depends(get_actor),
    service: GastosService = Depends(gastos),
) -> GastoRead:
    return await service.quitar_archivo(actor, gasto_id, archivo_id)
