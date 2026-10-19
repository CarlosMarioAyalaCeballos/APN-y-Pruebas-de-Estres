# Laboratorio 4 — Monitoreo con APM y prueba de estrés sobre el CRUD

CRUD de productos (Node.js + Express + PostgreSQL) instrumentado con OpenTelemetry, monitoreado
con **Grafana + Tempo + Prometheus** (imagen `grafana/otel-lgtm`) y sometido a una prueba de
estrés con **k6**. Los cuatro componentes corren en contenedores Docker; en el equipo solo se
necesita Docker (y, opcionalmente, Postman y el navegador).

```
                  ┌────────────── red de Docker: lab04-apm_default ───────────────┐
   navegador ───► │ apm  (Grafana :3001, Tempo, Prometheus :9090, colector OTLP)  │
                  │   ▲ trazas y métricas OTLP/HTTP :4318                         │
   Postman  ────► │ app  (Express :8080→3000, pool pg = 10) ──► db (PostgreSQL 16)│
                  │   ▲                                         max_connections=100│
                  │ k6   (escenario k6/escenario.js)                               │
                  └────────────────────────────────────────────────────────────────┘
```

## Estructura

| Ruta | Contenido |
|---|---|
| `app/` | Código de la aplicación (`src/server.js`), instrumentación (`src/tracing.js`) y `Dockerfile` |
| `db/init.sql` | Esquema y 10 000 productos semilla |
| `apm/` | Aprovisionamiento del panel de Grafana “Lab 4 - CRUD productos (APM)” |
| `k6/escenario.js` | Escenario de carga versionado (mezcla, datos variables, escalones) |
| `scripts/medir.ps1` | Ejecuta la prueba y muestrea `docker stats` y conexiones de PostgreSQL |
| `analisis/` | Contenedor que construye la tabla, evalúa los criterios y dibuja las gráficas |
| `docs/` | Criterios de saturación, ficha del equipo, informe y declaración de uso de IA |
| `resultados/` | Datos crudos y procesados de cada corrida |
| `postman/` | Colección para probar el CRUD a mano |

## Instructivo: levantar todo desde cero (equipo con solo Docker)

1. Clonar o copiar esta carpeta y abrir una terminal en ella.
2. **Un único comando** levanta aplicación, base de datos y APM:

   ```bash
   docker compose up -d --build
   ```

   La primera vez descarga las imágenes y compila la app (2–5 min). Compose espera a que la BD
   y el APM estén sanos antes de arrancar la app.
3. Verificar:
   - API: <http://localhost:8080/health> → `{"estado":"ok"}`
   - APM: <http://localhost:3001> (acceso anónimo; usuario `admin` / `admin` si lo pide) →
     *Dashboards → Laboratorio 4 → Lab 4 - CRUD productos (APM)*.
   - Trazas: *Explore → Tempo → Search*, servicio `crud-productos`; al abrir una traza se ven los
     spans de Express y el span `pg.query` con el tiempo de la consulta a PostgreSQL.

> Si el puerto 3001, 8080, 4318 o 9090 ya está ocupado, cambie el lado izquierdo del mapeo en
> `docker-compose.yml`.

## Endpoints del CRUD

| Operación | Método y ruta | Cuerpo |
|---|---|---|
| Listar | `GET /api/productos?limit=20&offset=0` | — |
| Consultar | `GET /api/productos/{id}` | — |
| Crear | `POST /api/productos` | `{"nombre":"Teclado","descripcion":"...","precio":99.5,"stock":3}` |
| Actualizar | `PUT /api/productos/{id}` | igual que crear |
| Eliminar | `DELETE /api/productos/{id}` | — |

## Ejecutar la prueba de estrés

Opción A — con muestreo de recursos (Windows PowerShell, recomendado para el informe):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\medir.ps1 -Etiqueta corrida1
docker compose --profile analisis run --rm --build analisis corrida1
```

El primer comando mide 60 s de línea base en reposo, corre k6 (1 min de calentamiento +
7 escalones de 3 min: 100, 300, 600, 900, 1200, 1500 y 2000 usuarios) y guarda en
`resultados/corrida1/` el resumen de k6 y el muestreo de `docker stats` y `pg_stat_activity`.
El segundo consulta el APM (Prometheus y Tempo) y genera `tabla.md`, `resultados.json` y
`graficas/*.png`.

Opción B — solo la carga (cualquier sistema operativo):

```bash
docker compose --profile carga run --rm k6
# escalones y duración configurables:
ESCALONES=10,25,50 DURACION=1m docker compose --profile carga run --rm k6
```

## Apagar

```bash
docker compose down        # conserva los datos (volumen pgdata)
docker compose down -v     # borra también la base de datos
```
