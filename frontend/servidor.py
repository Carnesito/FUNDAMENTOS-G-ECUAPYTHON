"""Servidor de desarrollo del frontend con proxy local a la API Flask."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

FRONTEND = Path(__file__).resolve().parent
PAGINAS = {"/", "/index.html", "/pacientes.html", "/consulta.html", "/centros.html", "/areas.html"}


def crear_servidor(puerto=5500, api="http://127.0.0.1:5000"):
    destino = urlsplit(api)
    if destino.scheme != "http" or destino.hostname not in {"127.0.0.1", "localhost"} or destino.path not in {"", "/"}:
        raise ValueError("La API debe ser una dirección HTTP local, sin rutas adicionales.")

    class FrontendHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(FRONTEND), **kwargs)

        def error_json(self, estado, mensaje):
            cuerpo = json.dumps({"error": mensaje}).encode("utf-8")
            self.send_response(estado)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def proxy(self):
            # Solo se atiende a este equipo y a peticiones del mismo origen.
            if self.headers.get("Host", "").split(":")[0] not in {"127.0.0.1", "localhost"}:
                return self.error_json(400, "Host no permitido.")
            if not self.path.startswith("/api/"):
                return self.error_json(404, "El recurso solicitado no existe.")
            origen = self.headers.get("Origin")
            if self.command != "GET" and origen and origen != "http://" + self.headers.get("Host", ""):
                return self.error_json(403, "Origen no permitido.")
            try:
                longitud = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self.error_json(400, "Longitud de solicitud no válida.")
            if longitud < 0 or longitud > 32 * 1024:
                return self.error_json(413, "El registro es demasiado grande.")
            # Se lee el cuerpo enviado por el navegador para reenviarlo tal cual a la API.
            cuerpo = self.rfile.read(longitud) if longitud else None
            cabeceras = {"Content-Type": self.headers.get("Content-Type", "application/json")}
            solicitud = Request(api.rstrip("/") + self.path, data=cuerpo, headers=cabeceras, method=self.command)
            try:
                respuesta = urlopen(solicitud, timeout=15)
            except HTTPError as error:
                respuesta = error
            except URLError:
                return self.error_json(502, "El backend no está disponible. Inícialo en el puerto configurado.")
            with respuesta:
                contenido = respuesta.read()
                self.send_response(respuesta.code)
                self.send_header("Content-Type", respuesta.headers.get("Content-Type", "application/json"))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(contenido)))
                self.end_headers()
                self.wfile.write(contenido)

        def do_GET(self):
            if self.path.startswith("/api/"):
                return self.proxy()
            ruta = urlsplit(self.path).path
            if ruta not in PAGINAS and not (ruta.startswith(("/css/", "/js/", "/assets/")) and Path(ruta).suffix in {".css", ".js", ".svg"}):
                return self.send_error(404)
            return super().do_GET()

        do_POST = proxy
        do_PUT = proxy
        do_DELETE = proxy

    return ThreadingHTTPServer(("127.0.0.1", puerto), FrontendHandler)


def main():
    parser = argparse.ArgumentParser(description="Frontend hospitalario independiente")
    parser.add_argument("--puerto", type=int, default=5500)
    parser.add_argument("--api", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    servidor = crear_servidor(args.puerto, args.api)
    print(f"Frontend: http://127.0.0.1:{servidor.server_port}\nBackend: {args.api}\nPara apagar: Ctrl+C", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
