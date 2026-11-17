# inspeccion

Dueño de las revisiones (checklist de gerente, 25 puntos; de ama de llaves, 29),
los folios de incidencia que abre una Falla, su historial y evidencias, y la
decisión de renta del gerente. También los reportes de propietarios (panel,
indicadores, expediente por habitación), porque se calculan sobre estas tablas.

Reglas que vienen del documento de la dirección y viven en `validations/`:
Sin revisar nunca cuenta como Bien; No aplica pide motivo; Falla pide
observación y abre folio (o se vincula al abierto de la misma falla en esa
habitación); solo el gerente decide la renta y cierra, y para cerrar hace falta
una foto de la reparación tomada por el gerente y la explicación de la
corrección. El historial solo se agrega.

Los checklists están en `models/catalogo_models.py`. Cada revisión copia el
texto de sus puntos, así que cambiar un criterio no reescribe el pasado.
