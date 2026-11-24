"""Factoría Flask: conecta API, SQLite y, opcionalmente, el frontend."""
from pathlib import Path
import sqlite3
from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from .config import BASE_DATOS, FRONTEND, PAGINAS
from .database import init_app
from .errores import ErrorValidacion
from .rutas import api


def create_app(database_path=None, servir_frontend=True):
    app = Flask(__name__, static_folder=None)
    app.config.update(DATABASE=Path(database_path) if database_path is not None else BASE_DATOS,
                      MAX_CONTENT_LENGTH=32 * 1024, TRUSTED_HOSTS=["localhost", "127.0.0.1"])
    app.json.ensure_ascii = False
    init_app(app)
    app.register_blueprint(api)

    @app.before_request
    def comprobar_origen():
        # Protección CSRF básica: las escrituras solo se aceptan desde este mismo host.
        if request.method in {"POST", "PUT", "DELETE"}:
            origen = request.headers.get("Origin")
            if origen and origen != request.host_url.rstrip("/"):
                abort(403)

    @app.after_request
    def cabeceras(respuesta):
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        respuesta.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        respuesta.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'")
        if request.path.startswith("/api/"):
            respuesta.headers["Cache-Control"] = "no-store"
        elif request.path.startswith(("/css/", "/js/", "/assets/")):
            # Los recursos estáticos llevan ETag; se revalidan en cada carga.
            respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta

    if servir_frontend:
        @app.get("/")
        def inicio():
            return send_from_directory(FRONTEND, "index.html")

        @app.get("/<pagina>.html")
        def pagina(pagina):
            archivo = pagina + ".html"
            if archivo not in PAGINAS:
                abort(404)
            return send_from_directory(FRONTEND, archivo)

        @app.get("/<carpeta>/<path:archivo>")
        def recurso(carpeta, archivo):
            if carpeta not in {"css", "js", "assets"}:
                abort(404)
            return send_from_directory(FRONTEND / carpeta, archivo)

    @app.errorhandler(ErrorValidacion)
    def error_validacion(error):
        return jsonify(error=error.mensaje, campo=error.campo), error.estado

    @app.errorhandler(sqlite3.IntegrityError)
    def error_integridad(error):
        mensaje = str(error)
        if "pacientes.cedula" in mensaje:
            return jsonify(error="Ya existe un paciente con esa cédula.", campo="cedula"), 409
        if "camas.codigo_clave" in mensaje:
            return jsonify(error="Ya existe una cama con ese código.", campo="codigo"), 409
        if "habitaciones" in mensaje and "numero_clave" in mensaje:
            return jsonify(error="Ya existe una habitación con ese número en el área.", campo="numero"), 409
        if "nombre_clave" in mensaje:
            return jsonify(error="Ya existe un registro con ese nombre en este centro o colección.", campo="nombre"), 409
        return jsonify(error="El registro entra en conflicto con los datos existentes."), 409

    @app.errorhandler(sqlite3.Error)
    def error_base_datos(error):
        app.logger.exception("No se pudo acceder a SQLite")
        return jsonify(error="No se pudo guardar o leer la base de datos. Inténtalo nuevamente."), 503

    @app.errorhandler(HTTPException)
    def error_http(error):
        if request.path.startswith("/api/"):
            mensajes = {400: "La solicitud contiene datos no válidos.",
                        403: "La solicitud no está autorizada desde ese origen.",
                        404: "El recurso solicitado no existe.",
                        405: "El método HTTP no está permitido.",
                        413: "El registro es demasiado grande.",
                        415: "Envía los datos en formato JSON."}
            return jsonify(error=mensajes.get(error.code, error.description)), error.code
        return error

    return app


def create_api():
    """Backend independiente para trabajar con otro servidor de frontend."""
    return create_app(servir_frontend=False)
