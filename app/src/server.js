const express = require('express');
const { Pool } = require('pg');
const { metrics } = require('@opentelemetry/api');

const PORT = Number(process.env.PORT || 3000);
const POOL_MAX = Number(process.env.DB_POOL_MAX || 10);

const pool = new Pool({
  host: process.env.DB_HOST || 'db',
  port: Number(process.env.DB_PORT || 5432),
  user: process.env.DB_USER || 'crud',
  password: process.env.DB_PASSWORD || 'crud',
  database: process.env.DB_NAME || 'crud',
  max: POOL_MAX,
  connectionTimeoutMillis: Number(process.env.DB_POOL_TIMEOUT_MS || 5000),
});

// Métricas del conjunto de conexiones, visibles en el APM (columna "Conex. BD").
const meter = metrics.getMeter('crud-productos');
meter.createObservableGauge('db.pool.total', { description: 'Conexiones abiertas del pool' })
  .addCallback((r) => r.observe(pool.totalCount));
meter.createObservableGauge('db.pool.idle', { description: 'Conexiones libres del pool' })
  .addCallback((r) => r.observe(pool.idleCount));
meter.createObservableGauge('db.pool.waiting', { description: 'Peticiones esperando conexión' })
  .addCallback((r) => r.observe(pool.waitingCount));
meter.createObservableGauge('db.pool.max', { description: 'Tamaño máximo del pool' })
  .addCallback((r) => r.observe(POOL_MAX));

const app = express();
app.use(express.json());

const CAMPOS = 'id, nombre, descripcion, precio, stock, creado_en, actualizado_en';

function validar(body, parcial = false) {
  const errores = [];
  const { nombre, descripcion, precio, stock } = body || {};
  if (!parcial || nombre !== undefined) {
    if (typeof nombre !== 'string' || !nombre.trim()) errores.push('nombre es obligatorio');
  }
  if (descripcion !== undefined && descripcion !== null && typeof descripcion !== 'string') {
    errores.push('descripcion debe ser texto');
  }
  if (!parcial || precio !== undefined) {
    if (typeof precio !== 'number' || precio < 0) errores.push('precio debe ser un número >= 0');
  }
  if (!parcial || stock !== undefined) {
    if (!Number.isInteger(stock) || stock < 0) errores.push('stock debe ser un entero >= 0');
  }
  return errores;
}

function idValido(req, res) {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ error: 'id inválido' });
    return null;
  }
  return id;
}

app.get('/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({ estado: 'ok' });
  } catch (e) {
    res.status(503).json({ estado: 'error', detalle: e.message });
  }
});

// Listar (paginado)
app.get('/api/productos', async (req, res, next) => {
  try {
    const limit = Math.min(Math.max(Number(req.query.limit) || 20, 1), 100);
    const offset = Math.max(Number(req.query.offset) || 0, 0);
    const { rows } = await pool.query(
      `SELECT ${CAMPOS} FROM productos ORDER BY id LIMIT $1 OFFSET $2`, [limit, offset]);
    res.json(rows);
  } catch (e) { next(e); }
});

// Consultar uno
app.get('/api/productos/:id', async (req, res, next) => {
  const id = idValido(req, res); if (id === null) return;
  try {
    const { rows } = await pool.query(`SELECT ${CAMPOS} FROM productos WHERE id = $1`, [id]);
    if (!rows.length) return res.status(404).json({ error: 'no encontrado' });
    res.json(rows[0]);
  } catch (e) { next(e); }
});

// Crear
app.post('/api/productos', async (req, res, next) => {
  const errores = validar(req.body);
  if (errores.length) return res.status(400).json({ errores });
  try {
    const { nombre, descripcion = null, precio, stock } = req.body;
    const { rows } = await pool.query(
      `INSERT INTO productos (nombre, descripcion, precio, stock) VALUES ($1, $2, $3, $4)
       RETURNING ${CAMPOS}`, [nombre, descripcion, precio, stock]);
    res.status(201).json(rows[0]);
  } catch (e) { next(e); }
});

// Actualizar
app.put('/api/productos/:id', async (req, res, next) => {
  const id = idValido(req, res); if (id === null) return;
  const errores = validar(req.body);
  if (errores.length) return res.status(400).json({ errores });
  try {
    const { nombre, descripcion = null, precio, stock } = req.body;
    const { rows } = await pool.query(
      `UPDATE productos SET nombre = $1, descripcion = $2, precio = $3, stock = $4,
       actualizado_en = now() WHERE id = $5 RETURNING ${CAMPOS}`,
      [nombre, descripcion, precio, stock, id]);
    if (!rows.length) return res.status(404).json({ error: 'no encontrado' });
    res.json(rows[0]);
  } catch (e) { next(e); }
});

// Eliminar
app.delete('/api/productos/:id', async (req, res, next) => {
  const id = idValido(req, res); if (id === null) return;
  try {
    const { rowCount } = await pool.query('DELETE FROM productos WHERE id = $1', [id]);
    if (!rowCount) return res.status(404).json({ error: 'no encontrado' });
    res.status(204).end();
  } catch (e) { next(e); }
});

app.use((err, _req, res, _next) => {
  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({ error: 'JSON inválido' });
  }
  console.error(err.message);
  res.status(500).json({ error: 'error interno', detalle: err.message });
});

app.listen(PORT, () => {
  console.log(`CRUD escuchando en :${PORT} (pool BD max=${POOL_MAX})`);
});
