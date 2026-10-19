-- Esquema y datos iniciales. Se ejecuta solo la primera vez que se crea el volumen.
CREATE TABLE IF NOT EXISTS productos (
  id              SERIAL PRIMARY KEY,
  nombre          VARCHAR(120)   NOT NULL,
  descripcion     TEXT,
  precio          NUMERIC(12, 2) NOT NULL CHECK (precio >= 0),
  stock           INTEGER        NOT NULL CHECK (stock >= 0),
  creado_en       TIMESTAMPTZ    NOT NULL DEFAULT now(),
  actualizado_en  TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- 10 000 productos semilla para que las lecturas toquen datos variados.
INSERT INTO productos (nombre, descripcion, precio, stock)
SELECT 'Producto ' || g,
       'Descripción del producto ' || g,
       round((random() * 1000)::numeric, 2),
       (random() * 500)::int
FROM generate_series(1, 10000) AS g;
