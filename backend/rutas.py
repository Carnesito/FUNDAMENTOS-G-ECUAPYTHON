"""API REST: JSON de entrada/salida; sin lógica de presentación."""
from flask import Blueprint, jsonify, request, url_for
from . import servicios

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/salud")
def salud():
    return jsonify(aplicacion="hospital-sprint2", estado="ok", version=3)


@api.get("/resumen")
def resumen():
    return jsonify(servicios.resumen())


@api.get("/disponibilidad")
def disponibilidad():
    return jsonify(servicios.disponibilidad(request.args.to_dict()))


@api.get("/datos")
def datos():
    """Lectura conjunta para respaldos e integraciones anteriores."""
    return jsonify(servicios.todos_los_datos())


@api.get("/<coleccion>")
def listar(coleccion):
    registros = servicios.listar(coleccion, request.args.to_dict())
    return jsonify(registros=registros, total=len(registros))


@api.get("/<coleccion>/<identificador>")
def obtener(coleccion, identificador):
    return jsonify(registro=servicios.obtener(coleccion, identificador))


@api.post("/<coleccion>")
def crear(coleccion):
    servicios.comprobar_coleccion(coleccion)
    registro = servicios.guardar(coleccion, request.get_json())
    respuesta = jsonify(registro=registro)
    respuesta.headers["Location"] = url_for("api.obtener", coleccion=coleccion, identificador=registro["id"])
    return respuesta, 201


@api.put("/<coleccion>/<identificador>")
def actualizar(coleccion, identificador):
    servicios.comprobar_coleccion(coleccion)
    return jsonify(registro=servicios.guardar(coleccion, request.get_json(), identificador))


@api.delete("/<coleccion>/<identificador>")
def eliminar(coleccion, identificador):
    servicios.eliminar(coleccion, identificador)
    return "", 204
