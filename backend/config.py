"""Rutas de ejecución y campos públicos de la API."""
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
FRONTEND = RAIZ / "frontend"
CARPETA_PROGRAMA = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else RAIZ
BASE_DATOS = CARPETA_PROGRAMA / "data" / "hospital.db"

PAGINAS = {"index.html", "pacientes.html", "consulta.html", "centros.html", "areas.html"}
CAMPOS = {
    "pacientes": ("id", "cedula", "nombres", "nacimiento", "telefono", "triaje", "cama"),
    "centros": ("id", "nombre", "direccion", "telefono"),
    "areas": ("id", "centroId", "nombre", "tipo"),
}
TIPOS_AREA = {"Emergencia", "Consulta externa", "Hospitalización", "Quirófano", "Laboratorio", "Imágenes"}
TRIAJES = {"", "Nivel I", "Nivel II", "Nivel III", "Nivel IV"}
