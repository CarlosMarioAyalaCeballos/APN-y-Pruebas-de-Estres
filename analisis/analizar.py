"""Análisis de una corrida de la prueba de estrés.

Lee   /resultados/<etiqueta>/{ejecucion.json, k6-salida.txt, k6-errores.txt,
                              k6-resumen.json, docker-stats.csv}
Consulta Prometheus (métricas del APM) y Tempo (trazas del APM) en la ventana de cada escalón.
Escribe /resultados/<etiqueta>/{resultados.json, tabla.md, graficas/*.png}

Uso: docker compose --profile analisis run --rm analisis <etiqueta>
"""
import csv
import json
import os
import re
import statistics
import sys
import urllib.parse
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROM = os.environ.get("PROM_URL", "http://apm:9090")
TEMPO = os.environ.get("TEMPO_URL", "http://apm:3200")
JOB = 'job="crud-productos"'
HIST = "http_server_duration_milliseconds"
RECORTE_INICIO, RECORTE_FIN = 15, 5          # segundos excluidos de cada escalón
TRAZAS_POR_ESCALON = int(os.environ.get("TRAZAS_POR_ESCALON", "150"))

# Criterios declarados en docs/CRITERIOS_SATURACION.md (no modificar después de medir).
MAX_ERROR_PCT = 1.0
MAX_P95_MS = 500.0
MIN_EFICIENCIA_THROUGHPUT = 0.90

OPERACIONES = {
    ("GET", "/api/productos"): "listar",
    ("GET", "/api/productos/:id"): "consultar",
    ("POST", "/api/productos"): "crear",
    ("PUT", "/api/productos/:id"): "actualizar",
}


def http_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def prom(query, t):
    url = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": query, "time": t})
    return http_json(url)["data"]["result"]


def prom_escalar(query, t):
    res = prom(query, t)
    if not res:
        return 0.0
    v = float(res[0]["value"][1])
    return 0.0 if v != v else v  # NaN -> 0


def segundos(d):
    m = re.fullmatch(r"(\d+)(s|m)", d.strip())
    return int(m.group(1)) * (60 if m.group(2) == "m" else 1)


def inicio_k6(carpeta, respaldo):
    for nombre in ("k6-salida.txt", "k6-errores.txt"):
        ruta = os.path.join(carpeta, nombre)
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8", errors="ignore") as f:
                m = re.search(r"INICIO_MS=(\d+)", f.read())
                if m:
                    return int(m.group(1)) / 1000
    return respaldo


# ------------------------------------------------------------------ Prometheus
def metricas_apm(ini, fin):
    w = int(fin - ini)
    rng = f"[{w}s]"
    total = prom_escalar(f"sum(increase({HIST}_count{{{JOB}}}{rng}))", fin)
    err5 = prom_escalar(f'sum(increase({HIST}_count{{{JOB},http_status_code=~"5.."}}{rng}))', fin)
    q = {}
    for p in (0.5, 0.95, 0.99):
        q[p] = prom_escalar(
            f"histogram_quantile({p}, sum by (le) (increase({HIST}_bucket{{{JOB}}}{rng})))", fin)
    por_op = {}
    for serie in prom(f"sum by (http_method, http_route) (increase({HIST}_count{{{JOB}}}{rng}))", fin):
        clave = (serie["metric"].get("http_method"), serie["metric"].get("http_route"))
        if clave not in OPERACIONES:
            continue
        op = OPERACIONES[clave]
        sel = f'{JOB},http_method="{clave[0]}",http_route="{clave[1]}"'
        n = float(serie["value"][1])
        e = prom_escalar(f'sum(increase({HIST}_count{{{sel},http_status_code=~"5.."}}{rng}))', fin)
        por_op[op] = {
            "rps": n / w,
            "p50": prom_escalar(f"histogram_quantile(0.5, sum by (le) (increase({HIST}_bucket{{{sel}}}{rng})))", fin),
            "p95": prom_escalar(f"histogram_quantile(0.95, sum by (le) (increase({HIST}_bucket{{{sel}}}{rng})))", fin),
            "p99": prom_escalar(f"histogram_quantile(0.99, sum by (le) (increase({HIST}_bucket{{{sel}}}{rng})))", fin),
            "error_pct": 100 * e / n if n else 0.0,
        }
    pool = {
        "pool_total_prom": prom_escalar(f"avg_over_time(db_pool_total{{{JOB}}}{rng})", fin),
        "pool_max": prom_escalar(f"max_over_time(db_pool_max{{{JOB}}}{rng})", fin),
        "pool_espera_prom": prom_escalar(f"avg_over_time(db_pool_waiting{{{JOB}}}{rng})", fin),
        "pool_espera_max": prom_escalar(f"max_over_time(db_pool_waiting{{{JOB}}}{rng})", fin),
        "pool_libres_prom": prom_escalar(f"avg_over_time(db_pool_idle{{{JOB}}}{rng})", fin),
    }
    return {
        "rps": total / w,
        "peticiones": total,
        "p50": q[0.5], "p95": q[0.95], "p99": q[0.99],
        "error_pct_apm": 100 * err5 / total if total else 0.0,
        "por_operacion": por_op,
        **pool,
    }


# ------------------------------------------------------------------ Tempo
def spans_de(traza):
    for b in traza.get("batches", traza.get("resourceSpans", [])):
        for ss in b.get("scopeSpans", b.get("instrumentationLibrarySpans", [])):
            alcance = (ss.get("scope") or ss.get("instrumentationLibrary") or {}).get("name", "")
            for s in ss.get("spans", []):
                yield alcance, s


def desglose_trazas(ini, fin):
    url = f"{TEMPO}/api/search?" + urllib.parse.urlencode({
        "tags": "service.name=crud-productos", "start": int(ini), "end": int(fin),
        "limit": TRAZAS_POR_ESCALON})
    try:
        ids = [t["traceID"] for t in http_json(url).get("traces", [])]
    except Exception as e:  # noqa: BLE001
        print("  Tempo no respondió:", e)
        return None
    total = consulta = espera = 0.0
    n = 0
    for tid in ids:
        try:
            traza = http_json(f"{TEMPO}/api/traces/{tid}")
        except Exception:  # noqa: BLE001
            continue
        raiz = None
        t_q = t_w = 0.0
        for alcance, s in spans_de(traza):
            dur = (int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1e6
            if not s.get("parentSpanId"):
                raiz = dur
            if "instrumentation-pg" in alcance:
                if s["name"].startswith("pg-pool.connect") or s["name"] == "pg.connect":
                    t_w += dur
                else:
                    t_q += dur
        if raiz and raiz > 0 and (t_q > 0 or t_w > 0):
            total += raiz; consulta += t_q; espera += t_w; n += 1
    if not n:
        return None
    app = max(total - consulta - espera, 0)
    return {
        "trazas": n,
        "dur_media_ms": total / n,
        "pct_bd_consulta": 100 * consulta / total,
        "pct_espera_pool": 100 * espera / total,
        "pct_app": 100 * app / total,
        "ms_bd_consulta": consulta / n,
        "ms_espera_pool": espera / n,
        "ms_app": app / n,
    }


# ------------------------------------------------------------------ docker stats
def leer_stats(ruta):
    filas = []
    if not os.path.exists(ruta):
        return filas
    with open(ruta, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                filas.append({"ts": int(r["ts"]), "c": r["contenedor"], "cpu": float(r["cpu_pct"]),
                              "mem": float(r["mem_mib"]),
                              "con": float(r["conexiones_bd"]) if r["conexiones_bd"] else None})
            except (ValueError, KeyError):
                pass
    return filas


def recursos(filas, ini, fin):
    def sel(patron):
        return [f for f in filas if ini <= f["ts"] <= fin and re.search(patron, f["c"])]

    def prom_(xs, k):
        v = [x[k] for x in xs if x[k] is not None]
        return statistics.mean(v) if v else 0.0

    def max_(xs, k):
        v = [x[k] for x in xs if x[k] is not None]
        return max(v) if v else 0.0

    app, db, apm, k6 = sel(r"-app-"), sel(r"-db-"), sel(r"-apm-1$"), sel(r"k6")
    return {
        "cpu_app": prom_(app, "cpu"), "cpu_app_max": max_(app, "cpu"),
        "cpu_bd": prom_(db, "cpu"), "cpu_bd_max": max_(db, "cpu"),
        "cpu_apm": prom_(apm, "cpu"), "cpu_k6": prom_(k6, "cpu"), "cpu_k6_max": max_(k6, "cpu"),
        "mem_app": prom_(app, "mem"), "mem_bd": prom_(db, "mem"),
        "conex_bd_prom": prom_(db, "con"), "conex_bd_max": max_(db, "con"),
    }


# ------------------------------------------------------------------ k6
def k6_por_escalon(resumen, nombre):
    m = resumen.get("metrics", {}) if resumen else {}
    reqs = m.get(f"http_reqs{{scenario:{nombre}}}", {}).get("values", {})
    fail = m.get(f"http_req_failed{{scenario:{nombre}}}", {}).get("values", {})
    dur = m.get(f"http_req_duration{{scenario:{nombre}}}", {}).get("values", {})
    return {"k6_peticiones": reqs.get("count", 0), "k6_error_pct": 100 * fail.get("rate", 0),
            "k6_p95": dur.get("p(95)", 0), "k6_p99": dur.get("p(99)", 0)}


# ------------------------------------------------------------------ principal
def main():
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "corrida"
    carpeta = os.path.join("/resultados", etiqueta)
    with open(os.path.join(carpeta, "ejecucion.json"), encoding="utf-8-sig") as f:
        eje = json.load(f)
    usuarios = [int(x) for x in str(eje["escalones"]).split(",")]
    dur, cal = segundos(eje["duracion"]), segundos(eje["calentamiento"])
    t0 = inicio_k6(carpeta, eje["inicio"])
    resumen = None
    ruta_res = os.path.join(carpeta, "k6-resumen.json")
    if os.path.exists(ruta_res):
        with open(ruta_res, encoding="utf-8") as f:
            resumen = json.load(f)
    stats = leer_stats(os.path.join(carpeta, "docker-stats.csv"))

    # Línea base: entorno en reposo antes de la carga (el calentamiento no se analiza).
    base = None
    if eje.get("inicio_reposo"):
        base = recursos(stats, eje["inicio_reposo"], eje["inicio"] - 1)
    filas = []
    for i, u in enumerate(usuarios, start=1):
        ini = t0 + cal + (i - 1) * dur + RECORTE_INICIO
        fin = t0 + cal + i * dur - RECORTE_FIN
        print(f"Escalón {i} ({u} usuarios): ventana {int(ini)}-{int(fin)}")
        fila = {"escalon": i, "usuarios": u, "ventana": [ini, fin]}
        fila.update(metricas_apm(ini, fin))
        fila.update(recursos(stats, ini, fin))
        fila.update(k6_por_escalon(resumen, f"esc_{i}_{u}u"))
        fila["trazas"] = desglose_trazas(ini, fin)
        filas.append(fila)

    # Evaluación de criterios
    punto = None
    for idx, f in enumerate(filas):
        f["error_pct"] = max(f["error_pct_apm"], f["k6_error_pct"])
        c1 = f["error_pct"] <= MAX_ERROR_PCT
        c2 = f["p95"] <= MAX_P95_MS
        if idx == 0:
            f["eficiencia_throughput"] = None
            c3 = True
        else:
            ant = filas[idx - 1]
            esperado = ant["rps"] * f["usuarios"] / ant["usuarios"]
            f["eficiencia_throughput"] = f["rps"] / esperado if esperado else 0
            c3 = f["eficiencia_throughput"] >= MIN_EFICIENCIA_THROUGHPUT
        f["cumple"] = {"error": c1, "p95": c2, "throughput": c3}
        f["cumple_todo"] = c1 and c2 and c3
        if f["cumple_todo"] and (punto is None or punto["escalon"] == f["escalon"] - 1):
            punto = f

    with open(os.path.join(carpeta, "resultados.json"), "w", encoding="utf-8") as fo:
        json.dump({"inicio_k6": t0, "linea_base": base, "escalones": filas,
                   "punto_saturacion": punto and punto["escalon"]}, fo, indent=2, ensure_ascii=False)

    escribir_tabla(carpeta, filas, punto, base)
    graficar(carpeta, filas, punto)
    print(open(os.path.join(carpeta, "tabla.md"), encoding="utf-8").read())


def si_no(b):
    return "✔" if b else "✘"


def escribir_tabla(carpeta, filas, punto, base=None):
    L = []
    if base:
        L.append("## Línea base en reposo (app + BD + APM corriendo, sin carga)\n")
        L.append("| CPU app | CPU BD | CPU APM | Memoria app | Memoria BD | Sesiones en PostgreSQL |")
        L.append("|---|---|---|---|---|---|")
        L.append(f"| {base['cpu_app']:.1f} % | {base['cpu_bd']:.1f} % | {base['cpu_apm']:.1f} % | {base['mem_app']:.0f} MiB | "
                 f"{base['mem_bd']:.0f} MiB | {base['conex_bd_prom']:.0f} |\n")
    L.append("## Tabla de resultados por escalón\n")
    L.append("| Esc. | Usuarios | Pet./s | p50 (ms) | p95 (ms) | p99 (ms) | Error % | CPU app | CPU BD | Memoria app | Conex. BD (activas / pool) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for f in filas:
        L.append(f"| {f['escalon']} | {f['usuarios']} | {f['rps']:.1f} | {f['p50']:.1f} | {f['p95']:.1f} | {f['p99']:.1f} | "
                 f"{f['error_pct']:.2f} | {f['cpu_app']:.0f} % | {f['cpu_bd']:.0f} % | {f['mem_app']:.0f} MiB | "
                 f"{f['conex_bd_prom']:.0f} (máx {f['conex_bd_max']:.0f}) / {f['pool_total_prom']:.1f} de {f['pool_max']:.0f}, "
                 f"en espera {f['pool_espera_prom']:.1f} (máx {f['pool_espera_max']:.0f}) |")
    L.append("\nCPU expresada en % de un núcleo (límite de la app y de la BD: 100 % = 1 núcleo). "
             "Conex. BD: sesiones en `pg_stat_activity` (máximo configurado 100) / conexiones abiertas del pool de la app "
             "(tamaño máximo) y peticiones esperando una conexión libre.\n")

    L.append("## Evaluación de los criterios declarados\n")
    L.append("| Esc. | Usuarios | Error ≤ 1 % | p95 ≤ 500 ms | Throughput ≥ 90 % de lo esperado | ¿Cumple? |")
    L.append("|---|---|---|---|---|---|")
    for f in filas:
        ef = "—" if f["eficiencia_throughput"] is None else f"{100 * f['eficiencia_throughput']:.0f} %"
        L.append(f"| {f['escalon']} | {f['usuarios']} | {si_no(f['cumple']['error'])} {f['error_pct']:.2f} % | "
                 f"{si_no(f['cumple']['p95'])} {f['p95']:.0f} ms | {si_no(f['cumple']['throughput'])} {ef} | "
                 f"**{'Sí' if f['cumple_todo'] else 'No'}** |")
    if punto:
        L.append(f"\n**Punto de saturación:** escalón {punto['escalon']} — {punto['usuarios']} usuarios concurrentes, "
                 f"{punto['rps']:.1f} peticiones/s.\n")
    else:
        L.append("\n**Ningún escalón cumple los tres criterios.**\n")

    L.append("## Recursos auxiliares (para descartar cuellos de botella ajenos al sistema)\n")
    L.append("| Esc. | CPU k6 (prom / máx) | CPU APM | Memoria BD | k6 pet. | k6 error % | k6 p95 (ms) |")
    L.append("|---|---|---|---|---|---|---|")
    for f in filas:
        L.append(f"| {f['escalon']} | {f['cpu_k6']:.0f} % / {f['cpu_k6_max']:.0f} % | {f['cpu_apm']:.0f} % | {f['mem_bd']:.0f} MiB | "
                 f"{f['k6_peticiones']:.0f} | {f['k6_error_pct']:.2f} | {f['k6_p95']:.1f} |")

    L.append("\n## Latencia y errores por operación (APM)\n")
    L.append("| Esc. | Operación | Pet./s | p50 | p95 | p99 | Error % |")
    L.append("|---|---|---|---|---|---|---|")
    for f in filas:
        for op in ("listar", "consultar", "crear", "actualizar"):
            o = f["por_operacion"].get(op)
            if o:
                L.append(f"| {f['escalon']} | {op} | {o['rps']:.1f} | {o['p50']:.1f} | {o['p95']:.1f} | {o['p99']:.1f} | {o['error_pct']:.2f} |")

    L.append("\n## Desglose del tiempo de una petición según las trazas (Tempo)\n")
    L.append("| Esc. | Trazas | Duración media (ms) | Aplicación | Espera de conexión del pool | Consulta a la BD |")
    L.append("|---|---|---|---|---|---|")
    for f in filas:
        t = f["trazas"]
        if t:
            L.append(f"| {f['escalon']} | {t['trazas']} | {t['dur_media_ms']:.1f} | {t['pct_app']:.0f} % ({t['ms_app']:.1f} ms) | "
                     f"{t['pct_espera_pool']:.0f} % ({t['ms_espera_pool']:.1f} ms) | {t['pct_bd_consulta']:.0f} % ({t['ms_bd_consulta']:.1f} ms) |")
        else:
            L.append(f"| {f['escalon']} | 0 | — | — | — | — |")
    with open(os.path.join(carpeta, "tabla.md"), "w", encoding="utf-8") as fo:
        fo.write("\n".join(L) + "\n")


def graficar(carpeta, filas, punto):
    d = os.path.join(carpeta, "graficas")
    os.makedirs(d, exist_ok=True)
    u = [f["usuarios"] for f in filas]
    plt.rcParams.update({"figure.figsize": (8, 4.8), "axes.grid": True, "grid.alpha": 0.3,
                         "axes.spines.top": False, "axes.spines.right": False})

    def marcar(ax):
        if punto:
            ax.axvline(punto["usuarios"], color="#888", ls=":", lw=1)
            ax.annotate("punto de saturación", (punto["usuarios"], ax.get_ylim()[1]),
                        xytext=(4, -12), textcoords="offset points", fontsize=8, color="#555")

    def guardar(fig, nombre):
        fig.tight_layout()
        fig.savefig(os.path.join(d, nombre), dpi=140)
        plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(u, [f["rps"] for f in filas], "o-", color="#2a6fdb", lw=2, label="Medido (APM)")
    base = filas[0]["rps"] / filas[0]["usuarios"]
    ax.plot(u, [base * x for x in u], "--", color="#aaa", lw=1, label="Lineal ideal")
    ax.set_xscale("log"); ax.set_xticks(u); ax.set_xticklabels(u)
    ax.set_xlabel("Usuarios concurrentes"); ax.set_ylabel("Peticiones por segundo")
    ax.set_title("Usuarios vs throughput"); ax.legend(); marcar(ax)
    guardar(fig, "1_usuarios_vs_throughput.png")

    fig, ax = plt.subplots()
    for k, c in (("p50", "#7fb3f5"), ("p95", "#2a6fdb"), ("p99", "#0b2e6b")):
        ax.plot(u, [f[k] for f in filas], "o-", color=c, lw=2 if k == "p95" else 1.2, label=k)
    ax.axhline(MAX_P95_MS, color="#d9534f", ls="--", lw=1, label="Umbral p95 = 500 ms")
    ax.set_xscale("log"); ax.set_xticks(u); ax.set_xticklabels(u)
    ax.set_yscale("log")
    ax.set_xlabel("Usuarios concurrentes"); ax.set_ylabel("Latencia (ms, escala log)")
    ax.set_title("Usuarios vs latencia p95 (con p50 y p99)"); ax.legend(); marcar(ax)
    guardar(fig, "2_usuarios_vs_latencia_p95.png")

    fig, ax = plt.subplots()
    ax.plot(u, [f["error_pct"] for f in filas], "o-", color="#d9534f", lw=2, label="Error % (criterio)")
    ax.plot(u, [f["error_pct_apm"] for f in filas], "s--", color="#f0a39f", lw=1, label="5xx en APM")
    ax.axhline(MAX_ERROR_PCT, color="#555", ls="--", lw=1, label="Umbral 1 %")
    ax.set_xscale("log"); ax.set_xticks(u); ax.set_xticklabels(u)
    ax.set_xlabel("Usuarios concurrentes"); ax.set_ylabel("Tasa de error (%)")
    ax.set_title("Usuarios vs tasa de error"); ax.legend(); marcar(ax)
    guardar(fig, "3_usuarios_vs_tasa_error.png")

    fig, ax = plt.subplots()
    ax.plot(u, [f["cpu_app"] for f in filas], "o-", label="CPU app (límite 100 %)", color="#2a6fdb")
    ax.plot(u, [f["cpu_bd"] for f in filas], "o-", label="CPU BD (límite 100 %)", color="#5cb85c")
    ax.plot(u, [f["cpu_k6"] for f in filas], "o--", label="CPU k6 (límite 400 %)", color="#aaa")
    ax.plot(u, [f["cpu_apm"] for f in filas], "o--", label="CPU APM (límite 400 %)", color="#f0ad4e")
    ax.set_xscale("log"); ax.set_xticks(u); ax.set_xticklabels(u)
    ax.set_xlabel("Usuarios concurrentes"); ax.set_ylabel("% de un núcleo")
    ax.set_title("Consumo de CPU por contenedor"); ax.legend(fontsize=8); marcar(ax)
    guardar(fig, "4_cpu_por_contenedor.png")

    fig, ax = plt.subplots()
    ax.plot(u, [f["pool_total_prom"] for f in filas], "o-", label="Conexiones abiertas del pool", color="#2a6fdb")
    ax.plot(u, [f["pool_espera_prom"] for f in filas], "o-", label="Peticiones esperando conexión (prom.)", color="#d9534f")
    ax.plot(u, [f["conex_bd_max"] for f in filas], "o--", label="Sesiones en PostgreSQL (máx.)", color="#5cb85c")
    ax.axhline(filas[0]["pool_max"] or 10, color="#555", ls=":", lw=1, label="Tamaño máximo del pool")
    ax.set_xscale("log"); ax.set_xticks(u); ax.set_xticklabels(u)
    ax.set_yscale("symlog")
    ax.set_xlabel("Usuarios concurrentes"); ax.set_ylabel("Cantidad")
    ax.set_title("Conjunto de conexiones a la base de datos"); ax.legend(fontsize=8); marcar(ax)
    guardar(fig, "5_conexiones_bd.png")

    con = [f for f in filas if f["trazas"]]
    if con:
        fig, ax = plt.subplots()
        x = [str(f["usuarios"]) for f in con]
        a = [f["trazas"]["pct_app"] for f in con]
        w = [f["trazas"]["pct_espera_pool"] for f in con]
        q = [f["trazas"]["pct_bd_consulta"] for f in con]
        ax.bar(x, a, label="Aplicación", color="#2a6fdb")
        ax.bar(x, w, bottom=a, label="Espera de conexión (pool)", color="#f0ad4e")
        ax.bar(x, q, bottom=[i + j for i, j in zip(a, w)], label="Consulta a la BD", color="#5cb85c")
        for i, f in enumerate(con):
            ax.annotate(f"{f['trazas']['dur_media_ms']:.1f} ms", (i, 100), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=8)
        ax.set_ylim(0, 112)
        ax.set_xlabel("Usuarios concurrentes (encima: duración media de la petición)")
        ax.set_ylabel("% del tiempo de la petición")
        ax.set_title("Desglose del tiempo de la petición según las trazas")
        ax.legend(loc="lower left", fontsize=8)
        guardar(fig, "6_desglose_trazas.png")


if __name__ == "__main__":
    main()
