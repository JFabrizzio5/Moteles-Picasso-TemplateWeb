"""Archivos para E-Cont.

- Excel con las columnas de la plantilla de movimientos de E-Cont
  (Cheques y transferencias → Importar). Los títulos son los mismos de
  ColumnasImportacionCheques.php, así E-Cont reconoce cada columna.
- ZIP con los XML de factura que se subieron a los gastos, para la
  importación de CFDI de E-Cont.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from ..enums import (
    NOMBRE_CATEGORIA,
    NOMBRE_FORMA_PAGO,
    NOMBRE_TIPO_OPERACION,
    CategoriaGasto,
    FormaPago,
    TipoOperacion,
)

#: (título en E-Cont, ancho, formato de Excel).
COLUMNAS: list[tuple[str, int, str]] = [
    ("FORMA DE PAGO", 18, "@"),
    ("BANCO", 16, "@"),
    ("FECHA DE PAGO", 15, "dd/mm/yyyy"),
    ("#FACTURA", 16, "@"),
    ("TOTAL PAGADO", 15, "#,##0.00"),
    ("TIPO DE CAMBIO", 15, "0.0000"),
    ("BENEFICIARIO", 30, "@"),
    ("TIPO DE OPERACIÓN", 24, "@"),
    ("RFC BENEFICIARIO", 17, "@"),
    ("SUCURSAL ASIGNADA (RFC)", 24, "@"),
    ("NOTA", 60, "@"),
]


@dataclass(frozen=True)
class FilaEcont:
    forma_pago: str
    banco: str | None
    fecha: date
    referencia: str
    importe: Decimal
    beneficiario: str
    tipo_operacion: str
    rfc_beneficiario: str | None
    nota: str


def fila_de_gasto(
    *,
    folio: str,
    forma_pago: str,
    banco: str | None,
    fecha: date,
    referencia: str | None,
    importe: Decimal,
    proveedor: str,
    tipo_operacion: str,
    rfc_proveedor: str | None,
    categoria: str,
    concepto: str,
    sucursal_nombre: str,
    incidencias: Sequence[str],
    nota: str | None,
    partidas: Sequence[tuple[str, Decimal, str, Decimal]] = (),
) -> FilaEcont:
    partes = [
        folio,
        sucursal_nombre,
        NOMBRE_CATEGORIA.get(CategoriaGasto(categoria), categoria),
        concepto,
    ]
    if incidencias:
        etiqueta = "Incidencia" if len(incidencias) == 1 else "Incidencias"
        partes.append(f"{etiqueta} {', '.join(incidencias)}")
    if partidas:
        # descripción, cantidad, unidad, importe: el desglose viaja en la nota.
        partes.append("; ".join(f"{d} {c.normalize():f} {u} ${i:,.2f}" for d, c, u, i in partidas))
    if nota:
        partes.append(nota)
    return FilaEcont(
        forma_pago=NOMBRE_FORMA_PAGO.get(FormaPago(forma_pago), forma_pago),
        banco=banco,
        fecha=fecha,
        # #FACTURA es obligatorio en E-Cont: sin referencia va el folio del gasto.
        referencia=referencia or folio,
        importe=importe,
        beneficiario=proveedor,
        tipo_operacion=NOMBRE_TIPO_OPERACION.get(TipoOperacion(tipo_operacion), tipo_operacion),
        rfc_beneficiario=rfc_proveedor,
        nota=" · ".join(partes)[:500],
    )


def excel(filas: Sequence[FilaEcont]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    assert hoja is not None
    hoja.title = "Movimientos"
    negrita = Font(bold=True, color="FFFFFF")
    fondo = PatternFill("solid", fgColor="1E1E1E")
    for i, (titulo, ancho, _) in enumerate(COLUMNAS, start=1):
        celda = hoja.cell(row=1, column=i, value=titulo)
        celda.font = negrita
        celda.fill = fondo
        celda.alignment = Alignment(horizontal="center", vertical="center")
        hoja.column_dimensions[celda.column_letter].width = ancho
    hoja.freeze_panes = "A2"
    for r, f in enumerate(filas, start=2):
        valores = [
            f.forma_pago,
            f.banco or "",
            f.fecha,
            f.referencia,
            float(f.importe),
            None,
            f.beneficiario,
            f.tipo_operacion,
            f.rfc_beneficiario or "",
            "",
            f.nota,
        ]
        for c, (valor, (_, _, formato)) in enumerate(zip(valores, COLUMNAS, strict=True), start=1):
            celda = hoja.cell(row=r, column=c, value=valor)
            celda.number_format = formato
    # Las mismas listas que la plantilla de E-Cont, para quien edite el archivo.
    catalogos = libro.create_sheet("Catálogos")
    formas = list(NOMBRE_FORMA_PAGO.values())
    tipos = list(NOMBRE_TIPO_OPERACION.values())
    catalogos.cell(row=1, column=1, value="FORMA DE PAGO").font = Font(bold=True)
    catalogos.cell(row=1, column=2, value="TIPO DE OPERACIÓN").font = Font(bold=True)
    for i, v in enumerate(formas, start=2):
        catalogos.cell(row=i, column=1, value=v)
    for i, v in enumerate(tipos, start=2):
        catalogos.cell(row=i, column=2, value=v)
    ultima = max(len(filas) + 1, 200)
    lista_formas = DataValidation(type="list", formula1=f"'Catálogos'!$A$2:$A${len(formas) + 1}")
    lista_tipos = DataValidation(type="list", formula1=f"'Catálogos'!$B$2:$B${len(tipos) + 1}")
    hoja.add_data_validation(lista_formas)
    hoja.add_data_validation(lista_tipos)
    lista_formas.add(f"A2:A{ultima}")
    lista_tipos.add(f"H2:H{ultima}")
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def zip_xml(archivos: Sequence[tuple[str, bytes]]) -> bytes:
    """(nombre, bytes) de cada XML; nombres repetidos se numeran."""
    salida = io.BytesIO()
    usados: set[str] = set()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, datos in archivos:
            base = nombre if nombre.lower().endswith(".xml") else f"{nombre}.xml"
            final, n = base, 1
            while final in usados:
                n += 1
                final = base[:-4] + f"-{n}.xml"
            usados.add(final)
            z.writestr(final, datos)
    return salida.getvalue()
