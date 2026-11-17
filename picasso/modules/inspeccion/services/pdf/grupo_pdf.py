"""Reporte por sucursal y grupo: el comparativo del panel y los indicadores
con su definición."""

from __future__ import annotations

from datetime import datetime

from reportlab.platypus import Flowable, Spacer

from ...models import Indicadores, Panel
from .base import (
    ANCHO_UTIL,
    CELDA,
    CHICO,
    COLOR_RESULTADO,
    CORAL_TEXTO,
    TEXTO,
    documento,
    encabezado,
    fecha,
    fecha_hora,
    horas,
    p,
    pct,
    seccion,
    t,
    tabla,
    tarjetas,
)


def construir_grupo(panel: Panel, ind: Indicadores, generado: datetime) -> bytes:
    def contenido() -> list[Flowable]:
        varias = len(panel.sucursales) > 1
        titulo = "Seis sucursales, en una sola vista" if varias else panel.sucursales[0].nombre
        historia: list[Flowable] = encabezado(
            "Reporte por sucursal y grupo",
            titulo,
            f"Periodo {fecha(panel.periodo.desde)} al {fecha(panel.periodo.hasta)} · "
            f"corte {fecha_hora(panel.corte)}, hora de CDMX",
        )
        historia.append(
            tarjetas(
                [
                    (
                        f"{panel.completas} / {panel.exigibles}",
                        "Revisiones completas (gerente + ama)",
                        TEXTO,
                    ),
                    (
                        str(panel.abiertas),
                        "Incidencias abiertas (incluye en atención)",
                        CORAL_TEXTO,
                    ),
                    (str(panel.bloqueados), "Cuartos bloqueados (no puede rentarse)", CORAL_TEXTO),
                ]
            )
        )

        historia.append(seccion("Resumen por sucursal"))
        filas: list[list[object]] = [
            ["Sucursal", "Gerente ¹", "Ama de llaves ¹", "Abiertas ²", "No rentar ³"]
        ]
        for s in panel.sucursales:
            filas.append(
                [
                    s.nombre,
                    f"{s.gerente_completas} / {s.gerente_exigibles}",
                    f"{s.ama_completas} / {s.ama_exigibles}",
                    str(s.abiertas),
                    str(s.no_rentar),
                ]
            )

        def suma(campo: str) -> int:
            return sum(int(getattr(x, campo)) for x in panel.sucursales)

        filas.append(
            [
                "TOTAL",
                f"{suma('gerente_completas')} / {suma('gerente_exigibles')}",
                f"{suma('ama_completas')} / {suma('ama_exigibles')}",
                str(panel.abiertas),
                str(panel.bloqueados),
            ]
        )
        historia.append(tabla(filas, [ANCHO_UTIL - 4 * 92, 92, 92, 92, 92], total=True))
        historia.append(Spacer(1, 4))
        historia.append(
            p(
                "¹ Revisiones completas / exigibles del periodo, por puesto. "
                "Completa no significa sin fallas. "
                "² Folios abiertos, incluidos los que están en atención. "
                "³ Habitaciones con decisión vigente de no rentarse.",
                CHICO,
            )
        )

        historia.append(seccion("Indicadores"))
        historia.append(
            p("Cumplimiento por puesto (gerente y ama), conformidad de puntos y tiempos.", CHICO)
        )
        historia.append(Spacer(1, 6))
        tot = ind.total
        historia.append(
            tarjetas(
                [
                    (
                        pct(tot.cumplimiento_gerente),
                        f"Cumplimiento gerente · ama {pct(tot.cumplimiento_ama)}",
                        TEXTO,
                    ),
                    (
                        pct(tot.conformidad),
                        f"Conformidad · {tot.bien} bien, {tot.fallas} fallas",
                        COLOR_RESULTADO["bien"],
                    ),
                    (
                        horas(tot.horas_solucion_promedio),
                        f"Tiempo de solución · {tot.cerradas} cerrados",
                        TEXTO,
                    ),
                    (str(len(ind.reincidencias)), "Reincidencias en el periodo", CORAL_TEXTO),
                ]
            )
        )
        historia.append(Spacer(1, 8))
        filas_ind: list[list[object]] = [
            [
                "Sucursal",
                "Gerente",
                "Ama",
                "Conform.",
                "Fallas",
                "No aplica",
                "Abiertos",
                "Solución",
            ]
        ]
        for fila in ind.sucursales:
            filas_ind.append(
                [
                    fila.nombre.replace("Picasso ", ""),
                    pct(fila.cumplimiento_gerente),
                    pct(fila.cumplimiento_ama),
                    pct(fila.conformidad),
                    str(fila.fallas),
                    str(fila.no_aplica),
                    str(fila.abiertas),
                    horas(fila.horas_solucion_promedio),
                ]
            )
        ancho = (ANCHO_UTIL - 92) / 7
        historia.append(tabla(filas_ind, [92] + [ancho] * 7))
        historia.append(Spacer(1, 4))
        historia.append(
            p(
                "Cumplimiento: completas / exigibles, por puesto y frecuencia. "
                "Conformidad: Bien / (Bien + Falla); No aplica y Sin revisar van aparte "
                "y nunca cuentan como aprobados. Tiempo de solución: de la apertura al cierre; "
                f"el abierto más antiguo lleva {horas(tot.horas_abiertas_max)}.",
                CHICO,
            )
        )

        historia.append(seccion("Fallas frecuentes"))
        if ind.fallas_frecuentes:
            historia.append(
                tabla(
                    [
                        ["Código", "Punto", "Veces"],
                        *[
                            [str(f["codigo"]), p(t(f["titulo"]), CELDA), str(f["veces"])]
                            for f in ind.fallas_frecuentes
                        ],
                    ],
                    [60, ANCHO_UTIL - 120, 60],
                )
            )
        else:
            historia.append(p("Sin fallas en el periodo."))

        historia.append(seccion("Reincidencias"))
        if ind.reincidencias:
            historia.append(
                tabla(
                    [
                        ["Sucursal", "Hab.", "Categoría", "Veces", "Folios"],
                        *[
                            [
                                r.sucursal_nombre.replace("Picasso ", ""),
                                r.habitacion_numero,
                                p(t(r.categoria), CELDA),
                                str(r.veces),
                                p(t(", ".join(r.folios)), CELDA),
                            ]
                            for r in ind.reincidencias
                        ],
                    ],
                    [80, 40, 120, 44, ANCHO_UTIL - 284],
                )
            )
        else:
            historia.append(p("Ninguna falla se repitió en la misma habitación."))
        return historia

    return documento(
        "Reporte del grupo", generado, contenido, asunto="Reporte por sucursal y grupo"
    )
