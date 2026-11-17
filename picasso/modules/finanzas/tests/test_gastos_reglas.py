"""Reglas de gastos y el archivo para E-Cont, sin base de datos."""

from __future__ import annotations

import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from jfastframework.errors import ForbiddenError, ValidationError

from modules.finanzas.models import Actor
from modules.finanzas.services import econt
from modules.finanzas.services.comun import tipo_de, uuid_de_cfdi
from modules.finanzas.validations import (
    exigir_finanzas,
    liga_de_incidencia,
    normalizar_rfc,
    sucursal_para,
    sucursal_visible,
)
from shared.enums import Rol

GERENTE = Actor("g1", "Laura", Rol.GERENTE, 3)
PROPIETARIO = Actor("p1", "Dueño", Rol.PROPIETARIO, None)
AMA = Actor("a1", "Rosa", Rol.AMA_LLAVES, 3)


def test_la_ama_de_llaves_no_entra_a_finanzas() -> None:
    with pytest.raises(ForbiddenError):
        exigir_finanzas(AMA)


def test_el_gerente_registra_en_su_sucursal() -> None:
    assert sucursal_para(GERENTE, None) == 3
    assert sucursal_para(GERENTE, 3) == 3
    with pytest.raises(ForbiddenError):
        sucursal_para(GERENTE, 4)


def test_quien_ve_todas_tiene_que_elegir_sucursal() -> None:
    with pytest.raises(ValidationError):
        sucursal_para(PROPIETARIO, None)
    assert sucursal_para(PROPIETARIO, 5) == 5


def test_el_gerente_solo_consulta_su_sucursal() -> None:
    assert sucursal_visible(GERENTE, 9) == 3
    assert sucursal_visible(PROPIETARIO, 9) == 9
    assert sucursal_visible(PROPIETARIO, None) is None


def test_un_gasto_solo_se_liga_a_un_folio_de_su_sucursal() -> None:
    liga_de_incidencia(3, 3)
    with pytest.raises(ValidationError):
        liga_de_incidencia(3, 4)


def test_rfc() -> None:
    assert normalizar_rfc(" xaxx-010101-000 ") == "XAXX010101000"
    assert normalizar_rfc("") is None
    with pytest.raises(ValidationError):
        normalizar_rfc("NOESRFC")


def test_tipo_de_comprobante_por_contenido_o_extension() -> None:
    assert tipo_de("ticket.jpg", "image/jpeg")[0].value == "foto"
    assert tipo_de("factura.XML", "application/octet-stream")[0].value == "xml"
    assert tipo_de("factura.pdf", None)[0].value == "pdf"
    with pytest.raises(ValidationError):
        tipo_de("hoja.xlsx", "application/vnd.ms-excel")


def test_uuid_del_timbre() -> None:
    xml = (
        b"<cfdi:Comprobante><cfdi:Complemento><tfd:TimbreFiscalDigital "
        b'UUID="ab12cd34-0000-4000-8000-1234567890ef" /></cfdi:Complemento></cfdi:Comprobante>'
    )
    assert uuid_de_cfdi(xml) == "AB12CD34-0000-4000-8000-1234567890EF"
    assert uuid_de_cfdi(b"<nada/>") is None


def _fila(**cambios: object) -> econt.FilaEcont:
    base: dict[str, object] = dict(
        folio="GTO-VAQ-000007",
        forma_pago="transferencia",
        banco=None,
        fecha=date(2026, 11, 16),
        referencia=None,
        importe=Decimal("1850.50"),
        proveedor="Refacciones del Valle",
        tipo_operacion="gasto",
        rfc_proveedor="XAXX010101000",
        categoria="mantenimiento",
        concepto="Compresor del aire acondicionado",
        sucursal_nombre="Picasso Vaqueritos",
        incidencias=["PIC-VAQ-000003"],
        nota=None,
    )
    base.update(cambios)
    return econt.fila_de_gasto(**base)  # type: ignore[arg-type]


def test_la_fila_usa_los_nombres_de_e_cont() -> None:
    f = _fila()
    assert f.forma_pago == "Transferencia"
    assert f.tipo_operacion == "Gasto"
    # #FACTURA es obligatorio en E-Cont: sin referencia va el folio del gasto.
    assert f.referencia == "GTO-VAQ-000007"
    assert "Incidencia PIC-VAQ-000003" in f.nota and "Mantenimiento" in f.nota
    assert _fila(referencia="A-123").referencia == "A-123"


def test_el_excel_tiene_las_columnas_de_la_plantilla_de_e_cont() -> None:
    contenido = econt.excel([_fila(), _fila(forma_pago="efectivo", importe=Decimal("90"))])
    libro = load_workbook(io.BytesIO(contenido))
    hoja = libro["Movimientos"]
    titulos = [c.value for c in hoja[1]]
    assert titulos == [
        "FORMA DE PAGO",
        "BANCO",
        "FECHA DE PAGO",
        "#FACTURA",
        "TOTAL PAGADO",
        "TIPO DE CAMBIO",
        "BENEFICIARIO",
        "TIPO DE OPERACIÓN",
        "RFC BENEFICIARIO",
        "SUCURSAL ASIGNADA (RFC)",
        "NOTA",
    ]
    fila = [c.value for c in hoja[2]]
    assert fila[0] == "Transferencia"
    assert fila[2].date() == date(2026, 11, 16)
    assert fila[4] == pytest.approx(1850.50)
    assert fila[6] == "Refacciones del Valle"
    assert hoja.cell(row=3, column=1).value == "Efectivo"
    assert "Catálogos" in libro.sheetnames


def test_zip_de_xml_no_pisa_nombres_repetidos() -> None:
    datos = econt.zip_xml([("UUID-1", b"<a/>"), ("UUID-1", b"<b/>"), ("otro.xml", b"<c/>")])
    nombres = zipfile.ZipFile(io.BytesIO(datos)).namelist()
    assert nombres == ["UUID-1.xml", "UUID-1-2.xml", "otro.xml"]


def test_no_acepta_partidas_que_solo_dicen_la_tienda() -> None:
    from modules.finanzas.validations import exigir_desglose

    for generico in ("Verdulería", "varios", " Despensa ", "FRUTAS Y VERDURAS"):
        with pytest.raises(ValidationError, match="Desglosa"):
            exigir_desglose(generico)
    exigir_desglose("Lechuga orejona")
    exigir_desglose("Broca para tornillo 1/4")


def test_importe_y_articulo_de_una_partida() -> None:
    from modules.finanzas.validations import articulo, importe_partida

    assert importe_partida(Decimal("22"), Decimal("4.55")) == Decimal("100.10")
    assert importe_partida(Decimal("1.5"), Decimal("33.333")) == Decimal("50.00")
    assert articulo("  Jitomate  SALADET ") == articulo("jitomate saladet")
    assert articulo("Plátano") == "platano"


def test_la_nota_para_e_cont_lleva_el_desglose() -> None:
    f = _fila(
        partidas=[
            ("Lechuga", Decimal("10.000"), "pza", Decimal("150.00")),
            ("Jitomate", Decimal("2.5"), "kg", Decimal("87.50")),
        ]
    )
    assert "Lechuga 10 pza $150.00" in f.nota
    assert "Jitomate 2.5 kg $87.50" in f.nota


def test_el_reporte_pdf_se_arma() -> None:
    from datetime import datetime

    from modules.finanzas.enums import CategoriaGasto
    from modules.finanzas.models import (
        AnalisisGastos,
        GastoPorArticulo,
        GastoPorCategoria,
        GastoPorPersona,
    )
    from modules.finanzas.services.reporte_pdf import DatosReporte, construir_finanzas

    analisis = AnalisisGastos(
        desde=date(2026, 11, 1),
        hasta=date(2026, 11, 16),
        total=Decimal("700"),
        gastos=1,
        por_persona=[
            GastoPorPersona(
                capturo_nombre="Laura", capturo_rol=Rol.GERENTE, sucursal_nombre="Picasso Lerma",
                gastos=1, total=Decimal("700"), categoria_mayor=CategoriaGasto.FRUTAS_VERDURAS,
            )
        ],
        por_categoria=[
            GastoPorCategoria(
                categoria=CategoriaGasto.FRUTAS_VERDURAS, partidas=2, total=Decimal("700"),
                por_sucursal={"Picasso Lerma": Decimal("700")},
            )
        ],
        por_articulo=[
            GastoPorArticulo(
                articulo="Lechuga", unidad="pza", categoria=CategoriaGasto.FRUTAS_VERDURAS, veces=2,
                cantidad=Decimal("20"), total=Decimal("400"), precio_promedio=Decimal("20"),
                precio_minimo=Decimal("15"), precio_maximo=Decimal("25"), sucursales=["Lerma"],
            )
        ],
    )  # fmt: skip
    datos = construir_finanzas(
        DatosReporte(date(2026, 11, 1), date(2026, 11, 16), "Picasso Lerma", None, analisis, []),
        datetime(2026, 11, 17, 12, 0),
    )
    assert datos.startswith(b"%PDF")
