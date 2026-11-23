"""Operaciones de negocio y límites de las transacciones."""
from uuid import uuid4
from . import repositorios
from .config import CAMPOS
from .database import get_db
from .errores import ErrorValidacion
from .validaciones import validar


def comprobar_coleccion(coleccion):
    if coleccion not in CAMPOS:
        raise ErrorValidacion("El recurso solicitado no existe.", estado=404)


def listar(coleccion, filtros=None):
    comprobar_coleccion(coleccion)
    for valor in (filtros or {}).values():
        if len(valor) > 500:
            raise ErrorValidacion("El criterio de búsqueda es demasiado largo.")
    return repositorios.listar(get_db(), coleccion, filtros)


def obtener(coleccion, identificador):
    comprobar_coleccion(coleccion)
    registro = repositorios.obtener(get_db(), coleccion, identificador)
    if registro is None:
        raise ErrorValidacion("El registro no existe o ya fue eliminado.", estado=404)
    return registro


def sincronizar_cama(db, paciente_id):
    """Mantiene `pacientes.cama` con el código de la cama realmente asignada."""
    db.execute("""
        UPDATE pacientes SET cama = COALESCE(
            (SELECT codigo FROM camas WHERE pacienteId = ? ORDER BY codigo LIMIT 1), '')
        WHERE id = ?
    """, (paciente_id, paciente_id))
    # Al quedar vinculado a una cama real, el texto heredado del Sprint 1 ya no aplica.
    db.execute("""
        UPDATE pacientes SET cama_heredada = ''
        WHERE id = ? AND EXISTS (SELECT 1 FROM camas WHERE pacienteId = ?)
    """, (paciente_id, paciente_id))


def _pacientes_afectados(db, coleccion, identificador):
    if coleccion == "camas":
        filas = db.execute("SELECT pacienteId FROM camas WHERE id = ?", (identificador,))
    elif coleccion == "habitaciones":
        filas = db.execute("SELECT pacienteId FROM camas WHERE habitacionId = ?", (identificador,))
    elif coleccion == "areas":
        filas = db.execute("""
            SELECT ca.pacienteId FROM camas ca
            JOIN habitaciones h ON h.id = ca.habitacionId WHERE h.areaId = ?
        """, (identificador,))
    elif coleccion == "centros":
        filas = db.execute("""
            SELECT ca.pacienteId FROM camas ca
            JOIN habitaciones h ON h.id = ca.habitacionId
            JOIN areas a ON a.id = h.areaId WHERE a.centroId = ?
        """, (identificador,))
    else:
        return []
    return [fila[0] for fila in filas if fila[0]]


def guardar(coleccion, entrada, identificador=None):
    comprobar_coleccion(coleccion)
    db = get_db()
    with db:
        db.execute("BEGIN IMMEDIATE")
        anterior = None
        if identificador is not None:
            anterior = obtener(coleccion, identificador)
        registro = validar(coleccion, entrada, db, identificador)
        if identificador is None:
            identificador = coleccion[0] + uuid4().hex
            registro["id"] = identificador
            repositorios.insertar(db, coleccion, registro)
        else:
            repositorios.actualizar(db, coleccion, identificador, registro)
        if coleccion == "camas":
            for paciente in {registro.get("pacienteId", ""), (anterior or {}).get("pacienteId", "")}:
                if paciente:
                    sincronizar_cama(db, paciente)
        resultado = repositorios.obtener(db, coleccion, identificador)
    return resultado


def eliminar(coleccion, identificador):
    comprobar_coleccion(coleccion)
    db = get_db()
    with db:
        db.execute("BEGIN IMMEDIATE")
        obtener(coleccion, identificador)
        afectados = _pacientes_afectados(db, coleccion, identificador)
        if coleccion == "pacientes":
            db.execute("""
                UPDATE camas SET pacienteId = '',
                    estado = CASE WHEN estado = 'Ocupada' THEN 'Disponible' ELSE estado END
                WHERE pacienteId = ?
            """, (identificador,))
        repositorios.eliminar(db, coleccion, identificador)
        for paciente in afectados:
            sincronizar_cama(db, paciente)


def resumen():
    db = get_db()
    with db:
        db.execute("BEGIN")
        return repositorios.resumen(db)


def disponibilidad(filtros=None):
    db = get_db()
    with db:
        db.execute("BEGIN")
        return repositorios.disponibilidad(db, filtros)


def todos_los_datos():
    db = get_db()
    with db:
        db.execute("BEGIN")
        return {nombre: repositorios.listar(db, nombre) for nombre in CAMPOS}
