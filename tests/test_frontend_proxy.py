"""Integración entre frontend independiente, API Flask y SQLite."""
from pathlib import Path
import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from waitress import create_server
from backend import create_app
from frontend.servidor import crear_servidor


class FrontendProxyTest(unittest.TestCase):
    def test_crud_a_traves_de_dos_servidores(self):
        with tempfile.TemporaryDirectory() as carpeta:
            app = create_app(Path(carpeta) / "hospital.db", servir_frontend=False)
            backend = create_server(app, host="127.0.0.1", port=0, asyncore_loop_timeout=0.1)
            hilo_backend = threading.Thread(target=backend.run, daemon=True)
            hilo_backend.start()
            frontend = crear_servidor(0, "http://127.0.0.1:" + str(backend.effective_port))
            hilo_frontend = threading.Thread(target=frontend.serve_forever, daemon=True)
            hilo_frontend.start()
            base = "http://127.0.0.1:" + str(frontend.server_port)

            def pedir(ruta, metodo="GET", datos=None, cabeceras=None):
                headers = {"Content-Type": "application/json", **(cabeceras or {})}
                cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
                return urlopen(Request(base + ruta, data=cuerpo, method=metodo, headers=headers), timeout=5)

            try:
                with pedir("/") as respuesta:
                    self.assertIn(b"js/api.js", respuesta.read())
                with pedir("/api/centros", "POST", dict(nombre="Centro del proxy", direccion="Calle Uno", telefono="0991234567")) as respuesta:
                    self.assertEqual(respuesta.status, 201)
                    registro = json.load(respuesta)["registro"]
                registro["direccion"] = "Calle Dos"
                with pedir("/api/centros/" + registro["id"], "PUT", registro) as respuesta:
                    self.assertEqual(json.load(respuesta)["registro"]["direccion"], "Calle Dos")
                with pedir("/api/centros/" + registro["id"], "DELETE") as respuesta:
                    self.assertEqual(respuesta.status, 204)
                for ruta, cabeceras, estado in [
                    ("/api/resumen", {"Host": "no-autorizado.test"}, 400),
                    ("/servidor.py", {}, 404),
                ]:
                    with self.assertRaises(HTTPError) as error:
                        pedir(ruta, cabeceras=cabeceras)
                    self.assertEqual(error.exception.code, estado)
                    error.exception.close()
            finally:
                frontend.shutdown()
                frontend.server_close()
                hilo_frontend.join(timeout=3)
                backend.close()
                hilo_backend.join(timeout=3)
                self.assertFalse(hilo_backend.is_alive())
