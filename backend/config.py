"""Rutas de ejecución y campos públicos de la API."""
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
FRONTEND = RAIZ / "frontend"
# Con PyInstaller (sys.frozen) los datos viven junto al ejecutable; en el código fuente, en la raíz.
CARPETA_PROGRAMA = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else RAIZ
BASE_DATOS = CARPETA_PROGRAMA / "data" / "hospital.db"

# Páginas HTML permitidas: cualquier otro archivo .html se responde con 404.
PAGINAS = {"index.html", "pacientes.html", "consulta.html", "centros.html", "areas.html", "camas.html"}

# Campos que se leen y se devuelven al navegador.
CAMPOS = {
    "pacientes": ("id", "cedula", "nombres", "nacimiento", "telefono", "triaje",
                  "motivo", "signos", "triaje_fecha", "cama"),
    "centros": ("id", "nombre", "direccion", "telefono"),
    "areas": ("id", "centroId", "nombre", "tipo"),
    "habitaciones": ("id", "areaId", "numero", "piso", "tipo"),
    "camas": ("id", "habitacionId", "codigo", "estado", "pacienteId", "observacion"),
}

# Campos que el cliente puede escribir. `cama` se calcula al asignar una cama.
EDITABLES = {
    "pacientes": ("cedula", "nombres", "nacimiento", "telefono", "triaje",
                  "motivo", "signos", "triaje_fecha"),
    "centros": ("nombre", "direccion", "telefono"),
    "areas": ("centroId", "nombre", "tipo"),
    "habitaciones": ("areaId", "numero", "piso", "tipo"),
    "camas": ("habitacionId", "codigo", "estado", "pacienteId", "observacion"),
}

# Catálogos cerrados que usan las validaciones antes de escribir en SQLite.
TIPOS_AREA = {"Emergencia", "Consulta externa", "Hospitalización", "Quirófano", "Laboratorio", "Imágenes"}
TIPOS_HABITACION = {"Individual", "Doble", "UCI", "Aislamiento", "Observación"}
ESTADOS_CAMA = {"Disponible", "Ocupada", "Mantenimiento"}
TRIAJES = {"", "Nivel I", "Nivel II", "Nivel III", "Nivel IV"}
