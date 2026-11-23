"""Consultas parametrizadas. Solo este módulo conoce el SQL de los recursos."""
from .config import CAMPOS
from .utilidades import normalizar

BUSQUEDAS = {
    "pacientes": "r.cedula || ' ' || r.nombres || ' ' || r.telefono || ' ' || r.motivo",
    "centros": "r.nombre || ' ' || r.direccion",
    "areas": "r.nombre || ' ' || c.nombre",
    "habitaciones": "r.numero || ' ' || r.piso || ' ' || a.nombre || ' ' || c.nombre",
    "camas": "r.codigo || ' ' || h.numero || ' ' || a.nombre || ' ' || c.nombre",
}


def seleccion(coleccion):
    campos = ", ".join("r." + campo for campo in CAMPOS[coleccion])
    if coleccion == "centros":
        return (f"SELECT {campos}, (SELECT COUNT(*) FROM areas a WHERE a.centroId = r.id) AS areasCount "
                "FROM centros r")
    if coleccion == "areas":
        return (f"SELECT {campos}, c.nombre AS centroNombre "
                "FROM areas r JOIN centros c ON c.id = r.centroId")
    if coleccion == "habitaciones":
        return (f"SELECT {campos}, a.nombre AS areaNombre, a.centroId AS centroId, "
                "c.nombre AS centroNombre, "
                "(SELECT COUNT(*) FROM camas ca WHERE ca.habitacionId = r.id) AS camasCount, "
                "(SELECT COUNT(*) FROM camas ca WHERE ca.habitacionId = r.id AND ca.estado = 'Disponible') "
                "AS disponiblesCount "
                "FROM habitaciones r JOIN areas a ON a.id = r.areaId "
                "JOIN centros c ON c.id = a.centroId")
    if coleccion == "camas":
        return (f"SELECT {campos}, h.numero AS habitacionNumero, h.piso, h.areaId AS areaId, "
                "a.nombre AS areaNombre, a.centroId AS centroId, c.nombre AS centroNombre, "
                "(SELECT p.nombres FROM pacientes p WHERE p.id = r.pacienteId) AS pacienteNombre "
                "FROM camas r JOIN habitaciones h ON h.id = r.habitacionId "
                "JOIN areas a ON a.id = h.areaId JOIN centros c ON c.id = a.centroId")
    return f"SELECT {campos} FROM pacientes r"


def orden(coleccion):
    if coleccion == "pacientes":
        return ("CASE r.triaje WHEN 'Nivel I' THEN 0 WHEN 'Nivel II' THEN 1 "
                "WHEN 'Nivel III' THEN 2 WHEN 'Nivel IV' THEN 3 ELSE 4 END, "
                "normalizar(r.nombres), r.id")
    if coleccion == "habitaciones":
        return "normalizar(c.nombre), normalizar(a.nombre), normalizar(r.numero), r.id"
    if coleccion == "camas":
        return "normalizar(c.nombre), normalizar(a.nombre), normalizar(r.codigo), r.id"
    nombre = "r.nombres" if coleccion == "pacientes" else "r.nombre"
    return f"normalizar({nombre}), r.id"


def listar(db, coleccion, filtros=None):
    filtros = filtros or {}
    condiciones, valores = [], []
    if filtros.get("q"):
        condiciones.append(f"instr(normalizar({BUSQUEDAS[coleccion]}), ?) > 0")
        valores.append(normalizar(filtros["q"]))
    if coleccion == "pacientes":
        for campo in ("cedula", "triaje"):
            if filtros.get(campo):
                condiciones.append(f"r.{campo} = ?")
                valores.append(filtros[campo])
        if filtros.get("apellidos"):
            condiciones.append("instr(normalizar(r.nombres), ?) > 0")
            valores.append(normalizar(filtros["apellidos"]))
    if coleccion == "areas" and filtros.get("centroId"):
        condiciones.append("r.centroId = ?")
        valores.append(filtros["centroId"])
    if coleccion == "habitaciones":
        if filtros.get("centroId"):
            condiciones.append("a.centroId = ?")
            valores.append(filtros["centroId"])
        if filtros.get("areaId"):
            condiciones.append("r.areaId = ?")
            valores.append(filtros["areaId"])
    if coleccion == "camas":
        for campo, columna in (("estado", "r.estado"), ("centroId", "a.centroId"),
                               ("areaId", "h.areaId"), ("habitacionId", "r.habitacionId"),
                               ("pacienteId", "r.pacienteId")):
            if filtros.get(campo):
                condiciones.append(f"{columna} = ?")
                valores.append(filtros[campo])
        if filtros.get("sinPaciente") in ("1", "true"):
            condiciones.append("r.pacienteId = ''")
    sql = seleccion(coleccion)
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY " + orden(coleccion)
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
    db.execute(f"UPDATE {coleccion} SET {asignaciones} WHERE id = ?",
               [*registro.values(), identificador])


def eliminar(db, coleccion, identificador):
    db.execute(f"DELETE FROM {coleccion} WHERE id = ?", (identificador,))


def resumen(db):
    totales = {nombre: db.execute(f"SELECT COUNT(*) FROM {nombre}").fetchone()[0] for nombre in CAMPOS}
    for estado, clave in (("Disponible", "camasDisponibles"), ("Ocupada", "camasOcupadas"),
                          ("Mantenimiento", "camasMantenimiento")):
        totales[clave] = db.execute("SELECT COUNT(*) FROM camas WHERE estado = ?", (estado,)).fetchone()[0]
    return totales


def disponibilidad(db, filtros=None):
    """Camas totales, disponibles, ocupadas y en mantenimiento por centro y área."""
    filtros = filtros or {}
    condiciones, valores = ["1 = 1"], []
    if filtros.get("centroId"):
        condiciones.append("c.id = ?")
        valores.append(filtros["centroId"])
    if filtros.get("areaId"):
        condiciones.append("a.id = ?")
        valores.append(filtros["areaId"])
    filas = [dict(fila) for fila in db.execute(f"""
        SELECT c.id AS centroId, c.nombre AS centro, a.id AS areaId, a.nombre AS area,
               COUNT(ca.id) AS total,
               SUM(CASE WHEN ca.estado = 'Disponible' THEN 1 ELSE 0 END) AS disponibles,
               SUM(CASE WHEN ca.estado = 'Ocupada' THEN 1 ELSE 0 END) AS ocupadas,
               SUM(CASE WHEN ca.estado = 'Mantenimiento' THEN 1 ELSE 0 END) AS mantenimiento,
               (SELECT COUNT(*) FROM habitaciones h2 WHERE h2.areaId = a.id) AS habitaciones
        FROM centros c
        LEFT JOIN areas a ON a.centroId = c.id
        LEFT JOIN habitaciones h ON h.areaId = a.id
        LEFT JOIN camas ca ON ca.habitacionId = h.id
        WHERE {' AND '.join(condiciones)}
        GROUP BY c.id, c.nombre, a.id, a.nombre
        ORDER BY normalizar(c.nombre), normalizar(a.nombre)
    """, valores)]
    centros = {}
    for fila in filas:
        centro = centros.setdefault(fila["centroId"], {
            "id": fila["centroId"], "nombre": fila["centro"], "total": 0,
            "disponibles": 0, "ocupadas": 0, "mantenimiento": 0, "habitaciones": 0,
            "areas": [],
        })
        if fila["areaId"]:
            centro["areas"].append({
                "id": fila["areaId"], "nombre": fila["area"], "total": fila["total"],
                "disponibles": fila["disponibles"], "ocupadas": fila["ocupadas"],
                "mantenimiento": fila["mantenimiento"], "habitaciones": fila["habitaciones"],
            })
        for clave in ("total", "disponibles", "ocupadas", "mantenimiento", "habitaciones"):
            centro[clave] += fila[clave] or 0
    totales = {clave: sum(centro[clave] for centro in centros.values())
               for clave in ("total", "disponibles", "ocupadas", "mantenimiento", "habitaciones")}
    totales["areas"] = sum(len(centro["areas"]) for centro in centros.values())
    return {"centros": list(centros.values()), "totales": totales}
