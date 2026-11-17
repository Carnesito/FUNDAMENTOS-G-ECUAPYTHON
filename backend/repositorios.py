"""Consultas parametrizadas. Solo este módulo conoce el SQL de los recursos."""
from .config import CAMPOS
from .utilidades import normalizar


def seleccion(coleccion):
    campos = ", ".join("r." + campo for campo in CAMPOS[coleccion])
    if coleccion == "centros":
        return f"SELECT {campos}, (SELECT COUNT(*) FROM areas a WHERE a.centroId = r.id) AS areasCount FROM centros r"
    if coleccion == "areas":
        return f"SELECT {campos}, c.nombre AS centroNombre FROM areas r JOIN centros c ON c.id = r.centroId"
    return f"SELECT {campos} FROM pacientes r"


def listar(db, coleccion, filtros=None):
    filtros = filtros or {}
    condiciones, valores = [], []
    if filtros.get("q"):
        campos = {"pacientes": "r.cedula || ' ' || r.nombres || ' ' || r.telefono",
                  "centros": "r.nombre || ' ' || r.direccion",
                  "areas": "r.nombre || ' ' || c.nombre"}[coleccion]
        condiciones.append(f"instr(normalizar({campos}), ?) > 0")
        valores.append(normalizar(filtros["q"]))
    if coleccion == "pacientes":
        if filtros.get("cedula"):
            condiciones.append("r.cedula = ?")
            valores.append(filtros["cedula"])
        if filtros.get("apellidos"):
            condiciones.append("instr(normalizar(r.nombres), ?) > 0")
            valores.append(normalizar(filtros["apellidos"]))
    if coleccion == "areas" and filtros.get("centroId"):
        condiciones.append("r.centroId = ?")
        valores.append(filtros["centroId"])
    sql = seleccion(coleccion)
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    nombre = "r.nombres" if coleccion == "pacientes" else "r.nombre"
    sql += f" ORDER BY normalizar({nombre}), r.id"
    return [dict(fila) for fila in db.execute(sql, valores)]


def obtener(db, coleccion, identificador):
    fila = db.execute(seleccion(coleccion) + " WHERE r.id = ?", (identificador,)).fetchone()
    return dict(fila) if fila else None


def insertar(db, coleccion, registro):
    campos = list(registro)
    db.execute(f"INSERT INTO {coleccion} ({', '.join(campos)}) VALUES ({', '.join('?' for _ in campos)})",
               [registro[campo] for campo in campos])


def actualizar(db, coleccion, identificador, registro):
    asignaciones = ", ".join(campo + " = ?" for campo in registro)
    db.execute(f"UPDATE {coleccion} SET {asignaciones} WHERE id = ?", [*registro.values(), identificador])


def eliminar(db, coleccion, identificador):
    db.execute(f"DELETE FROM {coleccion} WHERE id = ?", (identificador,))


def resumen(db):
    return {nombre: db.execute(f"SELECT COUNT(*) FROM {nombre}").fetchone()[0] for nombre in CAMPOS}
