"""Vocabulario del módulo finanzas.

Las formas de pago y los tipos de operación usan las mismas opciones que la
plantilla de movimientos del sistema contable: así un gasto exportado
entra a contabilidad sin traducir nada.
"""

from __future__ import annotations

from enum import StrEnum


class FormaPago(StrEnum):
    TRANSFERENCIA = "transferencia"
    CHEQUE = "cheque"
    DOMICILIACION = "domiciliacion"
    EFECTIVO = "efectivo"
    DEBITO = "debito"
    FALTA_DE_CFDI = "falta_de_CFDI"
    COMPENSACION = "compensacion"


#: Como los escribe la plantilla del sistema contable (columna FORMA DE PAGO).
NOMBRE_FORMA_PAGO: dict[FormaPago, str] = {
    FormaPago.TRANSFERENCIA: "Transferencia",
    FormaPago.CHEQUE: "Cheque",
    FormaPago.DOMICILIACION: "Domiciliación",
    FormaPago.EFECTIVO: "Efectivo",
    FormaPago.DEBITO: "Debito",
    FormaPago.FALTA_DE_CFDI: "Falta de CFDI",
    FormaPago.COMPENSACION: "Compensación",
}


class TipoOperacion(StrEnum):
    GASTO = "gasto"
    COMPRA = "compra"
    PROVEEDORES = "proveedores"
    NOMINA = "nomina"
    IMPUESTOS = "impuestos"
    GASTO_COMPRA_SIN_CFDI = "gasto_compra_sin_cfdi"
    NO_DEDUCIBLE = "no_deducible"
    OTRO = "otro"


#: Como los escribe la plantilla del sistema contable (columna TIPO DE OPERACIÓN).
NOMBRE_TIPO_OPERACION: dict[TipoOperacion, str] = {
    TipoOperacion.GASTO: "Gasto",
    TipoOperacion.COMPRA: "Compra",
    TipoOperacion.PROVEEDORES: "Proveedores",
    TipoOperacion.NOMINA: "Nómina",
    TipoOperacion.IMPUESTOS: "Impuestos (CFDI)",
    TipoOperacion.GASTO_COMPRA_SIN_CFDI: "Gasto/Compra (Sin CFDI)",
    TipoOperacion.NO_DEDUCIBLE: "No deducible",
    TipoOperacion.OTRO: "Otro",
}


class CategoriaGasto(StrEnum):
    """Para qué fue el gasto; es de Picasso, el sistema contable no la tiene (va en la nota)."""

    MANTENIMIENTO = "mantenimiento"
    LIMPIEZA = "limpieza"
    AMENIDADES = "amenidades"
    FRUTAS_VERDURAS = "frutas_verduras"
    ABARROTES = "abarrotes"
    BEBIDAS = "bebidas"
    COCINA_BAR = "cocina_bar"
    SERVICIOS = "servicios"
    NOMINA = "nomina"
    ADMINISTRACION = "administracion"
    OTRO = "otro"


NOMBRE_CATEGORIA: dict[CategoriaGasto, str] = {
    CategoriaGasto.MANTENIMIENTO: "Mantenimiento y reparaciones",
    CategoriaGasto.LIMPIEZA: "Limpieza y lavandería",
    CategoriaGasto.AMENIDADES: "Amenidades e insumos de cuarto",
    CategoriaGasto.FRUTAS_VERDURAS: "Frutas y verduras",
    CategoriaGasto.ABARROTES: "Abarrotes",
    CategoriaGasto.BEBIDAS: "Bebidas",
    CategoriaGasto.COCINA_BAR: "Insumos de cocina y bar",
    CategoriaGasto.SERVICIOS: "Luz, agua, gas e internet",
    CategoriaGasto.NOMINA: "Nómina y personal",
    CategoriaGasto.ADMINISTRACION: "Administración",
    CategoriaGasto.OTRO: "Otro",
}


class EstadoGasto(StrEnum):
    REGISTRADO = "registrado"
    ANULADO = "anulado"


class TipoArchivo(StrEnum):
    """Lo que se adjunta a un gasto: foto del ticket, PDF o el XML de la factura."""

    FOTO = "foto"
    PDF = "pdf"
    XML = "xml"
