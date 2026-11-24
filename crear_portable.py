"""Genera el ejecutable de Windows y su ZIP, conservando SQLite fuera del EXE :)."""
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

from backend import create_app
from backend.config import BASE_DATOS

# Nota documental 5.
RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "dist" / "Hospital_Portable"
INSTRUCCIONES = """SISTEMA DE GESTION HOSPITALARIA - FLASK + SQLITE

1. Extrae TODO el ZIP en una carpeta de tu equipo o memoria USB.
2. Haz doble clic en Hospital.exe. No necesitas instalar Python ni usar internet.
3. El navegador se abre automaticamente. Manten la ventana del programa abierta.
4. Para apagarlo, presiona Ctrl+C en la ventana del programa o cierra esa ventana.

Si el navegador no se abre, copia la direccion que aparece en la ventana.
El puerto habitual es http://127.0.0.1:5000; si esta ocupado se elige otro libre.

Los datos se guardan en data/hospital.db, al lado de Hospital.exe.
Para trasladar el programa CON sus registros, apaga la aplicacion y comprime
la carpeta completa: Hospital.exe + data + este archivo. Si envias solamente
el EXE, se creara una base nueva con los ejemplos al iniciarlo.

Esta version es para Windows de 64 bits. No ejecutes el programa dentro del ZIP.
La aplicacion funciona localmente en tu equipo. Cerrar el navegador no apaga el servidor.
No abras varias copias del programa al mismo tiempo.
"""


def main():
    if sys.platform != "win32":
        raise SystemExit("Construye la versión de Windows desde Windows.")
    comando = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--console",
        "--name", "Hospital", "--distpath", str(SALIDA),
        "--workpath", str(RAIZ / "build"), "--specpath", str(RAIZ / "build"),
    ]
    for recurso in [*sorted((RAIZ / "frontend").glob("*.html")),
                    *(RAIZ / "frontend" / nombre for nombre in ("css", "js", "assets"))]:
        destino_recurso = "frontend" if recurso.is_file() else "frontend/" + recurso.name
        comando.extend(["--add-data", f"{recurso}:{destino_recurso}"])
    comando.append(str(RAIZ / "iniciar.py"))
    subprocess.run(comando, cwd=RAIZ, check=True)
    destino = SALIDA / "data" / "hospital.db"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        print("Se conserva la base de datos existente de la versión portable.")
    elif BASE_DATOS.exists():
        # Una copia coherente incluso si SQLite tiene una transacción abierta.
        with closing(sqlite3.connect(BASE_DATOS)) as origen, closing(sqlite3.connect(destino)) as copia:
            origen.backup(copia)
    else:
        create_app(destino)
    (SALIDA / "LEEME.txt").write_text(INSTRUCCIONES, encoding="utf-8")
    archivo_zip = RAIZ / "Hospital_Portable.zip"
    with ZipFile(archivo_zip, "w", ZIP_DEFLATED) as comprimido:
        for archivo in sorted(SALIDA.rglob("*")):
            if archivo.is_file():
                comprimido.write(archivo, archivo.relative_to(SALIDA.parent))
    # El código fuente se entrega aparte, sin entornos virtuales ni compilaciones.
    respaldo = RAIZ / "build" / "hospital_fuente.db"
    with closing(sqlite3.connect(BASE_DATOS if BASE_DATOS.exists() else destino)) as origen, closing(sqlite3.connect(respaldo)) as copia:
        origen.backup(copia)
    fuentes_zip = RAIZ / "Hospital_Codigo_Fuente.zip"
    with ZipFile(fuentes_zip, "w", ZIP_DEFLATED) as comprimido:
        nombres = ["app.py", "iniciar.py", "INICIAR.cmd", "crear_portable.py", "requirements.txt", "requirements-build.txt", "README.md", "API.md"]
        archivos = [RAIZ / nombre for nombre in nombres]
        for carpeta in ["backend", "frontend", "tests"]:
            archivos.extend(p for p in (RAIZ / carpeta).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".py", ".html", ".js", ".css", ".svg"})
        for archivo in sorted(archivos):
            comprimido.write(archivo, "Hospital_Codigo_Fuente/" + archivo.relative_to(RAIZ).as_posix())
        comprimido.write(respaldo, "Hospital_Codigo_Fuente/data/hospital.db")
    print(f"\nEjecutable: {SALIDA / 'Hospital.exe'}")
    print(f"Para compartir: {archivo_zip}")
    print(f"Código fuente: {fuentes_zip}")


if __name__ == "__main__":
    main()
