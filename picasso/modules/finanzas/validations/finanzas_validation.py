"""Reglas del módulo finanzas que un esquema no puede ver."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from jfastframework.errors import ForbiddenError, ValidationError

from shared.enums import Rol

from ..models import Actor

#: Quién ve y captura finanzas: gerentes (su sucursal), administración y
#: propietarios. La ama de llaves no.
PUESTOS_FINANZAS = (Rol.GERENTE, Rol.ADMIN, Rol.PROPIETARIO)

_RFC = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")

#: Palabras que nombran la tienda o el rubro, no lo que se compró. Una partida
#: que solo dice eso no se acepta: «Verdulería $700» no se puede auditar.
_GENERICAS = {
    "varios",
    "varias",
    "compra",
    "compras",
    "gasto",
    "gastos",
    "mercado",
    "despensa",
    "verduleria",
    "fruteria",
    "abarrotes",
    "ferreteria",
    "tlapaleria",
    "papeleria",
    "material",
    "materiales",
    "insumos",
    "otros",
    "otro",
    "mandado",
    "super",
    "supermercado",
    "tienda",
    "frutas",
    "verduras",
    "frutas y verduras",
    "limpieza",
    "mantenimiento",
    "refacciones",
    "productos",
    "articulos",
    "cosas",
    "miscelanea",
}


def exigir_finanzas(actor: Actor) -> None:
    if actor.rol not in PUESTOS_FINANZAS:
        raise ForbiddenError("Finanzas es para gerencia, administración y propietarios.")


def exigir_quien_ve_todas(actor: Actor) -> None:
    if not actor.ve_todas:
        raise ForbiddenError("Solo administración y propietarios.")


def sucursal_para(actor: Actor, pedida: int | None) -> int:
    """El gerente siempre trabaja en la suya; quien ve todas tiene que decir cuál."""
    exigir_finanzas(actor)
    if actor.ve_todas:
        if pedida is None:
            raise ValidationError("Elige la sucursal del gasto.")
        return pedida
    if actor.sucursal_id is None:
        raise ForbiddenError("Tu cuenta no tiene sucursal asignada.")
    if pedida is not None and pedida != actor.sucursal_id:
        raise ForbiddenError("Solo puedes registrar gastos de tu sucursal.")
    return actor.sucursal_id


def sucursal_visible(actor: Actor, pedida: int | None) -> int | None:
    """Filtro de sucursal para consultar: el gerente solo ve la suya."""
    exigir_finanzas(actor)
    if actor.ve_todas:
        return pedida
    return actor.sucursal_id


def exigir_gasto_de(actor: Actor, sucursal_id: int) -> None:
    exigir_finanzas(actor)
    if not actor.puede_ver(sucursal_id):
        raise ForbiddenError("Ese gasto es de otra sucursal.")


def exigir_puede_eliminar(actor: Actor, exportado: bool) -> None:
    """Ya en contabilidad, solo administración o propietarios lo sacan."""
    if exportado and not actor.ve_todas:
        raise ForbiddenError(
            "Ese gasto ya se mandó a contabilidad: pídele a administración que lo elimine."
        )


def exigir_editable(estado: str) -> None:
    if estado == "anulado":
        raise ValidationError("El gasto está anulado: ya no se cambia.")


def liga_de_incidencia(gasto_sucursal_id: int, incidencia_sucursal_id: int) -> None:
    if gasto_sucursal_id != incidencia_sucursal_id:
        raise ValidationError("El folio es de otra sucursal que el gasto.")


def normalizar_rfc(rfc: str | None) -> str | None:
    if rfc is None or not rfc.strip():
        return None
    limpio = rfc.strip().upper().replace(" ", "").replace("-", "")
    if not _RFC.match(limpio):
        raise ValidationError("El RFC no tiene el formato del SAT (12 o 13 caracteres).")
    return limpio


def no_en_el_futuro(fecha: date, hoy: date) -> None:
    if fecha > hoy + timedelta(days=1):
        raise ValidationError("La fecha del gasto no puede ser futura.")


def rango(desde: date, hasta: date, *, max_dias: int = 400) -> None:
    if desde > hasta:
        raise ValidationError("La fecha inicial va antes de la final.")
    if (hasta - desde).days > max_dias:
        raise ValidationError(f"El periodo máximo es de {max_dias} días.")


def articulo(descripcion: str) -> str:
    """Llave para agrupar el mismo artículo: minúsculas, sin acentos ni espacios de más."""
    texto = unicodedata.normalize("NFKD", descripcion.lower())
    sin_acentos = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9ñ ./-]", " ", sin_acentos).split())[:120]


def exigir_desglose(descripcion: str) -> None:
    if articulo(descripcion) in _GENERICAS:
        raise ValidationError(
            f"«{descripcion.strip()}» no dice qué se compró. Desglosa cosa por cosa: "
            "por ejemplo «Lechuga» 10 pzas, «Jitomate» 2 kg."
        )


def importe_partida(cantidad: Decimal, precio_unitario: Decimal) -> Decimal:
    return (cantidad * precio_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
