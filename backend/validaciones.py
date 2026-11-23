"""Reglas de negocio verificadas en el servidor para altas y modificaciones."""
from datetime import date, datetime
import re
from .config import (EDITABLES, ESTADOS_CAMA, TIPOS_AREA,
                     TIPOS_HABITACION, TRIAJES)
from .errores import ErrorValidacion
from .utilidades import normalizar

OBLIGATORIOS = {
    "pacientes": ("cedula", "nombres", "nacimiento", "telefono"),
    "centros": ("nombre", "direccion", "telefono"),
    "areas": ("centroId", "nombre", "tipo"),
    "habitaciones": ("areaId", "numero", "piso", "tipo"),
    "camas": ("habitacionId", "codigo", "estado"),
}


def validar(coleccion, entrada, conexion, identificador=None):
    if not isinstance(entrada, dict):
        raise ErrorValidacion("Envía un objeto JSON con los datos del registro.")
    registro = {}
    for campo in EDITABLES[coleccion]:
        valor = entrada.get(campo, "")
        if not isinstance(valor, str):
            raise ErrorValidacion("Este campo debe ser texto.", campo)
        registro[campo] = valor.strip()
        if len(registro[campo]) > 500:
            raise ErrorValidacion("El campo admite un máximo de 500 caracteres.", campo)
    for campo in OBLIGATORIOS[coleccion]:
        if not registro[campo]:
            raise ErrorValidacion("Este campo es obligatorio.", campo)

    if "telefono" in registro and not re.fullmatch(r"[0-9]{7,10}", registro["telefono"]):
        raise ErrorValidacion("El teléfono debe tener entre 7 y 10 dígitos.", "telefono")

    if coleccion in ("pacientes", "centros", "areas"):
        campo_nombre = "nombres" if coleccion == "pacientes" else "nombre"
        if len(registro[campo_nombre]) < 3:
            raise ErrorValidacion("Escribe un nombre de al menos 3 caracteres.", campo_nombre)

    if coleccion == "pacientes":
        if not re.fullmatch(r"[0-9]{10}", registro["cedula"]):
            raise ErrorValidacion("La cédula debe tener 10 dígitos.", "cedula")
        try:
            nacimiento = date.fromisoformat(registro["nacimiento"])
            if nacimiento.isoformat() != registro["nacimiento"]:
                raise ValueError
        except ValueError:
            raise ErrorValidacion("La fecha de nacimiento no es válida.", "nacimiento") from None
        if nacimiento > date.today() or nacimiento.year < 1900:
            raise ErrorValidacion("La fecha debe estar entre 1900 y hoy.", "nacimiento")
        if registro["triaje"] not in TRIAJES:
            raise ErrorValidacion("Selecciona un nivel de triaje válido.", "triaje")
        if len(registro["motivo"]) > 200:
            raise ErrorValidacion("El motivo admite un máximo de 200 caracteres.", "motivo")
        if len(registro["signos"]) > 200:
            raise ErrorValidacion("Los signos vitales admiten un máximo de 200 caracteres.", "signos")
        if registro["triaje_fecha"]:
            try:
                datetime.fromisoformat(registro["triaje_fecha"].replace("T", " "))
            except ValueError:
                raise ErrorValidacion("La fecha y hora del triaje no es válida.", "triaje_fecha") from None

    elif coleccion == "centros":
        registro["nombre_clave"] = normalizar(registro["nombre"])

    elif coleccion == "areas":
        if registro["tipo"] not in TIPOS_AREA:
            raise ErrorValidacion("Selecciona un tipo de área válido.", "tipo")
        if not conexion.execute("SELECT 1 FROM centros WHERE id = ?", (registro["centroId"],)).fetchone():
            raise ErrorValidacion("El centro seleccionado ya no existe.", "centroId")
        registro["nombre_clave"] = normalizar(registro["nombre"])

    elif coleccion == "habitaciones":
        if registro["tipo"] not in TIPOS_HABITACION:
            raise ErrorValidacion("Selecciona un tipo de habitación válido.", "tipo")
        if not conexion.execute("SELECT 1 FROM areas WHERE id = ?", (registro["areaId"],)).fetchone():
            raise ErrorValidacion("El área seleccionada ya no existe.", "areaId")
        registro["numero_clave"] = normalizar(registro["numero"])

    elif coleccion == "camas":
        if registro["estado"] not in ESTADOS_CAMA:
            raise ErrorValidacion("Selecciona un estado de cama válido.", "estado")
        if len(registro["codigo"]) < 2:
            raise ErrorValidacion("El código de la cama debe tener al menos 2 caracteres.", "codigo")
        if not conexion.execute("SELECT 1 FROM habitaciones WHERE id = ?",
                                (registro["habitacionId"],)).fetchone():
            raise ErrorValidacion("La habitación seleccionada ya no existe.", "habitacionId")
        if registro["pacienteId"]:
            if not conexion.execute("SELECT 1 FROM pacientes WHERE id = ?",
                                    (registro["pacienteId"],)).fetchone():
                raise ErrorValidacion("El paciente seleccionado ya no existe.", "pacienteId")
            ocupada = conexion.execute(
                "SELECT 1 FROM camas WHERE pacienteId = ? AND id <> ?",
                (registro["pacienteId"], identificador or "")).fetchone()
            if ocupada:
                raise ErrorValidacion("El paciente ya tiene una cama asignada.", "pacienteId")
            registro["estado"] = "Ocupada"
        elif registro["estado"] == "Ocupada":
            registro["estado"] = "Disponible"
        registro["codigo_clave"] = normalizar(registro["codigo"])

    return registro
