# sucursal

Dueño de las sucursales, sus habitaciones (con lo que tienen: jacuzzi, alberca,
sauna, terraza) y del personal: quién es cada cuenta, qué puesto tiene y en qué
sucursal trabaja. Las cuentas y contraseñas las guarda el plugin `accounts`;
aquí solo el nombre, el puesto y la sucursal.

Dos reglas de conteo viven aquí como interruptores por sucursal, porque la
dirección no las ha confirmado: `frecuencia_gerente_dias` (1 = diaria, 2 = cada
dos días) y `ama_exigible` (`por_limpieza` o `diaria`). Ver `enums.py`.

Cada habitación guarda también su `tipo` (Suite, Jacuzzi, Jacuzzi y sauna, Pent
house) y su `seccion` (motel u hotel), como los dicen las tarifas de Kairos.
`public.sincronizar_habitaciones` da de alta los cuartos que faltan y corrige
tipo, sección, jacuzzi y sauna de los que ya existen; nunca borra ni da de baja
(un cuarto sin rentas puede estar en obra) y no toca alberca, terraza ni equipo.
Lo usa `finanzas` (tarea `finanzas.importar_cuartos`, script `kairos_cuartos.py`).
