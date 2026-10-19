# Declaración de criterios de saturación

**Fecha de declaración:** 19 de octubre de 2026, antes de ejecutar la primera medición.
**Archivo bajo control de versiones:** este archivo no se modifica después de medir.

Un escalón de carga **cumple** si se satisfacen a la vez los tres criterios. El punto de
saturación es el **último escalón que cumple los tres**.

| # | Criterio | Umbral declarado | Fuente del dato |
|---|----------|------------------|-----------------|
| 1 | Tasa de error | **≤ 1 %** de las peticiones del escalón (respuestas 5xx registradas en el APM **más** fallos de red o timeouts de 10 s registrados por k6) | APM (Prometheus) + k6 |
| 2 | Latencia p95 | **≤ 500 ms**, medida del lado del servidor en el APM sobre todas las operaciones del CRUD | APM (Prometheus, histograma `http.server.duration`) |
| 3 | Crecimiento del throughput | El throughput (peticiones/s) del escalón debe ser **≥ 90 % del throughput esperado** por el aumento de usuarios respecto al escalón anterior. Esperado = throughput anterior × (usuarios actuales / usuarios anteriores). Por debajo de eso se considera que el throughput se aplanó. | APM (Prometheus) |

## Condiciones de la medición

- Calentamiento de 1 minuto con 10 usuarios, descartado del análisis.
- Seis escalones de 3 minutos: 10, 25, 50, 100, 200 y 400 usuarios concurrentes (puede
  ajustarse la progresión, **no** los umbrales).
- Los primeros 15 s y los últimos 5 s de cada escalón se excluyen del cálculo para evitar la
  transición entre escalones.
- Cada usuario virtual espera entre 0,5 y 1,5 s (promedio 1 s) entre peticiones.
- Mezcla: 70 % lecturas (50 % listar, 20 % consultar), 20 % creaciones, 10 % actualizaciones.
- **Ajuste de la progresión (19/10/2026, tras una corrida de sondeo de 45 s por escalón que no
  forma parte de los resultados):** con 800 usuarios la app solo usaba ~68 % de su núcleo y
  p95 = 4 ms, de modo que la progresión 10…400 no alcanzaba la saturación. La medición oficial
  usa **siete escalones: 100, 300, 600, 900, 1200, 1500 y 2000 usuarios**, 3 minutos cada uno.
  Los tres umbrales de arriba **no se modificaron**.
- Límites de recursos: app 1 CPU / 512 MiB; PostgreSQL 1 CPU / 1 GiB; APM 4 CPU / 4 GiB;
  k6 4 CPU / 2 GiB. Pool de la app: 10 conexiones; `max_connections` de PostgreSQL: 100.
