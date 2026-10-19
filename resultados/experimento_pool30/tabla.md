## Línea base en reposo (app + BD + APM corriendo, sin carga)

| CPU app | CPU BD | CPU APM | Memoria app | Memoria BD | Sesiones en PostgreSQL |
|---|---|---|---|---|---|
| 0.3 % | 0.5 % | 1.7 % | 28 MiB | 91 MiB | 0 |

## Tabla de resultados por escalón

| Esc. | Usuarios | Pet./s | p50 (ms) | p95 (ms) | p99 (ms) | Error % | CPU app | CPU BD | Memoria app | Conex. BD (activas / pool) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 900 | 893.0 | 2.2 | 14.0 | 28.4 | 0.00 | 83 % | 61 % | 61 MiB | 30 (máx 31) / 29.9 de 30, en espera 0.0 (máx 0) |
| 2 | 1200 | 895.2 | 272.2 | 497.2 | 724.4 | 0.01 | 99 % | 71 % | 75 MiB | 30 (máx 31) / 30.0 de 30, en espera 269.7 (máx 409) |

CPU expresada en % de un núcleo (límite de la app y de la BD: 100 % = 1 núcleo). Conex. BD: sesiones en `pg_stat_activity` (máximo configurado 100) / conexiones abiertas del pool de la app (tamaño máximo) y peticiones esperando una conexión libre.

## Evaluación de los criterios declarados

| Esc. | Usuarios | Error ≤ 1 % | p95 ≤ 500 ms | Throughput ≥ 90 % de lo esperado | ¿Cumple? |
|---|---|---|---|---|---|
| 1 | 900 | ✔ 0.00 % | ✔ 14 ms | ✔ — | **Sí** |
| 2 | 1200 | ✔ 0.01 % | ✔ 497 ms | ✘ 75 % | **No** |

**Punto de saturación:** escalón 1 — 900 usuarios concurrentes, 893.0 peticiones/s.

## Recursos auxiliares (para descartar cuellos de botella ajenos al sistema)

| Esc. | CPU k6 (prom / máx) | CPU APM | Memoria BD | k6 pet. | k6 error % | k6 p95 (ms) |
|---|---|---|---|---|---|---|
| 1 | 34 % / 76 % | 35 % | 152 MiB | 159768 | 0.00 | 35.8 |
| 2 | 40 % / 82 % | 61 % | 159 MiB | 161495 | 0.01 | 545.2 |

## Latencia y errores por operación (APM)

| Esc. | Operación | Pet./s | p50 | p95 | p99 | Error % |
|---|---|---|---|---|---|---|
| 1 | listar | 444.0 | 2.5 | 14.4 | 29.0 | 0.00 |
| 1 | consultar | 178.4 | 1.3 | 11.8 | 25.7 | 0.00 |
| 1 | crear | 180.8 | 2.1 | 14.3 | 28.7 | 0.00 |
| 1 | actualizar | 89.8 | 2.2 | 14.0 | 28.1 | 0.00 |
| 2 | listar | 447.0 | 272.0 | 496.6 | 724.5 | 0.00 |
| 2 | consultar | 180.0 | 271.7 | 499.0 | 726.2 | 0.00 |
| 2 | crear | 179.4 | 273.4 | 496.4 | 721.3 | 0.00 |
| 2 | actualizar | 88.9 | 271.8 | 498.0 | 725.8 | 0.00 |

## Desglose del tiempo de una petición según las trazas (Tempo)

| Esc. | Trazas | Duración media (ms) | Aplicación | Espera de conexión del pool | Consulta a la BD |
|---|---|---|---|---|---|
| 1 | 150 | 3.6 | 10 % (0.4 ms) | 2 % (0.1 ms) | 88 % (3.1 ms) |
| 2 | 150 | 270.1 | 0 % (0.7 ms) | 87 % (236.2 ms) | 12 % (33.2 ms) |
