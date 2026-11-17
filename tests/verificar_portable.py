"""Prueba el ZIP real en otra carpeta, sin usar Python ni paquetes externos en el EXE."""
from pathlib import Path
from contextlib import contextmanager
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from zipfile import ZipFile
import socket

RAIZ = Path(__file__).resolve().parents[1]


@contextmanager
def carpeta_temporal(carpeta_pruebas):
    destino = Path(tempfile.mkdtemp(prefix="Prueba portátil con espacios ", dir=carpeta_pruebas)).resolve()
    assert destino.is_relative_to(carpeta_pruebas.resolve())
    try:
        yield destino
    finally:
        # Windows puede tardar un instante en liberar la imagen del ejecutable.
        for intento in range(50):
            try:
                shutil.rmtree(destino)
                break
            except PermissionError:
                if intento == 49:
                    raise
                time.sleep(0.1)


def iniciar(ejecutable, puerto):
    entorno = os.environ.copy()
    entorno["PATH"] = ""
    for variable in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        entorno.pop(variable, None)
    proceso = subprocess.Popen(
        [str(ejecutable), "--sin-navegador", "--puerto", str(puerto)],
        cwd=ejecutable.parent.parent, env=entorno,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    lineas = queue.Queue()

    def leer():
        for linea in proceso.stdout:
            lineas.put(linea)
        lineas.put(None)

    threading.Thread(target=leer, daemon=True).start()
    limite = time.monotonic() + 45
    salida = []
    try:
        while time.monotonic() < limite:
            linea = lineas.get(timeout=max(0.1, limite - time.monotonic()))
            if linea is None:
                break
            salida.append(linea)
            encontrado = re.search(r"Abrir: (http://127\.0\.0\.1:\d+)", linea)
            if encontrado:
                return proceso, encontrado.group(1)
        raise RuntimeError("El ejecutable no inició: " + "".join(salida))
    except Exception:
        apagar(proceso)
        raise


def apagar(proceso):
    if proceso.poll() is None:
        # PyInstaller crea un proceso hijo; cerramos exclusivamente ese árbol de prueba.
        taskkill = Path(os.environ["SystemRoot"]) / "System32" / "taskkill.exe"
        subprocess.run([str(taskkill), "/PID", str(proceso.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    proceso.wait(timeout=10)
    proceso.stdout.close()


def pedir(url, ruta, datos=None):
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    solicitud = urllib.request.Request(url + ruta, data=cuerpo,
                                      headers={"Content-Type": "application/json"} if datos is not None else {})
    with urllib.request.urlopen(solicitud, timeout=10) as respuesta:
        return json.load(respuesta)


def main():
    carpeta_pruebas = RAIZ / "build"
    carpeta_pruebas.mkdir(exist_ok=True)
    with carpeta_temporal(carpeta_pruebas) as temporal:
        destino = Path(temporal).resolve()
        assert destino.is_relative_to(carpeta_pruebas.resolve())
        with ZipFile(RAIZ / "Hospital_Portable.zip") as archivo:
            archivo.extractall(destino)
        ejecutable = destino / "Hospital_Portable" / "Hospital.exe"
        # Ocupa intencionalmente un puerto para comprobar el cambio automático.
        with socket.socket() as ocupado:
            ocupado.bind(("127.0.0.1", 0))
            ocupado.listen()
            puerto_ocupado = ocupado.getsockname()[1]
            proceso, url = iniciar(ejecutable, puerto_ocupado)
            try:
                assert url != f"http://127.0.0.1:{puerto_ocupado}"
                for ruta in ["/", "/pacientes.html", "/consulta.html", "/centros.html", "/areas.html",
                             "/css/style.css", "/js/api.js", "/js/crud.js", "/assets/hospital.svg"]:
                    with urllib.request.urlopen(url + ruta, timeout=10) as respuesta:
                        assert respuesta.status == 200, ruta
                iniciales = pedir(url, "/api/datos")
                paciente = pedir(url, "/api/pacientes", dict(
                    cedula="8888888888", nombres="Paciente de prueba del ejecutable",
                    nacimiento="1990-01-01", telefono="0000000000", triaje="Nivel I", cama="PRUEBA-EXE"))
                identificador = paciente["registro"]["id"]
                assert pedir(url, "/api/pacientes?cedula=8888888888")["total"] == 1
                assert pedir(url, "/api/resumen")["pacientes"] == len(iniciales["pacientes"]) + 1
            finally:
                apagar(proceso)
        assert (ejecutable.parent / "data" / "hospital.db").is_file()
        proceso, url = iniciar(ejecutable, 0)
        try:
            datos = pedir(url, "/api/datos")
            assert any(p["id"] == identificador and p["cama"] == "PRUEBA-EXE" for p in datos["pacientes"])
        finally:
            apagar(proceso)
    print("OK: ZIP extraído, EXE autónomo, rutas con espacios y tildes, recursos, puerto ocupado y persistencia tras reinicio.")


if __name__ == "__main__":
    main()
