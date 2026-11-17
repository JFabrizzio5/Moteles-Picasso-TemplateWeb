"""Reglas del módulo sucursal."""

from __future__ import annotations

from typing import Any

from jfastframework.accounts import AccountsService
from jfastframework.errors import ConflictError, NotFoundError

from shared.enums import PRIORIDAD_ROL, Rol

from ..models import (
    CuartoSincronizar,
    Equipo,
    EquipoCreate,
    EquipoUpdate,
    Habitacion,
    HabitacionCreate,
    HabitacionRead,
    HabitacionUpdate,
    PerfilRead,
    Personal,
    PersonalCreate,
    Sincronizacion,
    Sucursal,
    SucursalRead,
    SucursalUpdate,
)
from ..repositories import (
    EquipoRepository,
    HabitacionRepository,
    PersonalRepository,
    SucursalRepository,
)
from ..validations import validar_asignacion

#: Permisos que lleva cada puesto. Viajan en el token como scopes.
PERMISOS_POR_ROL: dict[Rol, list[str]] = {
    Rol.ADMIN: ["accounts:admin", "sucursales:admin", "reportes:leer"],
    Rol.PROPIETARIO: ["reportes:leer"],
    Rol.GERENTE: ["revision:gerente", "incidencias:gestionar", "renta:decidir", "reportes:leer"],
    Rol.AMA_LLAVES: ["revision:ama"],
}

DESCRIPCION_ROL: dict[Rol, str] = {
    Rol.ADMIN: "Administración del sistema",
    Rol.PROPIETARIO: "Consulta consolidada de las seis sucursales",
    Rol.GERENTE: "Inspecciona, decide la renta y cierra folios de su sucursal",
    Rol.AMA_LLAVES: "Revisa la habitación después de cada limpieza",
}


def rol_principal(roles: frozenset[str] | set[str]) -> Rol | None:
    for rol in PRIORIDAD_ROL:
        if rol.value in roles:
            return rol
    return None


class SucursalService:
    def __init__(
        self,
        sucursales: SucursalRepository,
        habitaciones: HabitacionRepository,
        personal: PersonalRepository,
        equipos: EquipoRepository,
    ) -> None:
        self.sucursales = sucursales
        self.habitaciones = habitaciones
        self.personal = personal
        self.equipos = equipos

    # -- sucursales ------------------------------------------------------

    async def listar(self) -> list[SucursalRead]:
        conteo = await self.sucursales.conteo_habitaciones()
        salida = []
        for sucursal in await self.sucursales.todas():
            leida = SucursalRead.model_validate(sucursal, from_attributes=True)
            leida.habitaciones = conteo.get(sucursal.id, 0)
            salida.append(leida)
        return salida

    async def actualizar(self, sucursal_id: int, payload: SucursalUpdate) -> Sucursal:
        sucursal = await self.sucursales.get_or_raise(sucursal_id)
        return await self.sucursales.update(sucursal, **payload.model_dump(exclude_unset=True))

    # -- habitaciones ----------------------------------------------------

    async def habitaciones_de(
        self, sucursal_id: int, *, solo_activas: bool
    ) -> list[HabitacionRead]:
        await self.sucursales.get_or_raise(sucursal_id)
        filas = await self.habitaciones.de_sucursal(sucursal_id, solo_activas=solo_activas)
        equipos = await self.equipos.ids_de([h.id for h in filas])
        return [self._leer(h, equipos.get(h.id, [])) for h in filas]

    @staticmethod
    def _leer(habitacion: Habitacion, equipo_ids: list[int]) -> HabitacionRead:
        leida = HabitacionRead.model_validate(habitacion, from_attributes=True)
        leida.equipo_ids = sorted(equipo_ids)
        return leida

    # -- equipo de los cuartos ---------------------------------------------

    async def listar_equipos(self) -> list[Equipo]:
        return await self.equipos.todos()

    async def crear_equipo(self, payload: EquipoCreate) -> Equipo:
        nombre = payload.nombre.strip()
        if await self.equipos.find_one(nombre=nombre):
            raise ConflictError(f"«{nombre}» ya está en el catálogo")
        return await self.equipos.create(nombre=nombre, categoria=payload.categoria.strip())

    async def actualizar_equipo(self, equipo_id: int, payload: EquipoUpdate) -> Equipo:
        equipo = await self.equipos.get_or_raise(equipo_id)
        cambios = payload.model_dump(exclude_unset=True)
        if cambios.get("nombre"):
            otro = await self.equipos.find_one(nombre=cambios["nombre"].strip())
            if otro is not None and otro.id != equipo.id:
                raise ConflictError(f"«{cambios['nombre']}» ya está en el catálogo")
        return await self.equipos.update(equipo, **cambios)

    async def asignar_equipos(self, habitacion_id: int, equipo_ids: list[int]) -> HabitacionRead:
        habitacion = await self.habitaciones.get_or_raise(habitacion_id)
        unicos = sorted(set(equipo_ids))
        conocidos = {e.id for e in await self.equipos.todos()}
        faltan = [e for e in unicos if e not in conocidos]
        if faltan:
            raise NotFoundError(f"equipo {faltan} no existe")
        await self.equipos.asignar(habitacion.id, unicos)
        return self._leer(habitacion, unicos)

    async def crear_habitacion(self, sucursal_id: int, payload: HabitacionCreate) -> Habitacion:
        await self.sucursales.get_or_raise(sucursal_id)
        numero = payload.numero.strip()
        if await self.habitaciones.find_one(sucursal_id=sucursal_id, numero=numero):
            raise ConflictError(f"la habitación {numero} ya existe en esta sucursal")
        datos = payload.model_dump()
        datos["numero"] = numero
        return await self.habitaciones.create(sucursal_id=sucursal_id, **datos)

    async def actualizar_habitacion(
        self, habitacion_id: int, payload: HabitacionUpdate
    ) -> HabitacionRead:
        habitacion = await self.habitaciones.get_or_raise(habitacion_id)
        habitacion = await self.habitaciones.update(
            habitacion, **payload.model_dump(exclude_unset=True)
        )
        # Se responde con su equipo: la pantalla de Ajustes reemplaza la tarjeta
        # con esta respuesta, y sin equipo_ids el cuarto se veía "sin equipo".
        equipos = await self.equipos.ids_de([habitacion.id])
        return self._leer(habitacion, equipos.get(habitacion.id, []))

    async def sincronizar_habitaciones(
        self, sucursal_id: int, cuartos: list[CuartoSincronizar]
    ) -> Sincronizacion:
        """Deja los cuartos como los conoce Kairos, sin borrar ni dar de baja nada.

        Alta del que falta; al que ya existe se le corrige el tipo, la sección y
        si tiene jacuzzi o sauna (eso lo decide la tarifa). Alberca, terraza,
        equipo y si está activo se quedan como los dejó administración. Un cuarto
        que Kairos no rentó en el periodo solo se reporta: puede estar en obra.
        """
        await self.sucursales.get_or_raise(sucursal_id)
        actuales = {
            h.numero: h
            for h in await self.habitaciones.de_sucursal(sucursal_id, solo_activas=False)
        }
        resultado = Sincronizacion()
        vistos: set[str] = set()
        for c in cuartos:
            numero = c.numero.strip()
            if not numero or numero in vistos:
                continue
            vistos.add(numero)
            datos: dict[str, Any] = {
                "tipo": c.tipo,
                "seccion": c.seccion,
                "tiene_jacuzzi": c.tiene_jacuzzi,
                "tiene_sauna": c.tiene_sauna,
            }
            # Alberca y terraza solo se prenden: la tarifa no dice si faltan.
            datos.update({k: True for k in ("tiene_alberca", "tiene_terraza") if getattr(c, k)})
            h = actuales.get(numero)
            if h is None:
                await self.habitaciones.create(sucursal_id=sucursal_id, numero=numero, **datos)
                resultado.nuevos.append(numero)
            elif any(getattr(h, k) != v for k, v in datos.items()):
                await self.habitaciones.update(h, **datos)
                resultado.actualizados.append(numero)
            else:
                resultado.sin_cambio += 1
        resultado.solo_en_picasso = [n for n in actuales if n not in vistos]
        return resultado

    # -- personal --------------------------------------------------------

    async def perfil(
        self, user_id: str, roles: frozenset[str], email: str | None = None
    ) -> PerfilRead:
        persona = await self.personal.de_usuario(user_id)
        rol = rol_principal(roles) or (Rol(persona.rol) if persona else None)
        if rol is None:
            raise NotFoundError("esta cuenta no tiene un puesto asignado")
        sucursal = None
        if persona is not None and persona.sucursal_id is not None:
            sucursal = await self.sucursales.get(persona.sucursal_id)
        return PerfilRead(
            user_id=user_id,
            nombre=persona.nombre if persona else (email or "Administración"),
            email=email,
            rol=rol,
            sucursal_id=sucursal.id if sucursal else None,
            sucursal_nombre=sucursal.nombre if sucursal else None,
            sucursal_clave=sucursal.clave if sucursal else None,
        )

    async def listar_personal(self) -> list[Personal]:
        return await self.personal.todos()

    async def asegurar_roles(self, cuentas: AccountsService) -> None:
        for rol, permisos in PERMISOS_POR_ROL.items():
            await cuentas.ensure_role(
                rol.value,
                tenant_id=None,
                permissions=permisos,
                description=DESCRIPCION_ROL[rol],
            )

    async def crear_personal(self, cuentas: AccountsService, payload: PersonalCreate) -> Personal:
        validar_asignacion(payload.rol, payload.sucursal_id)
        if payload.sucursal_id is not None:
            await self.sucursales.get_or_raise(payload.sucursal_id)
        await self.asegurar_roles(cuentas)
        usuario = await cuentas.create_user(
            str(payload.email),
            password=payload.password,
            display_name=payload.nombre,
            role_names=[payload.rol.value],
            email_verified=True,
        )
        return await self.personal.create(
            user_id=usuario.id,
            nombre=payload.nombre,
            rol=payload.rol.value,
            sucursal_id=payload.sucursal_id,
        )
