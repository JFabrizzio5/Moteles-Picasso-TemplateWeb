# sucursal

Dueño de las sucursales, sus habitaciones (con lo que tienen: jacuzzi, alberca,
sauna, terraza) y del personal: quién es cada cuenta, qué puesto tiene y en qué
sucursal trabaja. Las cuentas y contraseñas las guarda el plugin `accounts`;
aquí solo el nombre, el puesto y la sucursal.

Dos reglas de conteo viven aquí como interruptores por sucursal, porque la
dirección no las ha confirmado: `frecuencia_gerente_dias` (1 = diaria, 2 = cada
dos días) y `ama_exigible` (`por_limpieza` o `diaria`). Ver `enums.py`.
