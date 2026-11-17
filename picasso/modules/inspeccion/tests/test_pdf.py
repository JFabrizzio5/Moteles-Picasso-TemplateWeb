"""Los cuatro reportes PDF se arman con datos armados a mano, sin base."""

from __future__ import annotations

import io
from datetime import UTC, date, datetime

from PIL import Image
from reportlab.platypus import Image as ImagenPdf

from modules.inspeccion.enums import EstadoRevision, TipoEvidencia
from modules.inspeccion.models import (
    DecisionRead,
    EventoRead,
    EvidenciaRead,
    FilaSucursal,
    HabitacionExpediente,
    IncidenciaDetalle,
    IncidenciaResumen,
    Indicadores,
    IndicadorSucursal,
    Panel,
    Periodo,
    Reincidencia,
    ResultadoRead,
    RevisionDetalle,
    RevisionResumen,
)
from modules.inspeccion.services.pdf import (
    FotoPdf,
    construir_grupo,
    construir_habitacion,
    construir_incidencia,
    construir_revision,
)
from modules.inspeccion.services.pdf.base import _miniatura
from shared.enums import Rol

AHORA = datetime(2026, 11, 10, 18, 0, tzinfo=UTC)


def _jpeg() -> bytes:
    salida = io.BytesIO()
    Image.new("RGB", (320, 240), (120, 80, 70)).save(salida, "JPEG")
    return salida.getvalue()


def _punto(codigo: str, resultado: str, **extra: object) -> ResultadoRead:
    datos: dict[str, object] = {
        "codigo": codigo,
        "orden": int(codigo[1:]),
        "seccion": "Agua y baño",
        "titulo": "Fugas en baño",
        "texto": "Lavabo, regadera e inodoro sin fugas visibles.",
        "resultado": resultado,
        "observacion": None,
        "motivo_no_aplica": None,
        "automatico": False,
        "incidencia_id": None,
        "revisado_en": AHORA,
    }
    datos.update(extra)
    return ResultadoRead.model_validate(datos)


def _decision(puede: bool) -> DecisionRead:
    return DecisionRead(
        id=1,
        habitacion_id=5,
        habitacion_numero="105",
        sucursal_clave="LER",
        puede_rentarse=puede,
        motivo="Fuga activa & piso mojado <urgente>",
        gerente_nombre="Laura Méndez",
        incidencia_id=245,
        decidida_en=AHORA,
    )


def _resumen_incidencia() -> dict[str, object]:
    return {
        "id": 245,
        "folio": "PIC-LER-000245",
        "sucursal_id": 1,
        "sucursal_clave": "LER",
        "sucursal_nombre": "Picasso Lerma",
        "habitacion_id": 5,
        "habitacion_numero": "105",
        "codigo_punto": "G04",
        "categoria": "Agua y baño",
        "titulo": "Fuga en monomando de regadera",
        "prioridad": "alta",
        "estado": "cerrada",
        "origen_rol": "gerente",
        "reporto_nombre": "Laura Méndez",
        "reportada_en": AHORA,
        "responsable_atencion": "Mantenimiento",
        "cerrada_en": AHORA,
    }


def test_reporte_por_inspeccion() -> None:
    rev = RevisionDetalle(
        id=23,
        sucursal_id=1,
        sucursal_clave="LER",
        sucursal_nombre="Picasso Lerma",
        habitacion_id=5,
        habitacion_numero="105",
        rol=Rol.GERENTE,
        responsable_nombre="Laura Méndez",
        estado=EstadoRevision.COMPLETA,
        iniciada_en=AHORA,
        completada_en=AHORA,
        total=3,
        revisados=2,
        bien=1,
        fallas=1,
        no_aplica=0,
        puntos=[
            _punto("G01", "bien"),
            _punto(
                "G04", "falla", observacion="Fuga al abrir la regadera.", folio="PIC-LER-000245"
            ),
            _punto("G20", "no_aplica", motivo_no_aplica="La habitación no tiene jacuzzi."),
        ],
        renta=_decision(False),
    )
    fotos = {
        "G04": [FotoPdf("Evidencia · G04", "Laura (Gerente)", _jpeg()), FotoPdf("x", "y", None)]
    }
    assert construir_revision(rev, fotos, AHORA).startswith(b"%PDF")


def test_reporte_por_incidencia() -> None:
    inc = IncidenciaDetalle.model_validate(
        {
            **_resumen_incidencia(),
            "descripcion": "Fuga al abrir la regadera.",
            "correccion": "Se sustituyó el sello.",
            "cerrada_por_nombre": "Laura Méndez",
            "origen_revision_id": 23,
            "evidencias": [
                EvidenciaRead(
                    id=1,
                    tipo=TipoEvidencia.PUNTO,
                    url="/x",
                    codigo_punto="G04",
                    subida_por_nombre="Laura",
                    subida_por_rol=Rol.GERENTE,
                    nota=None,
                    creada_en=AHORA,
                )
            ],
            "historial": [
                EventoRead(
                    fecha=AHORA,
                    actor_nombre="Laura Méndez",
                    actor_rol=Rol.GERENTE,
                    accion="registro",
                    detalle="Registró la falla.",
                )
            ],
            "renta_vigente": _decision(True),
            "decisiones": [_decision(True), _decision(False)],
        }
    )
    fotos = [
        ("punto", FotoPdf("Evidencia", "Laura", _jpeg())),
        ("reparacion", FotoPdf("Reparación", "Laura", None)),
    ]
    assert construir_incidencia(inc, fotos, AHORA).startswith(b"%PDF")


def test_reporte_por_habitacion() -> None:
    exp = HabitacionExpediente(
        habitacion_id=5,
        sucursal_id=1,
        sucursal_nombre="Picasso Lerma",
        numero="105",
        amenidades=["jacuzzi"],
        revisiones=[
            RevisionResumen(
                id=23,
                sucursal_id=1,
                sucursal_clave="LER",
                sucursal_nombre="Picasso Lerma",
                habitacion_id=5,
                habitacion_numero="105",
                rol=Rol.AMA_LLAVES,
                responsable_nombre="Rosa Hernández",
                estado=EstadoRevision.EN_CURSO,
                iniciada_en=AHORA,
                completada_en=None,
                total=29,
                revisados=18,
            )
        ],
        pendientes=[_punto("A17", "sin_revisar")],
        incidencias=[IncidenciaResumen.model_validate(_resumen_incidencia())],
        renta=_decision(False),
        decisiones=[_decision(False), _decision(True)],
    )
    assert construir_habitacion(exp, AHORA).startswith(b"%PDF")


def test_reporte_por_sucursal_y_grupo() -> None:
    periodo = Periodo(desde=date(2026, 11, 9), hasta=date(2026, 11, 10))
    fila = FilaSucursal(
        sucursal_id=1,
        clave="LER",
        nombre="Picasso Lerma",
        foto=None,
        habitaciones=12,
        gerente_completas=18,
        gerente_exigibles=20,
        ama_completas=28,
        ama_exigibles=30,
        abiertas=5,
        no_rentar=2,
    )
    panel = Panel(
        corte=AHORA,
        periodo=periodo,
        completas=46,
        exigibles=50,
        abiertas=5,
        bloqueados=2,
        sucursales=[fila, fila.model_copy(update={"sucursal_id": 2, "nombre": "Picasso Toluca"})],
    )
    indicador = IndicadorSucursal(
        sucursal_id=1,
        nombre="Picasso Lerma",
        cumplimiento_gerente=0.9,
        cumplimiento_ama=None,
        bien=90,
        fallas=10,
        no_aplica=4,
        sin_revisar=0,
        conformidad=0.9,
        cerradas=3,
        horas_solucion_promedio=26.5,
        abiertas=5,
        horas_abiertas_max=70.0,
    )
    ind = Indicadores(
        periodo=periodo,
        total=indicador.model_copy(update={"sucursal_id": 0, "nombre": "Grupo Picasso"}),
        sucursales=[indicador],
        reincidencias=[
            Reincidencia(
                sucursal_nombre="Picasso Lerma",
                habitacion_id=5,
                habitacion_numero="105",
                categoria="Agua y baño",
                veces=2,
                folios=["PIC-LER-000245", "PIC-LER-000250"],
            )
        ],
        fallas_frecuentes=[{"codigo": "G04", "titulo": "Fugas en baño", "veces": 3}],
    )
    assert construir_grupo(panel, ind, AHORA).startswith(b"%PDF")


def test_una_foto_real_se_vuelve_imagen_y_no_el_aviso() -> None:
    # El aviso "Foto no disponible" atrapa cualquier error; sin esta prueba un
    # error al armar la miniatura se veía igual que una foto borrada.
    assert isinstance(_miniatura(_jpeg(), 160, 120), ImagenPdf)
