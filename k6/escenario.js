// Escenario de prueba de estrés del CRUD de productos (k6).
//
// Mezcla de operaciones (declarada):
//   50 % listar      GET  /api/productos?limit=20&offset=<aleatorio>
//   20 % consultar   GET  /api/productos/<id aleatorio>
//   20 % crear       POST /api/productos           (datos aleatorios)
//   10 % actualizar  PUT  /api/productos/<id aleatorio> (datos aleatorios)
//   => 70 % lecturas, 20 % creaciones, 10 % actualizaciones.
//
// Carga: 1 calentamiento (descartado del análisis) + escalones crecientes de usuarios
// concurrentes (VUs) a duración fija. Todo es parametrizable por variables de entorno:
//   ESCALONES   lista de VUs por escalón        (por defecto "100,300,600,900,1200,1500,2000")
//   DURACION    duración de cada escalón        (por defecto "3m")
//   CALENTAR_VUS / CALENTAR_DUR                 (por defecto 10 VUs durante "1m")
//   PAUSA_MIN / PAUSA_MAX  tiempo de pensamiento por usuario en segundos (0.5 / 1.5)
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://app:3000';
const ESCALONES = (__ENV.ESCALONES || '100,300,600,900,1200,1500,2000').split(',').map(Number);
const DURACION = __ENV.DURACION || '3m';
const CALENTAR_VUS = Number(__ENV.CALENTAR_VUS || 10);
const CALENTAR_DUR = __ENV.CALENTAR_DUR || '1m';
const PAUSA_MIN = Number(__ENV.PAUSA_MIN || 0.5);
const PAUSA_MAX = Number(__ENV.PAUSA_MAX || 1.5);
const SEMILLA = 10000; // filas sembradas por db/init.sql

function segundos(d) {
  const m = /^(\d+)(s|m)$/.exec(d);
  return Number(m[1]) * (m[2] === 'm' ? 60 : 1);
}

const scenarios = {
  esc_0_calentamiento: {
    executor: 'constant-vus', vus: CALENTAR_VUS, duration: CALENTAR_DUR,
    startTime: '0s', gracefulStop: '5s',
  },
};
const thresholds = {};
let inicio = segundos(CALENTAR_DUR);
ESCALONES.forEach((vus, i) => {
  const nombre = `esc_${i + 1}_${vus}u`;
  scenarios[nombre] = {
    executor: 'constant-vus', vus, duration: DURACION,
    startTime: `${inicio}s`, gracefulStop: '5s',
  };
  inicio += segundos(DURACION);
  // Umbrales "testigo": no cortan la prueba, solo hacen que el resumen
  // incluya las métricas separadas por escalón.
  thresholds[`http_req_duration{scenario:${nombre}}`] = ['p(95)<500'];
  thresholds[`http_req_failed{scenario:${nombre}}`] = ['rate<0.01'];
  thresholds[`http_reqs{scenario:${nombre}}`] = ['count>=0'];
});

export const options = {
  scenarios,
  thresholds,
  summaryTrendStats: ['avg', 'min', 'med', 'p(95)', 'p(99)', 'max'],
  discardResponseBodies: true,
};

const JSON_HDR = { headers: { 'Content-Type': 'application/json' }, timeout: '10s' };

function entero(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function texto(n) {
  const c = 'abcdefghijklmnopqrstuvwxyz ';
  let s = '';
  for (let i = 0; i < n; i++) s += c[entero(0, c.length - 1)];
  return s;
}
function productoAleatorio() {
  return JSON.stringify({
    nombre: `Prod-${__VU}-${__ITER}-${texto(8)}`,
    descripcion: texto(entero(20, 120)),
    precio: Math.round(Math.random() * 100000) / 100,
    stock: entero(0, 1000),
  });
}

// Marca de tiempo de inicio, usada por el análisis para ubicar cada escalón en el APM.
export function setup() {
  console.log(`INICIO_MS=${Date.now()}`);
}

export default function () {
  const r = Math.random();
  let res;
  if (r < 0.5) {
    res = http.get(`${BASE}/api/productos?limit=20&offset=${entero(0, SEMILLA - 20)}`,
      { tags: { name: 'listar', op: 'listar' }, timeout: '10s' });
    check(res, { 'listar 200': (x) => x.status === 200 });
  } else if (r < 0.7) {
    res = http.get(`${BASE}/api/productos/${entero(1, SEMILLA)}`,
      { tags: { name: 'consultar', op: 'consultar' }, timeout: '10s' });
    check(res, { 'consultar 200': (x) => x.status === 200 });
  } else if (r < 0.9) {
    res = http.post(`${BASE}/api/productos`, productoAleatorio(),
      Object.assign({ tags: { name: 'crear', op: 'crear' } }, JSON_HDR));
    check(res, { 'crear 201': (x) => x.status === 201 });
  } else {
    res = http.put(`${BASE}/api/productos/${entero(1, SEMILLA)}`, productoAleatorio(),
      Object.assign({ tags: { name: 'actualizar', op: 'actualizar' } }, JSON_HDR));
    check(res, { 'actualizar 200': (x) => x.status === 200 });
  }
  sleep(PAUSA_MIN + Math.random() * (PAUSA_MAX - PAUSA_MIN));
}

export function handleSummary(data) {
  return {
    '/resultados/k6-resumen.json': JSON.stringify(data, null, 2),
    stdout: `\nResumen guardado en resultados/k6-resumen.json\n`,
  };
}

