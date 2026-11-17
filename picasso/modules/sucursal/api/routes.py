"""HTTP del módulo sucursal: perfil, sucursales, habitaciones y personal."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from jfastframework.accounts import AccountsService, require_permission
from jfastframework.auth import Principal
from jfastframework.plugins.builtin.auth import require_auth
from jfastframework.plugins.builtin.database import DbSession

from ..models import (
    EquipoCreate,
    EquipoRead,
    EquiposDeHabitacion,
    EquipoUpdate,
    HabitacionCreate,
    HabitacionRead,
    HabitacionUpdate,
    PerfilRead,
    PersonalCreate,
    PersonalRead,
    SucursalRead,
    SucursalUpdate,
)
from ..repositories import (
    EquipoRepository,
    HabitacionRepository,
    PersonalRepository,
    SucursalRepository,
)
from ..services import SucursalService

router = APIRouter(tags=["sucursal"], dependencies=[Depends(require_auth)])

ADMIN = Depends(require_permission("sucursales:admin"))


async def get_service(session: DbSession) -> SucursalService:
    return SucursalService(
        SucursalRepository(session),
        HabitacionRepository(session),
        PersonalRepository(session),
        EquipoRepository(session),
    )


@router.get("/perfil", response_model=PerfilRead, summary="Quién soy y qué veo")
async def perfil(
    caller: Principal = Depends(require_auth),
    service: SucursalService = Depends(get_service),
) -> PerfilRead:
    return await service.perfil(caller.subject, caller.roles, caller.claims.get("email"))


@router.get("/sucursales", response_model=list[SucursalRead], summary="Las sucursales")
async def listar_sucursales(service: SucursalService = Depends(get_service)) -> list[SucursalRead]:
    return await service.listar()


@router.patch(
    "/sucursales/{sucursal_id}",
    response_model=SucursalRead,
    dependencies=[ADMIN],
    summary="Cambiar nombre, foto o reglas de una sucursal",
)
async def actualizar_sucursal(
    sucursal_id: int,
    payload: SucursalUpdate,
    service: SucursalService = Depends(get_service),
) -> SucursalRead:
    sucursal = await service.actualizar(sucursal_id, payload)
    return SucursalRead.model_validate(sucursal, from_attributes=True)


@router.get(
    "/sucursales/{sucursal_id}/habitaciones",
    response_model=list[HabitacionRead],
    summary="Habitaciones de una sucursal",
)
async def habitaciones(
    sucursal_id: int,
    todas: bool = Query(False, description="Incluir las dadas de baja"),
    service: SucursalService = Depends(get_service),
) -> list[HabitacionRead]:
    return await service.habitaciones_de(sucursal_id, solo_activas=not todas)


@router.post(
    "/sucursales/{sucursal_id}/habitaciones",
    response_model=HabitacionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[ADMIN],
    summary="Alta de habitación",
)
async def crear_habitacion(
    sucursal_id: int,
    payload: HabitacionCreate,
    service: SucursalService = Depends(get_service),
) -> HabitacionRead:
    fila = await service.crear_habitacion(sucursal_id, payload)
    return HabitacionRead.model_validate(fila, from_attributes=True)


@router.patch(
    "/habitaciones/{habitacion_id}",
    response_model=HabitacionRead,
    dependencies=[ADMIN],
    summary="Amenidades o baja de una habitación",
)
async def actualizar_habitacion(
    habitacion_id: int,
    payload: HabitacionUpdate,
    service: SucursalService = Depends(get_service),
) -> HabitacionRead:
    return await service.actualizar_habitacion(habitacion_id, payload)


@router.get(
    "/personal", response_model=list[PersonalRead], dependencies=[ADMIN], summary="El personal"
)
async def listar_personal(service: SucursalService = Depends(get_service)) -> list[PersonalRead]:
    return [
        PersonalRead.model_validate(p, from_attributes=True)
        for p in await service.listar_personal()
    ]


@router.post(
    "/personal",
    response_model=PersonalRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[ADMIN],
    summary="Dar de alta a una persona con su cuenta",
)
async def crear_personal(
    payload: PersonalCreate,
    session: DbSession,
    service: SucursalService = Depends(get_service),
) -> PersonalRead:
    persona = await service.crear_personal(AccountsService(session), payload)
    return PersonalRead.model_validate(persona, from_attributes=True)


# -- equipo de los cuartos ----------------------------------------------------


@router.get("/equipos", response_model=list[EquipoRead], summary="Catálogo de equipo de cuarto")
async def listar_equipos(service: SucursalService = Depends(get_service)) -> list[EquipoRead]:
    return [
        EquipoRead.model_validate(e, from_attributes=True) for e in await service.listar_equipos()
    ]


@router.post(
    "/equipos",
    response_model=EquipoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[ADMIN],
    summary="Agregar al catálogo",
)
async def crear_equipo(
    payload: EquipoCreate, service: SucursalService = Depends(get_service)
) -> EquipoRead:
    return EquipoRead.model_validate(await service.crear_equipo(payload), from_attributes=True)


@router.patch(
    "/equipos/{equipo_id}",
    response_model=EquipoRead,
    dependencies=[ADMIN],
    summary="Renombrar, cambiar categoría o desactivar",
)
async def actualizar_equipo(
    equipo_id: int, payload: EquipoUpdate, service: SucursalService = Depends(get_service)
) -> EquipoRead:
    equipo = await service.actualizar_equipo(equipo_id, payload)
    return EquipoRead.model_validate(equipo, from_attributes=True)


@router.put(
    "/habitaciones/{habitacion_id}/equipos",
    response_model=HabitacionRead,
    dependencies=[ADMIN],
    summary="Lo que tiene un cuarto (reemplaza la lista)",
)
async def asignar_equipos(
    habitacion_id: int,
    payload: EquiposDeHabitacion,
    service: SucursalService = Depends(get_service),
) -> HabitacionRead:
    return await service.asignar_equipos(habitacion_id, payload.equipo_ids)
