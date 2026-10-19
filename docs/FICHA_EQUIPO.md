# Ficha del equipo donde se midió

| Elemento | Valor |
|---|---|
| Procesador | Intel Core i7-13700HX (13.ª generación) |
| Núcleos / hilos | 16 núcleos (8 P + 8 E) / 24 hilos |
| Memoria RAM | 40 GB (39,7 GiB) |
| Sistema operativo | Windows 11 Pro for Workstations, compilación 10.0.26300 |
| Docker | Docker Desktop, motor 29.6.1, Docker Compose v5.1.4, backend WSL 2 |
| Recursos de la VM de Docker | 24 CPU, 19,4 GiB de memoria |
| Fecha de la medición | 19 de octubre de 2026 |

## Límites de recursos asignados a los contenedores

| Contenedor | Imagen | CPU | Memoria | Notas |
|---|---|---|---|---|
| `app` | `lab04-crud-app:1.0` (node:20-alpine) | 1,0 | 512 MiB | Pool de PostgreSQL: 10 conexiones, timeout 5 s; muestreo de trazas al 100 % |
| `db` | `postgres:16-alpine` | 1,0 | 1 GiB | `max_connections=100`, `shared_buffers=128MB` |
| `apm` | `grafana/otel-lgtm:0.8.1` | 4,0 | 4 GiB | Grafana, Tempo, Prometheus, Loki y colector OTel |
| `k6` | `grafana/k6:0.54.0` | 4,0 | 2 GiB | Generador de carga |

Otros contenedores en el equipo durante la medición: `open-webui` (en reposo, ~0,2 % de CPU).
