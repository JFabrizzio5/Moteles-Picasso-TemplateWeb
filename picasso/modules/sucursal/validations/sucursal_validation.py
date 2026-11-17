"""Reglas puras del módulo sucursal."""

from __future__ import annotations

from jfastframework.errors import ValidationError

from shared.enums import Rol


def validar_asignacion(rol: Rol, sucursal_id: int | None) -> None:
    """Gerente y ama de llaves trabajan en una sucursal; los demás ven todas."""
    if rol in (Rol.GERENTE, Rol.AMA_LLAVES) and sucursal_id is None:
        raise ValidationError(f"un puesto de {rol.value} necesita una sucursal")
    if rol in (Rol.PROPIETARIO, Rol.ADMIN) and sucursal_id is not None:
        raise ValidationError(f"un puesto de {rol.value} ve todas las sucursales; no lleva una")
