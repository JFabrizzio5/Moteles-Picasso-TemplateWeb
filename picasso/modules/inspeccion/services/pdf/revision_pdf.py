"""Reporte por inspección: sucursal, cuarto, puesto, responsable, fecha, cada
punto con su resultado, observaciones, folios y fotos."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from reportlab.platypus import Flowable, KeepTogether, Spacer

from ...models import RevisionDetalle
from .base import (
    ANCHO_UTIL,
    CELDA,
    CELDA_NEGRITA,
    CHICO,
    COLOR_RESULTADO,
    CORAL_TEXTO,
    ROLES,
    FotoPdf,
    caja,
    chip_resultado,
    documento,
    encabezado,
    etiqueta,
    fecha_hora,
    galeria,
    p,
    seccion,
    t,
    tabla,
    tarjetas,
)


def construir_revision(
    rev: RevisionDetalle,
    fotos: Mapping[str, Sequence[FotoPdf]],
    generado: datetime,
) -> bytes:
    """`fotos` va por código de punto (G04 → sus fotos)."""

    def contenido() -> list[Flowable]:
        puesto = ROLES.get(rev.rol, rev.rol)
        estado = (
            f"terminada {fecha_hora(rev.completada_en)}"
            if rev.estado == "completa"
            else "en curso: aún no se termina"
        )
        historia: list[Flowable] = encabezado(
            "Reporte por inspección",
            f"{rev.sucursal_nombre} · Hab. {rev.habitacion_numero}",
            f"{t(puesto)} · {t(rev.responsable_nombre)} · "
            f"iniciada {fecha_hora(rev.iniciada_en)} · {estado}",
        )
        sin_revisar = rev.total - rev.revisados
        historia.append(
            tarjetas(
                [
                    (str(rev.bien), "Bien", COLOR_RESULTADO["bien"]),
                    (str(rev.fallas), "Falla", COLOR_RESULTADO["falla"]),
                    (str(rev.no_aplica), "No aplica", COLOR_RESULTADO["no_aplica"]),
                    (str(sin_revisar), "Sin revisar", COLOR_RESULTADO["sin_revisar"]),
                ]
            )
        )
        historia.append(Spacer(1, 10))
        if rev.renta is not None:
            decision = "Puede rentarse" if rev.renta.puede_rentarse else "No puede rentarse"
            historia.append(
                caja(
                    [
                        etiqueta("Decisión vigente de renta"),
                        p(f"<b>{decision}</b> · {t(rev.renta.motivo)}"),
                        p(
                            f"{t(rev.renta.gerente_nombre)} · {fecha_hora(rev.renta.decidida_en)}",
                            CHICO,
                        ),
                    ]
                )
            )

        secciones: dict[str, list[list[object]]] = {}
        for punto in rev.puntos:
            detalle = [f"<b>{t(punto.titulo)}</b><br/>{t(punto.texto)}"]
            if punto.observacion:
                detalle.append(
                    f'<font color="{CORAL_TEXTO.hexval()}">Observación:</font> '
                    f"{t(punto.observacion)}"
                )
            if punto.en_bloque:
                detalle.append("<i>Bien en bloque: marcado con «Lo demás está bien».</i>")
            if punto.motivo_no_aplica:
                detalle.append(f"<i>Motivo: {t(punto.motivo_no_aplica)}</i>")
            folio = p(f"<b>{t(punto.folio)}</b>", CELDA_NEGRITA) if punto.folio else p("—", CELDA)
            secciones.setdefault(punto.seccion, []).append(
                [
                    p(f"<b>{t(punto.codigo)}</b>", CELDA),
                    p("<br/>".join(detalle), CELDA),
                    chip_resultado(punto.resultado),
                    folio,
                ]
            )
        for nombre, filas in secciones.items():
            historia.append(seccion(nombre))
            historia.append(
                tabla(
                    [["Código", "Punto", "Resultado", "Folio"], *filas],
                    [54, ANCHO_UTIL - 54 - 74 - 92, 74, 92],
                )
            )

        con_fotos = [x for x in rev.puntos if fotos.get(x.codigo)]
        if con_fotos:
            titulo: list[Flowable] = [seccion("Evidencias")]
            for punto in con_fotos:
                historia.append(
                    KeepTogether(
                        [
                            *titulo,
                            etiqueta(f"{punto.codigo} · {punto.titulo}"),
                            Spacer(1, 4),
                            galeria(fotos[punto.codigo]),
                        ]
                    )
                )
                titulo = []
        return historia

    return documento(
        f"Revisión · {rev.sucursal_clave} {rev.habitacion_numero}",
        generado,
        contenido,
        asunto="Reporte por inspección",
    )
