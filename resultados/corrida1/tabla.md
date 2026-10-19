## Línea base en reposo (app + BD + APM corriendo, sin carga)

| CPU app | CPU BD | CPU APM | Memoria app | Memoria BD | Sesiones en PostgreSQL |
|---|---|---|---|---|---|
| 0.1 % | 0.4 % | 1.7 % | 35 MiB | 48 MiB | 0 |

## Tabla de resultados por escalón

| Esc. | Usuarios | Pet./s | p50 (ms) | p95 (ms) | p99 (ms) | Error % | CPU app | CPU BD | Memoria app | Conex. BD (activas / pool) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100 | 100.1 | 1.5 | 2.8 | 3.8 | 0.00 | 11 % | 6 % | 48 MiB | 4 (máx 4) / 3.6 de 10, en espera 0.0 (máx 0) |
| 2 | 300 | 299.5 | 1.5 | 2.9 | 6.2 | 0.00 | 30 % | 17 % | 52 MiB | 7 (máx 10) / 6.6 de 10, en espera 0.0 (máx 0) |
| 3 | 600 | 597.7 | 1.6 | 4.1 | 8.8 | 0.00 | 55 % | 33 % | 58 MiB | 10 (máx 10) / 9.8 de 10, en espera 0.0 (máx 0) |
| 4 | 900 | 894.6 | 1.9 | 12.1 | 27.9 | 0.00 | 78 % | 49 % | 63 MiB | 10 (máx 10) / 10.0 de 10, en espera 0.4 (máx 12) |
| 5 | 1200 | 896.5 | 298.6 | 575.0 | 735.7 | 0.00 | 98 % | 59 % | 76 MiB | 10 (máx 10) / 10.0 de 10, en espera 297.0 (máx 440) |
| 6 | 1500 | 917.8 | 625.0 | 857.6 | 988.9 | 0.00 | 98 % | 61 % | 92 MiB | 10 (máx 10) / 10.0 de 10, en espera 588.5 (máx 755) |
| 7 | 2000 | 865.2 | 1269.1 | 1686.2 | 1937.2 | 0.30 | 99 % | 60 % | 115 MiB | 10 (máx 10) / 10.0 de 10, en espera 1113.6 (máx 1276) |

CPU expresada en % de un núcleo (límite de la app y de la BD: 100 % = 1 núcleo). Conex. BD: sesiones en `pg_stat_activity` (máximo configurado 100) / conexiones abiertas del pool de la app (tamaño máximo) y peticiones esperando una conexión libre.

## Evaluación de los criterios declarados

| Esc. | Usuarios | Error ≤ 1 % | p95 ≤ 500 ms | Throughput ≥ 90 % de lo esperado | ¿Cumple? |
|---|---|---|---|---|---|
| 1 | 100 | ✔ 0.00 % | ✔ 3 ms | ✔ — | **Sí** |
| 2 | 300 | ✔ 0.00 % | ✔ 3 ms | ✔ 100 % | **Sí** |
| 3 | 600 | ✔ 0.00 % | ✔ 4 ms | ✔ 100 % | **Sí** |
| 4 | 900 | ✔ 0.00 % | ✔ 12 ms | ✔ 100 % | **Sí** |
| 5 | 1200 | ✔ 0.00 % | ✘ 575 ms | ✘ 75 % | **No** |
| 6 | 1500 | ✔ 0.00 % | ✘ 858 ms | ✘ 82 % | **No** |
| 7 | 2000 | ✔ 0.30 % | ✘ 1686 ms | ✘ 71 % | **No** |

**Punto de saturación:** escalón 4 — 900 usuarios concurrentes, 894.6 peticiones/s.

## Recursos auxiliares (para descartar cuellos de botella ajenos al sistema)

| Esc. | CPU k6 (prom / máx) | CPU APM | Memoria BD | k6 pet. | k6 error % | k6 p95 (ms) |
|---|---|---|---|---|---|---|
| 1 | 7 % / 42 % | 6 % | 55 MiB | 18042 | 0.00 | 2.9 |
| 2 | 19 % / 76 % | 8 % | 63 MiB | 53998 | 0.00 | 3.4 |
| 3 | 25 % / 81 % | 23 % | 72 MiB | 107766 | 0.00 | 6.8 |
| 4 | 32 % / 88 % | 39 % | 77 MiB | 161084 | 0.00 | 25.7 |
| 5 | 35 % / 42 % | 51 % | 84 MiB | 162158 | 0.00 | 543.6 |
| 6 | 39 % / 118 % | 38 % | 90 MiB | 164879 | 0.00 | 824.6 |
| 7 | 34 % / 39 % | 36 % | 96 MiB | 156556 | 0.30 | 1578.5 |

## Latencia y errores por operación (APM)

| Esc. | Operación | Pet./s | p50 | p95 | p99 | Error % |
|---|---|---|---|---|---|---|
| 1 | listar | 50.2 | 1.6 | 2.8 | 3.8 | 0.00 |
| 1 | consultar | 20.3 | 0.8 | 1.9 | 2.0 | 0.00 |
| 1 | crear | 19.6 | 1.6 | 2.9 | 4.3 | 0.00 |
| 1 | actualizar | 10.0 | 1.7 | 2.9 | 4.2 | 0.00 |
| 2 | listar | 149.8 | 1.6 | 2.9 | 6.4 | 0.00 |
| 2 | consultar | 60.4 | 0.7 | 1.9 | 5.0 | 0.00 |
| 2 | crear | 59.4 | 1.6 | 2.9 | 6.6 | 0.00 |
| 2 | actualizar | 29.9 | 1.6 | 2.9 | 7.1 | 0.00 |
| 3 | listar | 299.8 | 1.7 | 4.3 | 8.8 | 0.00 |
| 3 | consultar | 118.0 | 0.8 | 2.5 | 7.0 | 0.00 |
| 3 | crear | 119.5 | 1.7 | 4.2 | 9.1 | 0.00 |
| 3 | actualizar | 60.3 | 1.7 | 4.5 | 9.7 | 0.00 |
| 4 | listar | 445.3 | 2.0 | 12.4 | 28.1 | 0.00 |
| 4 | consultar | 181.0 | 1.2 | 10.3 | 26.5 | 0.00 |
| 4 | crear | 179.5 | 1.9 | 12.8 | 28.4 | 0.00 |
| 4 | actualizar | 88.7 | 2.0 | 12.1 | 27.6 | 0.00 |
| 5 | listar | 447.6 | 298.8 | 574.8 | 735.1 | 0.00 |
| 5 | consultar | 179.3 | 297.1 | 575.7 | 736.1 | 0.00 |
| 5 | crear | 181.2 | 299.9 | 575.9 | 736.4 | 0.00 |
| 5 | actualizar | 88.5 | 298.3 | 572.1 | 736.4 | 0.00 |
| 6 | listar | 458.5 | 624.6 | 856.5 | 988.5 | 0.00 |
| 6 | consultar | 184.7 | 624.4 | 854.5 | 988.1 | 0.00 |
| 6 | crear | 183.5 | 625.8 | 860.1 | 989.3 | 0.00 |
| 6 | actualizar | 91.1 | 626.0 | 864.3 | 991.4 | 0.00 |
| 7 | listar | 433.4 | 1269.1 | 1685.1 | 1937.0 | 0.00 |
| 7 | consultar | 172.9 | 1268.8 | 1681.8 | 1936.4 | 0.00 |
| 7 | crear | 172.6 | 1269.8 | 1694.4 | 1938.9 | 0.00 |
| 7 | actualizar | 86.4 | 1269.0 | 1683.8 | 1936.8 | 0.00 |

## Desglose del tiempo de una petición según las trazas (Tempo)

| Esc. | Trazas | Duración media (ms) | Aplicación | Espera de conexión del pool | Consulta a la BD |
|---|---|---|---|---|---|
| 1 | 150 | 1.5 | 31 % (0.5 ms) | 2 % (0.0 ms) | 67 % (1.0 ms) |
| 2 | 150 | 1.6 | 32 % (0.5 ms) | 2 % (0.0 ms) | 66 % (1.1 ms) |
| 3 | 150 | 1.9 | 24 % (0.4 ms) | 1 % (0.0 ms) | 75 % (1.4 ms) |
| 4 | 150 | 2.7 | 13 % (0.4 ms) | 16 % (0.4 ms) | 70 % (1.9 ms) |
| 5 | 150 | 307.5 | 0 % (0.8 ms) | 96 % (295.2 ms) | 4 % (11.5 ms) |
| 6 | 150 | 610.5 | 0 % (0.7 ms) | 98 % (597.2 ms) | 2 % (12.6 ms) |
| 7 | 150 | 1255.7 | 0 % (0.9 ms) | 99 % (1244.1 ms) | 1 % (10.7 ms) |
