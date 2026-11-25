import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

DB_PATH = Path("data/vintalytics.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS lotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        nombre TEXT NOT NULL,
        variedad TEXT,
        anada TEXT,
        region TEXT,
        parcela TEXT,
        tipo_vino TEXT,
        fecha_inicio TEXT,
        responsable TEXT,
        etapa TEXT NOT NULL DEFAULT 'Elaboración',
        descripcion TEXT,
        observaciones TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS analisis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        responsable TEXT,
        metodo TEXT,
        observaciones TEXT,
        ph REAL,
        acidez_total REAL,
        acidez_volatil REAL,
        alcohol REAL,
        azucares_residuales REAL,
        glucosa REAL,
        fructosa REAL,
        so2_libre REAL,
        so2_total REAL,
        acido_malico REAL,
        acido_lactico REAL,
        FOREIGN KEY(lote_id) REFERENCES lotes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS catas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        responsable TEXT,
        color TEXT,
        claridad TEXT,
        intensidad_aromatica TEXT,
        descriptores TEXT,
        acidez_percibida TEXT,
        dulzor TEXT,
        taninos TEXT,
        cuerpo TEXT,
        persistencia TEXT,
        observaciones TEXT,
        defectos TEXT,
        FOREIGN KEY(lote_id) REFERENCES lotes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS almacenamiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER NOT NULL,
        tipo_recipiente TEXT,
        identificador TEXT,
        material TEXT,
        fecha_inicio TEXT,
        temperatura REAL,
        condiciones TEXT,
        cierre TEXT,
        observaciones TEXT,
        registrado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lote_id) REFERENCES lotes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS seguimiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        tipo TEXT,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        FOREIGN KEY(lote_id) REFERENCES lotes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS predicciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER,
        modelo_nombre TEXT,
        modelo_version TEXT,
        variables_json TEXT,
        prediccion TEXT,
        confianza REAL,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lote_id) REFERENCES lotes(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS modelos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        version TEXT NOT NULL,
        tipo TEXT,
        dataset TEXT,
        objetivo TEXT,
        features TEXT,
        metricas_json TEXT,
        ruta_archivo TEXT,
        entrenado_en TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS procesos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote_id INTEGER NOT NULL,
        etapa TEXT,
        fecha TEXT,
        descripcion TEXT,
        FOREIGN KEY(lote_id) REFERENCES lotes(id) ON DELETE CASCADE
    );
    """
    schema = schema.replace("INTO", "NOT NULL") if "INTO" in schema else schema
    with connection() as conn:
        conn.executescript(schema)
        conn.commit()


def fetch_df(query: str, params=()):
    import pandas as pd
    with connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def execute(query: str, params=()):
    with connection() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid
