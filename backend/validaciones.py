"""Reglas de negocio verificadas en el servidor para altas y modificaciones."""
from datetime import date
import re
from .config import CAMPOS, TIPOS_AREA, TRIAJES
from .errores import ErrorValidacion
from .utilidades import normalizar

def validar(coleccion, entrada, conexion):
    if not isinstance(entrada, dict):
        raise ErrorValidacion("Envía un objeto JSON con los datos del registro.")
    registro = {}
    for campo in CAMPOS[coleccion][1:]:
        valor = entrada.get(campo, "")
        if not isinstance(valor, str):
            raise ErrorValidacion("Este campo debe ser texto.", campo)
        registro[campo] = valor.strip()
        if len(registro[campo]) > 500:
            raise ErrorValidacion("El campo admite un máximo de 500 caracteres.", campo)
    obligatorios = {
        "pacientes": ("cedula", "nombres", "nacimiento", "telefono"),
        "centros": ("nombre", "direccion", "telefono"),
        "areas": ("centroId", "nombre", "tipo"),
    }
    for campo in obligatorios[coleccion]:
        if not registro[campo]:
            raise ErrorValidacion("Este campo es obligatorio.", campo)
    if "telefono" in registro and not re.fullmatch(r"[0-9]{7,10}", registro["telefono"]):
        raise ErrorValidacion("El teléfono debe tener entre 7 y 10 dígitos.", "telefono")
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
    else:
        registro["nombre_clave"] = normalizar(registro["nombre"])
    if coleccion == "areas":
        if registro["tipo"] not in TIPOS_AREA:
            raise ErrorValidacion("Selecciona un tipo de área válido.", "tipo")
        if not conexion.execute("SELECT 1 FROM centros WHERE id = ?", (registro["centroId"],)).fetchone():
            raise ErrorValidacion("El centro seleccionado ya no existe.", "centroId")
    return registro
