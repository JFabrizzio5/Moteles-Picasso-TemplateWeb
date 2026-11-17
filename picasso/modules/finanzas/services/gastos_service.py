"""Gastos: se capturan en Picasso, se ligan a un folio y se exportan a E-Cont."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from jfastframework.errors import NotFoundError, ValidationError

from shared.enums import Rol

from ..enums import CategoriaGasto, FormaPago, TipoArchivo, TipoOperacion
from ..models import (
    Actor,
    AnalisisGastos,
    ArchivoRead,
    ExportarEcont,
    Gasto,
    GastoActualizar,
    GastoArchivo,
    GastoCrear,
    GastoPartida,
    GastoPorArticulo,
    GastoPorCategoria,
    GastoPorPersona,
    GastoRead,
    PartidaCrear,
    PartidaRead,
)
from ..repositories import FinanzasRepository
from ..validations import (
    articulo,
    exigir_desglose,
    exigir_editable,
    exigir_finanzas,
    exigir_gasto_de,
    importe_partida,
    liga_de_incidencia,
    no_en_el_futuro,
    normalizar_rfc,
    rango,
    sucursal_para,
    sucursal_visible,
)
from . import econt
from .comun import Comprobantes, ahora, hoy, uuid_de_cfdi
from .ingresos_service import Sucursal

#: Lo que finanzas necesita de un folio; lo da la fachada de inspeccion.
BuscarFolio = Callable[[int], Awaitable["FolioLigado | None"]]


class FolioLigado:
    def __init__(self, id: int, folio: str, titulo: str, sucursal_id: int) -> None:
        self.id = id
        self.folio = folio
        self.titulo = titulo
        self.sucursal_id = sucursal_id


class GastosService:
    def __init__(
        self,
        repo: FinanzasRepository,
        sucursales: list[Sucursal],
        comprobantes: Comprobantes,
        buscar_folio: BuscarFolio,
    ) -> None:
        self.repo = repo
        self.sucursales = {s.id: s for s in sucursales}
        self.comprobantes = comprobantes
        self.buscar_folio = buscar_folio

    def _sucursal(self, sucursal_id: int) -> Sucursal:
        s = self.sucursales.get(sucursal_id)
        if s is None:
            raise ValidationError("Esa sucursal no existe o está inactiva.")
        return s

    async def _ligar(self, gasto: Gasto, incidencia_id: int | None) -> None:
        if not incidencia_id:
            gasto.incidencia_id = None
            gasto.incidencia_folio = None
            gasto.incidencia_titulo = None
            return
        folio = await self.buscar_folio(incidencia_id)
        if folio is None:
            raise NotFoundError("Ese folio no existe.")
        liga_de_incidencia(gasto.sucursal_id, folio.sucursal_id)
        gasto.incidencia_id = folio.id
        gasto.incidencia_folio = folio.folio
        gasto.incidencia_titulo = folio.titulo[:160]

    def _partidas(
        self, gasto: Gasto, partidas: Sequence[PartidaCrear]
    ) -> tuple[list[GastoPartida], Decimal]:
        """Cada partida con su importe calculado; el total del gasto es su suma."""
        filas: list[GastoPartida] = []
        for orden, p in enumerate(partidas, start=1):
            exigir_desglose(p.descripcion)
            importe = importe_partida(p.cantidad, p.precio_unitario)
            filas.append(
                GastoPartida(
                    gasto_id=gasto.id,
                    orden=orden,
                    descripcion=p.descripcion.strip()[:120],
                    articulo=articulo(p.descripcion),
                    cantidad=p.cantidad,
                    unidad=p.unidad.strip().lower()[:12],
                    precio_unitario=p.precio_unitario,
                    importe=importe,
                    categoria=(p.categoria or CategoriaGasto(gasto.categoria)).value,
                )
            )
        total = sum((f.importe for f in filas), Decimal("0.00"))
        if total <= 0:
            raise ValidationError("El gasto tiene que sumar más de $0.")
        return filas, total

    async def leer(self, gastos: list[Gasto]) -> list[GastoRead]:
        ids = [g.id for g in gastos]
        archivos = await self.repo.archivos(ids)
        partidas = await self.repo.partidas(ids)
        return [await self._read(g, archivos.get(g.id, []), partidas.get(g.id, [])) for g in gastos]

    async def _read(
        self, g: Gasto, archivos: list[GastoArchivo], partidas: list[GastoPartida]
    ) -> GastoRead:
        return GastoRead(
            id=g.id,
            folio=g.folio,
            sucursal_id=g.sucursal_id,
            sucursal_clave=g.sucursal_clave,
            sucursal_nombre=g.sucursal_nombre,
            fecha=g.fecha,
            categoria=CategoriaGasto(g.categoria),
            concepto=g.concepto,
            proveedor=g.proveedor,
            rfc_proveedor=g.rfc_proveedor,
            forma_pago=FormaPago(g.forma_pago),
            tipo_operacion=TipoOperacion(g.tipo_operacion),
            banco=g.banco,
            referencia=g.referencia,
            importe=g.importe,
            nota=g.nota,
            incidencia_id=g.incidencia_id,
            incidencia_folio=g.incidencia_folio,
            incidencia_titulo=g.incidencia_titulo,
            capturo_nombre=g.capturo_nombre,
            capturo_rol=Rol(g.capturo_rol),
            estado=g.estado,
            exportado_en=g.exportado_en,
            creado_en=g.created_at,
            partidas=[PartidaRead.model_validate(p, from_attributes=True) for p in partidas],
            archivos=[
                ArchivoRead(
                    id=a.id,
                    tipo=TipoArchivo(a.tipo),
                    nombre=a.nombre,
                    url=await self.comprobantes.liga(a.archivo),
                    uuid_cfdi=a.uuid_cfdi,
                )
                for a in archivos
            ],
        )

    async def listar(
        self,
        actor: Actor,
        *,
        sucursal_id: int | None,
        desde: date | None,
        hasta: date | None,
        incidencia_id: int | None,
        sin_incidencia: bool,
        categoria: str | None,
        buscar: str | None,
        incluir_anulados: bool,
    ) -> list[GastoRead]:
        if desde and hasta:
            rango(desde, hasta)
        filas = await self.repo.gastos(
            sucursal_id=sucursal_visible(actor, sucursal_id),
            desde=desde,
            hasta=hasta,
            incidencia_id=incidencia_id,
            sin_incidencia=sin_incidencia,
            categoria=categoria,
            texto=buscar,
            incluir_anulados=incluir_anulados,
        )
        return await self.leer(filas)

    async def detalle(self, actor: Actor, gasto_id: int) -> GastoRead:
        g = await self.repo.gasto(gasto_id)
        exigir_gasto_de(actor, g.sucursal_id)
        return (await self.leer([g]))[0]

    async def crear(self, actor: Actor, payload: GastoCrear) -> GastoRead:
        sucursal = self._sucursal(sucursal_para(actor, payload.sucursal_id))
        no_en_el_futuro(payload.fecha, hoy())
        # Antes de guardar nada: un gasto sin desglose no debe gastar un folio.
        for partida in payload.partidas:
            exigir_desglose(partida.descripcion)
        g = Gasto(
            sucursal_id=sucursal.id,
            sucursal_clave=sucursal.clave,
            sucursal_nombre=sucursal.nombre,
            fecha=payload.fecha,
            categoria=payload.categoria.value,
            concepto=payload.concepto.strip(),
            proveedor=payload.proveedor.strip(),
            rfc_proveedor=normalizar_rfc(payload.rfc_proveedor),
            forma_pago=payload.forma_pago.value,
            tipo_operacion=payload.tipo_operacion.value,
            banco=(payload.banco or "").strip() or None,
            referencia=(payload.referencia or "").strip() or None,
            importe=Decimal("0.00"),
            nota=(payload.nota or "").strip() or None,
            capturo_id=actor.user_id,
            capturo_nombre=actor.nombre,
            capturo_rol=actor.rol.value,
            estado="registrado",
        )
        await self._ligar(g, payload.incidencia_id)
        await self.repo.agregar(g)
        g.folio = f"GTO-{sucursal.clave}-{g.id:06d}"
        filas, g.importe = self._partidas(g, payload.partidas)
        await self.repo.reemplazar_partidas(g.id, filas)
        return (await self.leer([g]))[0]

    async def actualizar(self, actor: Actor, gasto_id: int, payload: GastoActualizar) -> GastoRead:
        g = await self.repo.gasto(gasto_id)
        exigir_gasto_de(actor, g.sucursal_id)
        exigir_editable(g.estado)
        cambios = payload.model_dump(exclude_unset=True)
        if "incidencia_id" in cambios:
            await self._ligar(g, cambios.pop("incidencia_id"))
        if "fecha" in cambios and cambios["fecha"] is not None:
            no_en_el_futuro(cambios["fecha"], hoy())
        if "rfc_proveedor" in cambios:
            cambios["rfc_proveedor"] = normalizar_rfc(cambios["rfc_proveedor"])
        cambios.pop("partidas", None)
        for campo, valor in cambios.items():
            if valor is None and campo in (
                "fecha",
                "categoria",
                "concepto",
                "proveedor",
                "forma_pago",
                "tipo_operacion",
            ):
                continue
            if hasattr(valor, "value"):
                valor = valor.value
            if isinstance(valor, str):
                valor = valor.strip() or None
            setattr(g, campo, valor)
        if payload.partidas is not None:
            filas, g.importe = self._partidas(g, payload.partidas)
            await self.repo.reemplazar_partidas(g.id, filas)
        await self.repo.session.flush()
        return (await self.leer([g]))[0]

    async def anular(self, actor: Actor, gasto_id: int) -> GastoRead:
        g = await self.repo.gasto(gasto_id)
        exigir_gasto_de(actor, g.sucursal_id)
        exigir_editable(g.estado)
        g.estado = "anulado"
        await self.repo.session.flush()
        return (await self.leer([g]))[0]

    async def subir(
        self, actor: Actor, gasto_id: int, datos: bytes, nombre: str, contenido: str | None
    ) -> GastoRead:
        g = await self.repo.gasto(gasto_id)
        exigir_gasto_de(actor, g.sucursal_id)
        exigir_editable(g.estado)
        tipo, llave = await self.comprobantes.guardar(datos, nombre, contenido)
        await self.repo.agregar(
            GastoArchivo(
                gasto_id=g.id,
                tipo=tipo.value,
                archivo=llave,
                nombre=(nombre or f"comprobante.{tipo.value}")[:160],
                uuid_cfdi=uuid_de_cfdi(datos) if tipo is TipoArchivo.XML else None,
            )
        )
        return (await self.leer([g]))[0]

    async def quitar_archivo(self, actor: Actor, gasto_id: int, archivo_id: int) -> GastoRead:
        g = await self.repo.gasto(gasto_id)
        exigir_gasto_de(actor, g.sucursal_id)
        exigir_editable(g.estado)
        await self.repo.borrar(await self.repo.archivo(gasto_id, archivo_id))
        return (await self.leer([g]))[0]

    # -- E-Cont ---------------------------------------------------------------------

    async def _para_exportar(self, actor: Actor, pedido: ExportarEcont) -> list[Gasto]:
        exigir_finanzas(actor)
        if not pedido.ids and not (pedido.desde and pedido.hasta):
            raise ValidationError("Elige los gastos o un periodo para exportar.")
        if pedido.desde and pedido.hasta:
            rango(pedido.desde, pedido.hasta)
        filas = await self.repo.gastos(
            ids=pedido.ids or None,
            sucursal_id=sucursal_visible(actor, pedido.sucursal_id),
            desde=pedido.desde,
            hasta=pedido.hasta,
            solo_pendientes=pedido.solo_pendientes,
            limite=5000,
        )
        if not filas:
            raise ValidationError("No hay gastos que exportar con esos filtros.")
        return filas

    async def exportar_excel(self, actor: Actor, pedido: ExportarEcont) -> tuple[bytes, int]:
        filas = await self._para_exportar(actor, pedido)
        partidas = await self.repo.partidas([g.id for g in filas])
        contenido = econt.excel(
            [
                econt.fila_de_gasto(
                    folio=g.folio,
                    forma_pago=g.forma_pago,
                    banco=g.banco,
                    fecha=g.fecha,
                    referencia=g.referencia,
                    importe=g.importe,
                    proveedor=g.proveedor,
                    tipo_operacion=g.tipo_operacion,
                    rfc_proveedor=g.rfc_proveedor,
                    categoria=g.categoria,
                    concepto=g.concepto,
                    sucursal_nombre=g.sucursal_nombre,
                    incidencia_folio=g.incidencia_folio,
                    nota=g.nota,
                    partidas=[
                        (p.descripcion, p.cantidad, p.unidad, p.importe)
                        for p in partidas.get(g.id, [])
                    ],
                )
                for g in sorted(filas, key=lambda x: (x.fecha, x.id))
            ]
        )
        momento = ahora()
        for g in filas:
            g.exportado_en = momento
        await self.repo.session.flush()
        return contenido, len(filas)

    async def exportar_xml(self, actor: Actor, pedido: ExportarEcont) -> tuple[bytes, int]:
        filas = await self._para_exportar(actor, pedido)
        archivos = await self.repo.archivos([g.id for g in filas])
        xmls: list[tuple[str, bytes]] = []
        for g in filas:
            for a in archivos.get(g.id, []):
                if a.tipo != TipoArchivo.XML.value:
                    continue
                datos = await self.comprobantes.leer(a.archivo)
                if datos:
                    xmls.append((a.uuid_cfdi or f"{g.folio}-{a.id}", datos))
        if not xmls:
            raise ValidationError("Ninguno de esos gastos tiene el XML de la factura.")
        return econt.zip_xml(xmls), len(xmls)

    # -- auditoría ----------------------------------------------------------------

    async def analisis(
        self, actor: Actor, *, desde: date, hasta: date, sucursal_id: int | None
    ) -> AnalisisGastos:
        """Quién gasta, en qué y a cuánto sale cada artículo, para la contadora."""
        exigir_finanzas(actor)
        rango(desde, hasta)
        filas = await self.repo.partidas_del_periodo(
            desde=desde, hasta=hasta, sucursal_id=sucursal_visible(actor, sucursal_id)
        )
        gastos: dict[int, Gasto] = {g.id: g for g, _ in filas}
        personas: dict[tuple[str, str], _Persona] = {}
        categorias: dict[str, _Categoria] = {}
        articulos: dict[tuple[str, str], _Articulo] = {}
        for g, p in filas:
            per = personas.setdefault(
                (g.capturo_id, g.sucursal_nombre),
                _Persona(g.capturo_nombre, Rol(g.capturo_rol), g.sucursal_nombre),
            )
            per.gastos.add(g.id)
            per.total += p.importe
            per.por_categoria[p.categoria] += p.importe

            cat = categorias.setdefault(p.categoria, _Categoria())
            cat.partidas += 1
            cat.total += p.importe
            cat.por_sucursal[g.sucursal_nombre] += p.importe

            art = articulos.setdefault(
                (p.articulo, p.unidad), _Articulo(p.descripcion, p.unidad, p.categoria)
            )
            art.veces += 1
            art.cantidad += p.cantidad
            art.total += p.importe
            art.precios.append(p.precio_unitario)
            art.sucursales.add(g.sucursal_nombre)

        por_persona = [
            GastoPorPersona(
                capturo_nombre=v.nombre,
                capturo_rol=v.rol,
                sucursal_nombre=v.sucursal,
                gastos=len(v.gastos),
                total=_centavos(v.total),
                categoria_mayor=CategoriaGasto(
                    max(v.por_categoria, key=v.por_categoria.__getitem__)
                )
                if v.por_categoria
                else None,
            )
            for v in personas.values()
        ]
        por_categoria = [
            GastoPorCategoria(
                categoria=CategoriaGasto(c),
                partidas=v.partidas,
                total=_centavos(v.total),
                por_sucursal={s: _centavos(t) for s, t in v.por_sucursal.items()},
            )
            for c, v in categorias.items()
        ]
        por_articulo = [
            GastoPorArticulo(
                articulo=v.nombre,
                unidad=v.unidad,
                categoria=CategoriaGasto(v.categoria),
                veces=v.veces,
                cantidad=v.cantidad,
                total=_centavos(v.total),
                precio_promedio=_centavos(v.total / v.cantidad) if v.cantidad else _CERO,
                precio_minimo=_centavos(min(v.precios)),
                precio_maximo=_centavos(max(v.precios)),
                sucursales=sorted(v.sucursales),
            )
            for v in articulos.values()
        ]
        return AnalisisGastos(
            desde=desde,
            hasta=hasta,
            total=_centavos(sum((g.importe for g in gastos.values()), _CERO)),
            gastos=len(gastos),
            por_persona=sorted(por_persona, key=lambda x: x.total, reverse=True),
            por_categoria=sorted(por_categoria, key=lambda x: x.total, reverse=True),
            por_articulo=sorted(por_articulo, key=lambda x: x.total, reverse=True)[:300],
        )


_CERO = Decimal("0.00")


def _centavos(x: Decimal) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"))


@dataclass
class _Persona:
    nombre: str
    rol: Rol
    sucursal: str
    gastos: set[int] = field(default_factory=set)
    total: Decimal = _CERO
    por_categoria: defaultdict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))


@dataclass
class _Categoria:
    partidas: int = 0
    total: Decimal = _CERO
    por_sucursal: defaultdict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))


@dataclass
class _Articulo:
    nombre: str
    unidad: str
    categoria: str
    veces: int = 0
    cantidad: Decimal = Decimal(0)
    total: Decimal = _CERO
    precios: list[Decimal] = field(default_factory=list)
    sucursales: set[str] = field(default_factory=set)
