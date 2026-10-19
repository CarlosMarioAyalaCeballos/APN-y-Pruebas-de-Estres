## Línea base en reposo (app + BD + APM corriendo, sin carga)

| CPU app | CPU BD | CPU APM | Memoria app | Memoria BD | Sesiones en PostgreSQL |
|---|---|---|---|---|---|
| 0.1 % | 0.1 % | 1.6 % | 39 MiB | 80 MiB | 0 |

## Tabla de resultados por escalón

| Esc. | Usuarios | Pet./s | p50 (ms) | p95 (ms) | p99 (ms) | Error % | CPU app | CPU BD | Memoria app | Conex. BD (activas / pool) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 900 | 892.3 | 2.1 | 26.7 | 99.5 | 0.00 | 80 % | 65 % | 65 MiB | 10 (máx 10) / 10.0 de 10, en espera 5.9 (máx 73) |
| 2 | 1200 | 923.9 | 270.5 | 489.7 | 686.4 | 0.00 | 98 % | 70 % | 77 MiB | 10 (máx 10) / 10.0 de 10, en espera 240.5 (máx 465) |

CPU expresada en % de un núcleo (límite de la app y de la BD: 100 % = 1 núcleo). Conex. BD: sesiones en `pg_stat_activity` (máximo configurado 100) / conexiones abiertas del pool de la app (tamaño máximo) y peticiones esperando una conexión libre.

## Evaluación de los criterios declarados

| Esc. | Usuarios | Error ≤ 1 % | p95 ≤ 500 ms | Throughput ≥ 90 % de lo esperado | ¿Cumple? |
|---|---|---|---|---|---|
| 1 | 900 | ✔ 0.00 % | ✔ 27 ms | ✔ — | **Sí** |
| 2 | 1200 | ✔ 0.00 % | ✔ 490 ms | ✘ 78 % | **No** |

**Punto de saturación:** escalón 1 — 900 usuarios concurrentes, 892.3 peticiones/s.

## Recursos auxiliares (para descartar cuellos de botella ajenos al sistema)

| Esc. | CPU k6 (prom / máx) | CPU APM | Memoria BD | k6 pet. | k6 error % | k6 p95 (ms) |
|---|---|---|---|---|---|---|
| 1 | 37 % / 75 % | 63 % | 102 MiB | 160564 | 0.00 | 44.3 |
| 2 | 42 % / 93 % | 47 % | 108 MiB | 167893 | 0.00 | 487.9 |

## Latencia y errores por operación (APM)

| Esc. | Operación | Pet./s | p50 | p95 | p99 | Error % |
|---|---|---|---|---|---|---|
| 1 | listar | 446.0 | 2.5 | 27.6 | 100.0 | 0.00 |
| 1 | consultar | 178.7 | 1.2 | 24.3 | 98.2 | 0.00 |
| 1 | crear | 178.4 | 2.0 | 26.6 | 100.7 | 0.00 |
| 1 | actualizar | 89.3 | 2.0 | 26.9 | 98.1 | 0.00 |
| 2 | listar | 460.2 | 270.3 | 489.9 | 687.6 | 0.00 |
| 2 | consultar | 185.3 | 269.9 | 488.7 | 683.1 | 0.00 |
| 2 | crear | 185.5 | 271.8 | 490.2 | 686.5 | 0.00 |
| 2 | actualizar | 92.9 | 270.2 | 489.4 | 686.3 | 0.00 |

## Desglose del tiempo de una petición según las trazas (Tempo)

| Esc. | Trazas | Duración media (ms) | Aplicación | Espera de conexión del pool | Consulta a la BD |
|---|---|---|---|---|---|
| 1 | 150 | 8.3 | 5 % (0.4 ms) | 61 % (5.1 ms) | 34 % (2.8 ms) |
| 2 | 148 | 261.4 | 0 % (0.9 ms) | 96 % (249.8 ms) | 4 % (10.7 ms) |
