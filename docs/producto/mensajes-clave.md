# Picasso — mensajes clave (producto y marketing)

Fuente común para el documento de producto y el folleto. Todo lo que dice aquí
lo hace la app hoy, salvo donde se indica «propuesta» o «por construir». Sin
precios: los montos se confirman con CometaX Company.

## Mensajes clave

1. **Del papel al celular.** Cada cuarto de las seis sucursales se revisa desde
   el celular con los checklists del documento de Picasso: 25 puntos del gerente
   (G01–G25) y 29 de la ama de llaves (A01–A29), más el equipo propio de cada
   cuarto. Cada revisión queda con nombre, fecha y hora.
2. **Ninguna falla se pierde.** Cada falla abre un folio consecutivo
   (PIC-LER-000001) con foto y queda abierto hasta que el gerente lo cierra con
   la foto de la reparación y lo que se corrigió. El historial solo se agrega:
   nadie borra lo que pasó.
3. **Rápido para el personal.** Se toca solo lo que está mal; lo demás queda
   «Bien» al enviar. Funciona con poca señal: lo marcado se sube solo al
   volver la conexión.
4. **Las seis sucursales en una sola vista.** Los propietarios ven en el Panel
   las revisiones completas contra las que tocaban, los folios abiertos, los
   cuartos que no pueden rentarse y el último chequeo de cada sucursal.
5. **Decisiones con datos, no con suposiciones.** Cumplimiento de revisión,
   conformidad de puntos, tiempo de solución, reincidencias y fallas frecuentes
   por sucursal, más cuatro reportes en PDF (revisión, cuarto, folio y grupo).
6. **La renta se decide con evidencia.** El gerente decide si un cuarto puede
   rentarse, por separado del folio, y cada decisión queda con motivo, fecha y
   nombre.
7. **Hecho a la medida de Picasso y seguro.** Las reglas que el documento no
   define (frecuencia del gerente, cómo contar a la ama, tipo de checklist) son
   interruptores por sucursal. Los permisos se revisan en el servidor, las fotos
   son privadas con ligas que caducan y la plataforma no paga licencias.
8. **Listo para crecer sin reescribir.** La arquitectura crece por escalones
   cuando una medición lo pide, y deja la puerta abierta a apps para los
   huéspedes (por ejemplo, el QR de quejas y sugerencias).

## Fases (las de la documentación técnica, sección «Pendientes»)

| Fase | Nombre | Qué incluye | Tamaño |
|---|---|---|---|
| 1 | Antes de producción | Repositorio git, servidor y dominio con HTTPS, secretos nuevos, app sin modo demo, respaldos programados | S |
| 2 | Piloto en una sucursal | Cuartos, equipo y personal reales; confirmar reglas con la dirección; lista de QA en los teléfonos del personal | M |
| 3 | Las seis sucursales | Alta del resto de sucursales, capacitación por puesto, revisión de indicadores al primer mes | M |
| 4 | Después | Avisos al gerente, fotos en la cola sin señal, recuperación de contraseña por correo y, si hace falta, app de tienda (Capacitor) | M–L |
| Más adelante | Crecer cuando se mida | Escalones de carga (servidor más grande, varias copias, base administrada) y app para huéspedes (QR de quejas) | según medición |

## Indicadores

| Indicador | Definición | ¿Ya en la app? | Meta propuesta |
|---|---|---|---|
| Cumplimiento de revisión | Completas / exigibles, por puesto (gerente y ama) y sucursal | Sí: Panel y Reportes | Gerente ≥ 95 %, ama ≥ 90 % |
| Conformidad de puntos | Bien / (Bien + Falla) | Sí: Reportes | Fijarla con la línea base del piloto y subirla mes con mes |
| Folios abiertos y el más antiguo | Abiertos hoy y horas del más viejo | Sí: Panel, inicio del gerente y Reportes | Ninguno con más de 7 días sin avance |
| Tiempo de solución | Horas promedio de la apertura al cierre del folio | Sí: Reportes | Promedio ≤ 48 h |
| Reincidencia | Misma categoría, mismo cuarto, 2 o más veces en el periodo | Sí: Reportes | A la baja mes con mes |
| Fallas frecuentes | Puntos del checklist (y equipo E##) que más fallan | Sí: Reportes | Sin meta: guía compras y preventivo |
| Cuartos que no pueden rentarse | Decisión vigente del gerente | Sí: Panel | Cada uno con folio en atención el mismo día |
| Tendencia mes contra mes | Comparar un periodo con el anterior | Por construir | — |
| Tiempo de solución por prioridad | Hoy el promedio junta todas las prioridades | Por construir | — |
| Horas de cuarto fuera de renta | Tiempo entre «no puede rentarse» y «puede rentarse» | Por construir | — |
| Uso por persona | Adopción en el piloto | Por construir | — |
| Costo de reparaciones | La app no registra costos | Por construir | — |

Las metas son propuesta de CometaX, no acuerdos: se fijan con la dirección con
la línea base de las dos primeras semanas del piloto.

## Piloto (propuesta)

4 semanas en una sucursal que elige la dirección: semana 0 preparar (fase 1,
datos reales, reglas), 1 capacitar y arrancar (QA en los teléfonos), 2 línea
base, 3 afinar y fijar metas, 4 decidir si pasa a las seis.

## Continuidad

Planes del catálogo de CometaX: Essential («Que todo siga funcionando»),
**Growth** («Que tu sistema mejore cada mes», el recomendado para Picasso
durante el piloto, las seis sucursales y la fase 4) y Enterprise («Tu área de
tecnología, con dirección», si se suma la app para huéspedes). Montos: a
confirmar con CometaX. Cierre sugerido: «Una reunión de 30 minutos con la
dirección para elegir la sucursal piloto, confirmar las tres reglas y acordar
servidor y dominio».

Tamaños: S ajuste acotado · M varias pantallas o un módulo · L producto nuevo.

## Tono

Directo, en español de México, sin tecnicismos para la dirección. Beneficio
primero, detalle después. Sin cifras inventadas: lo que no se ha medido se dice
como «se espera», con su supuesto. Sin testimonios.
