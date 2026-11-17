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


def guardar(coleccion, entrada, identificador=None):
    comprobar_coleccion(coleccion)
    db = get_db()
    with db:
        db.execute("BEGIN IMMEDIATE")
        if identificador is not None:
            obtener(coleccion, identificador)
        registro = validar(coleccion, entrada, db)
        if identificador is None:
            identificador = coleccion[0] + uuid4().hex
            registro["id"] = identificador
            repositorios.insertar(db, coleccion, registro)
        else:
            repositorios.actualizar(db, coleccion, identificador, registro)
        resultado = repositorios.obtener(db, coleccion, identificador)
    return resultado


def eliminar(coleccion, identificador):
    comprobar_coleccion(coleccion)
    db = get_db()
    with db:
        db.execute("BEGIN IMMEDIATE")
        obtener(coleccion, identificador)
        repositorios.eliminar(db, coleccion, identificador)


def resumen():
    db = get_db()
    with db:
        db.execute("BEGIN")
        return repositorios.resumen(db)


def todos_los_datos():
    db = get_db()
    with db:
        db.execute("BEGIN")
        return {nombre: repositorios.listar(db, nombre) for nombre in CAMPOS}
