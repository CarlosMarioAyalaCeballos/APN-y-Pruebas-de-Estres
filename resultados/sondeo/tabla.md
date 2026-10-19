## Tabla de resultados por escalón

| Esc. | Usuarios | Pet./s | p50 (ms) | p95 (ms) | p99 (ms) | Error % | CPU app | CPU BD | Memoria app | Conex. BD (activas / pool) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 25 | 24.2 | 1.7 | 3.8 | 4.9 | 0.00 | 4 % | 2 % | 42 MiB | 2 (máx 2) / 2.0 de 10, en espera 0.0 (máx 0) |
| 2 | 100 | 99.8 | 1.4 | 2.6 | 3.6 | 0.00 | 11 % | 4 % | 45 MiB | 4 (máx 4) / 3.6 de 10, en espera 0.0 (máx 0) |
| 3 | 400 | 397.2 | 1.3 | 2.4 | 5.7 | 0.00 | 35 % | 13 % | 52 MiB | 8 (máx 10) / 7.4 de 10, en espera 0.0 (máx 0) |
| 4 | 800 | 797.5 | 1.5 | 4.4 | 8.6 | 0.00 | 68 % | 31 % | 60 MiB | 10 (máx 10) / 10.0 de 10, en espera 0.0 (máx 0) |

CPU expresada en % de un núcleo (límite de la app y de la BD: 100 % = 1 núcleo). Conex. BD: sesiones en `pg_stat_activity` (máximo configurado 100) / conexiones abiertas del pool de la app (tamaño máximo) y peticiones esperando una conexión libre.

## Evaluación de los criterios declarados

| Esc. | Usuarios | Error ≤ 1 % | p95 ≤ 500 ms | Throughput ≥ 90 % de lo esperado | ¿Cumple? |
|---|---|---|---|---|---|
| 1 | 25 | ✔ 0.00 % | ✔ 4 ms | ✔ — | **Sí** |
| 2 | 100 | ✔ 0.00 % | ✔ 3 ms | ✔ 103 % | **Sí** |
| 3 | 400 | ✔ 0.00 % | ✔ 2 ms | ✔ 99 % | **Sí** |
| 4 | 800 | ✔ 0.00 % | ✔ 4 ms | ✔ 100 % | **Sí** |

**Punto de saturación:** escalón 4 — 800 usuarios concurrentes, 797.5 peticiones/s.

## Recursos auxiliares (para descartar cuellos de botella ajenos al sistema)

| Esc. | CPU k6 (prom / máx) | CPU APM | Memoria BD | k6 pet. | k6 error % | k6 p95 (ms) |
|---|---|---|---|---|---|---|
| 1 | 2 % / 2 % | 2 % | 49 MiB | 1124 | 0.00 | 3.9 |
| 2 | 6 % / 6 % | 5 % | 52 MiB | 4530 | 0.00 | 3.1 |
| 3 | 20 % / 38 % | 25 % | 62 MiB | 17999 | 0.00 | 4.8 |
| 4 | 27 % / 28 % | 39 % | 66 MiB | 35901 | 0.00 | 9.5 |

## Latencia y errores por operación (APM)

| Esc. | Operación | Pet./s | p50 | p95 | p99 | Error % |
|---|---|---|---|---|---|---|
| 1 | listar | 12.4 | 1.6 | 2.9 | 4.6 | 0.00 |
| 1 | consultar | 3.9 | 1.4 | 2.0 | 4.2 | 0.00 |
| 1 | crear | 5.5 | 2.4 | 4.5 | 5.0 | 0.00 |
| 1 | actualizar | 2.3 | 2.5 | 4.5 | 4.9 | 0.00 |
| 2 | listar | 51.2 | 1.4 | 2.0 | 2.9 | 0.00 |
| 2 | consultar | 19.7 | 0.7 | 1.9 | 2.0 | 0.00 |
| 2 | crear | 19.5 | 1.7 | 2.9 | 4.5 | 0.00 |
| 2 | actualizar | 9.4 | 1.7 | 3.0 | 5.1 | 0.00 |
| 3 | listar | 195.1 | 1.3 | 2.0 | 4.8 | 0.00 |
| 3 | consultar | 83.5 | 0.6 | 1.9 | 5.2 | 0.00 |
| 3 | crear | 79.8 | 1.6 | 2.9 | 6.1 | 0.00 |
| 3 | actualizar | 38.8 | 1.6 | 3.0 | 8.8 | 0.00 |
| 4 | listar | 401.1 | 1.5 | 4.4 | 8.5 | 0.00 |
| 4 | consultar | 155.3 | 0.8 | 2.9 | 6.7 | 0.00 |
| 4 | crear | 157.3 | 1.7 | 4.8 | 9.2 | 0.00 |
| 4 | actualizar | 83.8 | 1.7 | 4.8 | 10.1 | 0.00 |

## Desglose del tiempo de una petición según las trazas (Tempo)

| Esc. | Trazas | Duración media (ms) | Aplicación | Espera de conexión del pool | Consulta a la BD |
|---|---|---|---|---|---|
| 1 | 150 | 1.9 | 39 % (0.7 ms) | 4 % (0.1 ms) | 58 % (1.1 ms) |
| 2 | 150 | 1.4 | 36 % (0.5 ms) | 2 % (0.0 ms) | 62 % (0.9 ms) |
| 3 | 150 | 1.3 | 35 % (0.5 ms) | 2 % (0.0 ms) | 63 % (0.8 ms) |
| 4 | 150 | 1.5 | 25 % (0.4 ms) | 2 % (0.0 ms) | 73 % (1.1 ms) |
