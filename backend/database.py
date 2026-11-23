"""Conexión SQLite por solicitud, migraciones y ejemplos iniciales."""
from contextlib import closing
import sqlite3
from flask import current_app, g
from .utilidades import normalizar

VERSION_ESQUEMA = 2

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pacientes (
    id TEXT PRIMARY KEY, cedula TEXT NOT NULL UNIQUE,
    nombres TEXT NOT NULL, nacimiento TEXT NOT NULL,
    telefono TEXT NOT NULL, triaje TEXT NOT NULL DEFAULT '',
    cama TEXT NOT NULL DEFAULT '',
    motivo TEXT NOT NULL DEFAULT '', signos TEXT NOT NULL DEFAULT '',
    triaje_fecha TEXT NOT NULL DEFAULT ''
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
CREATE TABLE IF NOT EXISTS habitaciones (
    id TEXT PRIMARY KEY,
    areaId TEXT NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
    numero TEXT NOT NULL, numero_clave TEXT NOT NULL,
    piso TEXT NOT NULL, tipo TEXT NOT NULL,
    UNIQUE (areaId, numero_clave)
);
CREATE TABLE IF NOT EXISTS camas (
    id TEXT PRIMARY KEY,
    habitacionId TEXT NOT NULL REFERENCES habitaciones(id) ON DELETE CASCADE,
    codigo TEXT NOT NULL, codigo_clave TEXT NOT NULL UNIQUE,
    estado TEXT NOT NULL DEFAULT 'Disponible',
    pacienteId TEXT NOT NULL DEFAULT '', observacion TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS camas_estado ON camas(estado);
CREATE UNIQUE INDEX IF NOT EXISTS camas_paciente ON camas(pacienteId) WHERE pacienteId <> '';
"""


def _ejemplos_iniciales(conexion):
    """Carga los ejemplos una sola vez, incluso si luego se borran todos."""
    conexion.executemany("INSERT INTO pacientes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("p1", "0951234567", "María Fernanda Vera López", "1992-04-18", "0991234567",
         "Nivel III", "", "Dolor abdominal de 12 horas", "TA 118/76 · FC 88 · T 36.8 °C · SpO2 97 %",
         "2026-11-20 08:15"),
        ("p2", "0104567890", "Luis Alberto Cárdenas Paredes", "1978-11-02", "0987654321",
         "Nivel II", "", "Traumatismo en miembro inferior derecho", "TA 130/85 · FC 96 · T 37.1 °C · SpO2 96 %",
         "2026-11-20 09:40"),
        ("p3", "1723456789", "Ana Sofía Zambrano Ruiz", "2001-07-25", "0976543210",
         "", "", "", "", ""),
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
        ("a4", "c2", "Hospitalización", "Hospitalización"),
    ]:
        conexion.execute("INSERT INTO areas VALUES (?, ?, ?, ?, ?)",
                         (clave, centro, nombre, normalizar(nombre), tipo))


def _habitaciones_iniciales(conexion):
    """Crea camas de ejemplo en las áreas de emergencia y hospitalización."""
    if conexion.execute("SELECT COUNT(*) FROM habitaciones").fetchone()[0]:
        return
    areas = conexion.execute("""
        SELECT a.id, a.tipo FROM areas a
        WHERE a.tipo IN ('Hospitalización', 'Emergencia')
        ORDER BY CASE a.tipo WHEN 'Hospitalización' THEN 0 ELSE 1 END, a.id
        LIMIT 4
    """).fetchall()
    contador = 0
    for indice, (area_id, tipo) in enumerate(areas, 1):
        numero = str(indice * 100 + 1)
        tipo_habitacion = "Individual" if tipo == "Hospitalización" else "Observación"
        conexion.execute("INSERT INTO habitaciones VALUES (?, ?, ?, ?, ?, ?)",
                         (f"h{indice}", area_id, numero, normalizar(numero), str(min(indice, 4)),
                          tipo_habitacion))
        prefijo = "H" if tipo == "Hospitalización" else "E"
        for _ in range(2):
            contador += 1
            codigo = f"{prefijo}-{contador:02d}"
            conexion.execute("INSERT INTO camas VALUES (?, ?, ?, ?, 'Disponible', '', '')",
                             (f"ca{indice}{contador}", f"h{indice}", codigo, normalizar(codigo)))
    primera = conexion.execute("""
        SELECT ca.id FROM camas ca JOIN habitaciones h ON h.id = ca.habitacionId
        WHERE h.tipo = 'Individual' ORDER BY ca.codigo LIMIT 1
    """).fetchone()
    if primera and conexion.execute("SELECT 1 FROM pacientes WHERE id = 'p1'").fetchone():
        conexion.execute("UPDATE camas SET pacienteId = 'p1', estado = 'Ocupada' WHERE id = ?",
                         (primera[0],))
        conexion.execute("UPDATE pacientes SET cama = (SELECT codigo FROM camas WHERE id = ?) WHERE id = 'p1'",
                         (primera[0],))


def inicializar(conexion):
    """Aplica el esquema del Sprint 2 sin perder los datos del Sprint 1."""
    version = conexion.execute("PRAGMA user_version").fetchone()[0]
    if version >= VERSION_ESQUEMA:
        return
    try:
        conexion.executescript("BEGIN IMMEDIATE;" + ESQUEMA)
        columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(pacientes)")}
        for nombre, definicion in (
            ("motivo", "TEXT NOT NULL DEFAULT ''"),
            ("signos", "TEXT NOT NULL DEFAULT ''"),
            ("triaje_fecha", "TEXT NOT NULL DEFAULT ''"),
        ):
            if nombre not in columnas:
                conexion.execute(f"ALTER TABLE pacientes ADD COLUMN {nombre} {definicion}")
        if version == 0:
            _ejemplos_iniciales(conexion)
        _habitaciones_iniciales(conexion)
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
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
