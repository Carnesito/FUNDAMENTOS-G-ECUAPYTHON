"""Conexión SQLite por solicitud e inicialización del esquema."""
from contextlib import closing
import sqlite3
from flask import current_app, g
from .utilidades import normalizar

def inicializar(conexion):
    """Carga los ejemplos una sola vez, incluso si luego se borran todos."""
    if conexion.execute("PRAGMA user_version").fetchone()[0] != 0:
        return
    conexion.executescript("""
        BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS pacientes (
            id TEXT PRIMARY KEY, cedula TEXT NOT NULL UNIQUE,
            nombres TEXT NOT NULL, nacimiento TEXT NOT NULL,
            telefono TEXT NOT NULL, triaje TEXT NOT NULL DEFAULT '',
            cama TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS centros (
            id TEXT PRIMARY KEY, nombre TEXT NOT NULL,
            nombre_clave TEXT NOT NULL UNIQUE,
            direccion TEXT NOT NULL, telefono TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS areas (
            id TEXT PRIMARY KEY,
            centroId TEXT NOT NULL REFERENCES centros(id) ON DELETE CASCADE,
            nombre TEXT NOT NULL, nombre_clave TEXT NOT NULL, tipo TEXT NOT NULL,
            UNIQUE (centroId, nombre_clave)
        );
    """)
    try:
        conexion.executemany("INSERT INTO pacientes VALUES (?, ?, ?, ?, ?, ?, ?)", [
            ("p1", "0951234567", "María Fernanda Vera López", "1992-04-18", "0991234567", "Nivel III", "UCI-02"),
            ("p2", "0104567890", "Luis Alberto Cárdenas Paredes", "1978-11-02", "0987654321", "Nivel II", ""),
            ("p3", "1723456789", "Ana Sofía Zambrano Ruiz", "2001-07-25", "0976543210", "", ""),
        ])
        for clave, nombre, direccion, telefono in [
            ("c1", "Hospital Santa Vida", "Av. Amazonas 123", "022345678"),
            ("c2", "Centro Médico El Norte", "Av. Eloy Alfaro 456", "022987654"),
        ]:
            conexion.execute("INSERT INTO centros VALUES (?, ?, ?, ?, ?)",
                             (clave, nombre, normalizar(nombre), direccion, telefono))
        for clave, centro, nombre, tipo in [
            ("a1", "c1", "Emergencia", "Emergencia"),
            ("a2", "c1", "Consulta Externa A", "Consulta externa"),
            ("a3", "c2", "Laboratorio", "Laboratorio"),
        ]:
            conexion.execute("INSERT INTO areas VALUES (?, ?, ?, ?, ?)",
                             (clave, centro, nombre, normalizar(nombre), tipo))
        conexion.execute("PRAGMA user_version = 1")
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.create_function("normalizar", 1, normalizar, deterministic=True)
    return g.db

def cerrar_db(error=None):
    conexion = g.pop("db", None)
    if conexion is not None:
        conexion.close()

def init_app(app):
    app.config["DATABASE"].parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(app.config["DATABASE"])) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        inicializar(conexion)
    app.teardown_appcontext(cerrar_db)
