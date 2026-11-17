"""Contratos del módulo finanzas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import Rol

from ..enums import CategoriaGasto, FormaPago, TipoArchivo, TipoOperacion


@dataclass(frozen=True, slots=True)
class Actor:
    """Quién pide: puesto, nombre y sucursal (None = todas)."""

    user_id: str
    nombre: str
    rol: Rol
    sucursal_id: int | None

    @property
    def ve_todas(self) -> bool:
        return self.rol in (Rol.ADMIN, Rol.PROPIETARIO)

    def puede_ver(self, sucursal_id: int) -> bool:
        return self.ve_todas or self.sucursal_id == sucursal_id


# -- ingresos ------------------------------------------------------------------


class IngresoDiaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sucursal_id: int
    fecha: date
    habitaciones: Decimal
    rentas: int
    extras: Decimal
    room_service: Decimal
    comandas: int
    gastos_kairos: Decimal
    total: Decimal
    con_detalle: bool


class TarifaRead(BaseModel):
    tarifa: str
    cantidad: int
    importe: Decimal


class FilaSucursalFinanzas(BaseModel):
    sucursal_id: int
    clave: str
    nombre: str
    dias: int
    rentas: int
    habitaciones: Decimal
    room_service: Decimal
    extras: Decimal
    #: Habitaciones + room service + extras (sin restar lo anotado en Kairos).
    ingresos: Decimal
    gastos_kairos: Decimal
    #: Los gastos capturados en Picasso en el periodo.
    gastos: Decimal
    gastos_n: int
    #: Ingresos menos gastos de Picasso.
    utilidad: Decimal
    ultimo_ok: datetime | None
    ultimo_error: str | None


class ResumenFinanzas(BaseModel):
    desde: date
    hasta: date
    sucursales: list[FilaSucursalFinanzas]
    rentas: int
    ingresos: Decimal
    gastos: Decimal
    utilidad: Decimal


class PuntoSerie(BaseModel):
    """Un tramo de la gráfica: un día, una semana (empieza en lunes) o un mes."""

    inicio: date
    fin: date
    ingresos: Decimal
    gastos: Decimal


class SerieFinanzas(BaseModel):
    desde: date
    hasta: date
    #: dia hasta 62 días, semana hasta 200, mes después.
    agrupado: str
    puntos: list[PuntoSerie]


class FuenteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sucursal_clave: str
    nombre_kairos: str
    url_base: str
    activo: bool
    primer_dia: date | None
    historial_desde: date | None
    ultima_corrida: datetime | None
    ultimo_ok: datetime | None
    ultimo_error: str | None


class FuenteActualizar(BaseModel):
    url_base: str | None = Field(None, max_length=200, pattern=r"^https?://")
    activo: bool | None = None


class ImportarIngresos(BaseModel):
    """Volver a leer de Kairos un rango (el cron ya lee los últimos días)."""

    desde: date
    hasta: date
    sucursal_clave: str | None = Field(None, max_length=3)
    #: Con tarifas y cada renta, o solo el resumen del día (más ligero para años).
    detalle: bool = True


# -- gastos --------------------------------------------------------------------


class ArchivoRead(BaseModel):
    id: int
    tipo: TipoArchivo
    nombre: str
    url: str
    uuid_cfdi: str | None


class PartidaCrear(BaseModel):
    """Una cosa comprada. El importe lo calcula el servidor: cantidad por precio."""

    descripcion: str = Field(min_length=3, max_length=120)
    cantidad: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unidad: str = Field("pza", min_length=1, max_length=12)
    precio_unitario: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    #: Sin categoría, toma la del gasto.
    categoria: CategoriaGasto | None = None


class PartidaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden: int
    descripcion: str
    cantidad: Decimal
    unidad: str
    precio_unitario: Decimal
    importe: Decimal
    categoria: CategoriaGasto


class GastoCrear(BaseModel):
    sucursal_id: int | None = Field(None, description="Obligatorio para quien ve todas")
    fecha: date
    #: La categoría principal; cada partida puede tener la suya.
    categoria: CategoriaGasto
    concepto: str = Field(min_length=3, max_length=200)
    proveedor: str = Field(min_length=2, max_length=120)
    rfc_proveedor: str | None = Field(None, max_length=13)
    forma_pago: FormaPago
    tipo_operacion: TipoOperacion = TipoOperacion.GASTO
    banco: str | None = Field(None, max_length=40)
    referencia: str | None = Field(None, max_length=40)
    partidas: list[PartidaCrear] = Field(min_length=1, max_length=100)
    nota: str | None = Field(None, max_length=1000)
    #: Folios de mantenimiento de la misma sucursal a los que se carga el gasto.
    incidencia_ids: list[int] = Field(default_factory=list, max_length=50)


class GastoActualizar(BaseModel):
    """Parcial. `incidencia_ids` reemplaza los folios ligados ([] los quita todos)."""

    fecha: date | None = None
    categoria: CategoriaGasto | None = None
    concepto: str | None = Field(None, min_length=3, max_length=200)
    proveedor: str | None = Field(None, min_length=2, max_length=120)
    rfc_proveedor: str | None = Field(None, max_length=13)
    forma_pago: FormaPago | None = None
    tipo_operacion: TipoOperacion | None = None
    banco: str | None = Field(None, max_length=40)
    referencia: str | None = Field(None, max_length=40)
    #: Si llega, reemplaza todas las partidas (y con ellas el total).
    partidas: list[PartidaCrear] | None = Field(None, min_length=1, max_length=100)
    nota: str | None = Field(None, max_length=1000)
    incidencia_ids: list[int] | None = Field(None, max_length=50)


class FolioDelGasto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incidencia_id: int
    folio: str
    titulo: str
    habitacion_numero: str


class CostoFolio(BaseModel):
    """Lo gastado en un folio de mantenimiento (suma de los gastos ligados)."""

    incidencia_id: int
    gastos: int
    total: Decimal


class GastoRead(BaseModel):
    id: int
    folio: str
    sucursal_id: int
    sucursal_clave: str
    sucursal_nombre: str
    fecha: date
    categoria: CategoriaGasto
    concepto: str
    proveedor: str
    rfc_proveedor: str | None
    forma_pago: FormaPago
    tipo_operacion: TipoOperacion
    banco: str | None
    referencia: str | None
    importe: Decimal
    nota: str | None
    incidencias: list[FolioDelGasto] = []
    capturo_nombre: str
    capturo_rol: Rol
    estado: str
    exportado_en: datetime | None
    creado_en: datetime
    partidas: list[PartidaRead] = []
    archivos: list[ArchivoRead] = []


# -- análisis para auditar ------------------------------------------------------


class GastoPorPersona(BaseModel):
    capturo_nombre: str
    capturo_rol: Rol
    sucursal_nombre: str
    gastos: int
    total: Decimal
    #: Categoría donde más gastó esa persona.
    categoria_mayor: CategoriaGasto | None


class GastoPorCategoria(BaseModel):
    categoria: CategoriaGasto
    partidas: int
    total: Decimal
    por_sucursal: dict[str, Decimal]


class GastoPorArticulo(BaseModel):
    articulo: str
    unidad: str
    categoria: CategoriaGasto
    veces: int
    cantidad: Decimal
    total: Decimal
    precio_promedio: Decimal
    precio_minimo: Decimal
    precio_maximo: Decimal
    sucursales: list[str]


class AnalisisGastos(BaseModel):
    desde: date
    hasta: date
    total: Decimal
    gastos: int
    por_persona: list[GastoPorPersona]
    por_categoria: list[GastoPorCategoria]
    por_articulo: list[GastoPorArticulo]


class ExportarEcont(BaseModel):
    """Qué gastos van al archivo: unos en particular o los de un periodo."""

    ids: list[int] | None = Field(None, max_length=2000)
    desde: date | None = None
    hasta: date | None = None
    sucursal_id: int | None = None
    #: Sin esto, los que ya se exportaron antes también van.
    solo_pendientes: bool = False
