# Declaración de uso de herramientas de inteligencia artificial

**Herramienta:** Claude Code (modelo Claude Opus 5.5, Anthropic), asistente de programación en
terminal.

**Fecha de uso:** 19 de octubre de 2026.

## Para qué se usó

- Construir el CRUD de productos (Node.js/Express/PostgreSQL), su `Dockerfile` y el
  `docker-compose.yml` del entorno completo.
- Configurar la instrumentación OpenTelemetry y el APM (Grafana + Tempo + Prometheus) y crear el
  panel de Grafana.
- Escribir el escenario de carga de k6, el script de muestreo de recursos y el script de
  análisis que calcula la tabla, evalúa los criterios y dibuja las gráficas.
- Proponer los criterios de saturación (tomando los valores sugeridos por el taller) y redactar
  el instructivo, la ficha del equipo y el borrador del informe y de las respuestas de análisis.

## Lo que no hizo la IA

- Los datos de la tabla y de las gráficas **no fueron inventados**: provienen de la ejecución
  real de la prueba en el equipo descrito en `docs/FICHA_EQUIPO.md`, consultados al APM
  (Prometheus/Tempo) y a `docker stats` por los scripts incluidos. Los datos crudos están en
  `resultados/corrida1/`.

## Responsabilidad de los estudiantes

Los estudiantes revisaron el código y el informe, tomaron las capturas del APM y son
responsables de sustentar cada conclusión.

**Estudiantes:** Carlos Mario Ayala Ceballos y Santiago Gonzales Becerra
