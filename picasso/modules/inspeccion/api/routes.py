"""HTTP del módulo inspeccion: checklists, folios, renta y reportes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status

from jfastframework.auth import Principal
from jfastframework.errors import ForbiddenError
from jfastframework.plugins.builtin.auth import require_auth
from jfastframework.plugins.builtin.database import DbSession

from modules.sucursal import public as sucursal_publica
from shared.enums import Rol

from ..enums import Prioridad, TipoEvidencia
from ..models import (
    Actor,
    AvanceCrear,
    CierreCrear,
    ConteoFolios,
    DecisionCrear,
    DecisionRead,
    EvidenciaRead,
    HabitacionEstado,
    HabitacionExpediente,
    IncidenciaActualizar,
    IncidenciaDetalle,
    IncidenciaResumen,
    Indicadores,
    Panel,
    PuntoGuardar,
    ResultadoRead,
    RevisionCrear,
    RevisionDetalle,
    RevisionResumen,
)
from ..repositories import InspeccionRepository
from ..services import (
    Archivos,
    IncidenciaService,
    ReporteService,
    RevisionService,
    periodo,
    rango_utc,
)

router = APIRouter(tags=["inspeccion"], dependencies=[Depends(require_auth)])


async def get_actor(session: DbSession, caller: Principal = Depends(require_auth)) -> Actor:
    perfil = await sucursal_publica.perfil_de(
        session, tenant_id=None, user_id=caller.subject, roles=caller.roles
    )
    if perfil is None:
        raise ForbiddenError("Esta cuenta no tiene un puesto asignado.")
    return Actor(
        user_id=perfil.user_id,
        nombre=perfil.nombre,
        rol=perfil.rol,
        sucursal_id=perfil.sucursal_id,
    )


def _archivos(request: Request) -> Archivos:
    storage = request.app.state.jfast.require("storage")
    return Archivos(storage.disk("private"))


async def revisiones(request: Request, session: DbSession) -> RevisionService:
    return RevisionService(InspeccionRepository(session), _archivos(request))


async def incidencias(request: Request, session: DbSession) -> IncidenciaService:
    return IncidenciaService(InspeccionRepository(session), _archivos(request))


async def reportes(session: DbSession) -> ReporteService:
    return ReporteService(InspeccionRepository(session))


def _sin_ama(actor: Actor) -> Actor:
    if actor.rol is Rol.AMA_LLAVES:
        raise ForbiddenError("Los reportes son para gerencia y propietarios.")
    return actor


# -- checklists y tablero ---------------------------------------------------


@router.get("/checklists/{rol}", summary="Los puntos de un checklist")
async def checklist(rol: Rol) -> list[dict[str, object]]:
    return RevisionService.catalogo(rol)


@router.get(
    "/tablero", response_model=list[HabitacionEstado], summary="Habitaciones y sus pendientes"
)
async def tablero(
    sucursal_id: int | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> list[HabitacionEstado]:
    return await service.tablero(actor, sucursal_id)


# -- revisiones -------------------------------------------------------------


@router.post(
    "/revisiones",
    response_model=RevisionDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir (o retomar) la revisión de una habitación",
)
async def iniciar_revision(
    payload: RevisionCrear,
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> RevisionDetalle:
    return await service.iniciar(actor, payload.habitacion_id)


@router.get("/revisiones", response_model=list[RevisionResumen], summary="Revisiones")
async def listar_revisiones(
    sucursal_id: int | None = Query(None),
    habitacion_id: int | None = Query(None),
    rol: Rol | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> list[RevisionResumen]:
    p = periodo(desde, hasta)
    inicio, fin = rango_utc(p.desde, p.hasta)
    return await service.listar(
        actor,
        sucursal_id=sucursal_id,
        habitacion_id=habitacion_id,
        rol=rol,
        desde=inicio,
        hasta=fin,
    )


@router.get("/revisiones/{revision_id}", response_model=RevisionDetalle, summary="Una revisión")
async def detalle_revision(
    revision_id: int,
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> RevisionDetalle:
    return await service.detalle(actor, revision_id)


@router.put(
    "/revisiones/{revision_id}/puntos/{codigo}",
    response_model=ResultadoRead,
    summary="Resultado de un punto",
)
async def guardar_punto(
    revision_id: int,
    codigo: str,
    payload: PuntoGuardar,
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> ResultadoRead:
    return await service.guardar_punto(actor, revision_id, codigo, payload)


@router.post(
    "/revisiones/{revision_id}/puntos/{codigo}/fotos",
    response_model=EvidenciaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Foto de un punto",
)
async def foto_de_punto(
    revision_id: int,
    codigo: str,
    foto: UploadFile = File(...),
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> EvidenciaRead:
    datos = await foto.read()
    return await service.foto_de_punto(actor, revision_id, codigo, datos, foto.content_type)


@router.delete(
    "/revisiones/{revision_id}/fotos/{evidencia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar una foto tomada por error",
)
async def quitar_foto(
    revision_id: int,
    evidencia_id: int,
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> None:
    await service.quitar_foto(actor, revision_id, evidencia_id)


@router.post(
    "/revisiones/{revision_id}/resto-bien",
    response_model=RevisionDetalle,
    summary="Lo demás está bien: los puntos sin tocar pasan a Bien (en bloque)",
)
async def resto_bien(
    revision_id: int,
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> RevisionDetalle:
    return await service.resto_bien(actor, revision_id)


@router.post(
    "/revisiones/{revision_id}/completar",
    response_model=RevisionResumen,
    summary="Terminar la revisión (ama de llaves: enviarla al gerente)",
)
async def completar(
    revision_id: int,
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> RevisionResumen:
    return await service.completar(actor, revision_id)


# -- habitación ---------------------------------------------------------------


@router.post(
    "/habitaciones/{habitacion_id}/renta",
    response_model=DecisionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Decisión del gerente: puede o no puede rentarse",
)
async def decidir_renta(
    habitacion_id: int,
    payload: DecisionCrear,
    actor: Actor = Depends(get_actor),
    service: RevisionService = Depends(revisiones),
) -> DecisionRead:
    return await service.decidir_renta(actor, habitacion_id, payload)


@router.get(
    "/habitaciones/{habitacion_id}/expediente",
    response_model=HabitacionExpediente,
    summary="Reporte por habitación",
)
async def expediente(
    habitacion_id: int,
    actor: Actor = Depends(get_actor),
    service: ReporteService = Depends(reportes),
) -> HabitacionExpediente:
    return await service.expediente(_sin_ama(actor), habitacion_id)


# -- incidencias --------------------------------------------------------------


@router.get("/incidencias", response_model=list[IncidenciaResumen], summary="Folios")
async def listar_incidencias(
    estado: str | None = Query(None, description="abiertas, todas o un estado"),
    sucursal_id: int | None = Query(None),
    habitacion_id: int | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    buscar: str | None = Query(None, max_length=60),
    prioridad: Prioridad | None = Query(None, description="alta, media o baja"),
    actor: Actor = Depends(get_actor),
    service: IncidenciaService = Depends(incidencias),
) -> list[IncidenciaResumen]:
    inicio = fin = None
    if desde or hasta:
        p = periodo(desde, hasta)
        inicio, fin = rango_utc(p.desde, p.hasta)
    return await service.listar(
        actor,
        sucursal_id=sucursal_id,
        habitacion_id=habitacion_id,
        estado=estado,
        desde=inicio,
        hasta=fin,
        buscar=buscar,
        prioridad=prioridad,
    )


# Antes de /incidencias/{incidencia_id}: si no, «conteo» se toma por un id.
@router.get(
    "/incidencias/conteo",
    response_model=list[ConteoFolios],
    summary="Folios por estado y prioridad",
)
async def conteo_incidencias(
    sucursal_id: int | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    buscar: str | None = Query(None, max_length=60),
    actor: Actor = Depends(get_actor),
    service: IncidenciaService = Depends(incidencias),
) -> list[ConteoFolios]:
    inicio = fin = None
    if desde or hasta:
        p = periodo(desde, hasta)
        inicio, fin = rango_utc(p.desde, p.hasta)
    return await service.conteo(
        actor, sucursal_id=sucursal_id, desde=inicio, hasta=fin, buscar=buscar
    )


@router.get(
    "/incidencias/{incidencia_id}", response_model=IncidenciaDetalle, summary="Expediente del folio"
)
async def detalle_incidencia(
    incidencia_id: int,
    actor: Actor = Depends(get_actor),
    service: IncidenciaService = Depends(incidencias),
) -> IncidenciaDetalle:
    return await service.detalle(actor, incidencia_id)


@router.patch(
    "/incidencias/{incidencia_id}",
    response_model=IncidenciaDetalle,
    summary="Prioridad, responsable o poner en atención",
)
async def actualizar_incidencia(
    incidencia_id: int,
    payload: IncidenciaActualizar,
    actor: Actor = Depends(get_actor),
    service: IncidenciaService = Depends(incidencias),
) -> IncidenciaDetalle:
    return await service.actualizar(actor, incidencia_id, payload)


@router.post(
    "/incidencias/{incidencia_id}/avances",
    response_model=IncidenciaDetalle,
    summary="Anotar un avance",
)
async def avance(
    incidencia_id: int,
    payload: AvanceCrear,
    actor: Actor = Depends(get_actor),
    service: IncidenciaService = Depends(incidencias),
) -> IncidenciaDetalle:
    return await service.avance(actor, incidencia_id, payload.nota)


@router.post(
    "/incidencias/{incidencia_id}/fotos",
    response_model=EvidenciaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Foto de avance o de la reparación terminada",
)
async def foto_de_incidencia(
    incidencia_id: int,
    foto: UploadFile = File(...),
    tipo: TipoEvidencia = Form(TipoEvidencia.REPARACION),
    nota: str | None = Form(None),
    actor: Actor = Depends(get_actor),
    service: IncidenciaService = Depends(incidencias),
) -> EvidenciaRead:
    datos = await foto.read()
    return await service.foto(actor, incidencia_id, tipo, datos, foto.content_type, nota)


@router.post(
    "/incidencias/{incidencia_id}/cerrar",
    response_model=IncidenciaDetalle,
    summary="Actualizar y cerrar (solo gerente, con foto y explicación)",
)
async def cerrar(
    incidencia_id: int,
    payload: CierreCrear,
    actor: Actor = Depends(get_actor),
    service: IncidenciaService = Depends(incidencias),
) -> IncidenciaDetalle:
    return await service.cerrar(actor, incidencia_id, payload.correccion)


# -- propietarios -------------------------------------------------------------


@router.get("/panel", response_model=Panel, summary="Las sucursales en una sola vista")
async def panel(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: ReporteService = Depends(reportes),
) -> Panel:
    return await service.panel(_sin_ama(actor), periodo(desde, hasta))


@router.get("/indicadores", response_model=Indicadores, summary="Indicadores del periodo")
async def indicadores(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    actor: Actor = Depends(get_actor),
    service: ReporteService = Depends(reportes),
) -> Indicadores:
    return await service.indicadores(_sin_ama(actor), periodo(desde, hasta))
