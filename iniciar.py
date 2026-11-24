"""Inicia el servidor local y abre el navegador, también dentro del ejecutable."""
import argparse
import sys
import threading
import webbrowser

from waitress import create_server
from backend import create_app
from backend.config import BASE_DATOS


def main():
    parser = argparse.ArgumentParser(description="Sistema de Gestión Hospitalaria")
    parser.add_argument("--sin-navegador", action="store_true", help="No abrir el navegador automáticamente")
    parser.add_argument("--solo-api", action="store_true", help="Iniciar únicamente el backend REST")
    parser.add_argument("--puerto", type=int, default=5000, help="Puerto local (0 selecciona uno libre)")
    args = parser.parse_args()
    if not 0 <= args.puerto <= 65535:
        parser.error("El puerto debe estar entre 0 y 65535.")
    app = create_app(servir_frontend=not args.solo_api)
    try:
        servidor = create_server(app, host="127.0.0.1", port=args.puerto)
    except OSError:
        # Si el puerto pedido está ocupado, se elige uno libre automáticamente.
        if args.puerto == 0:
            raise
        servidor = create_server(app, host="127.0.0.1", port=0)
    url = f"http://127.0.0.1:{servidor.effective_port}"
    print("\nSistema de Gestión Hospitalaria - Flask + SQLite", flush=True)
    print(f"Abrir: {url}", flush=True)
    print(f"Base de datos: {BASE_DATOS}", flush=True)
    print("Mantén esta ventana abierta. Para apagar: Ctrl+C o cierra esta ventana.\n", flush=True)
    if not args.sin_navegador and not args.solo_api:
        # Se abre el navegador medio segundo después, ya con el servidor escuchando.
        temporizador = threading.Timer(0.5, webbrowser.open, args=(url,))
        temporizador.daemon = True
        temporizador.start()
    try:
        servidor.run()
    except KeyboardInterrupt:
        print("\nAplicación apagada. Los datos permanecen guardados.")
    finally:
        servidor.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nNo se pudo iniciar la aplicación: {error}", file=sys.stderr)
        print("Extrae el ZIP en una carpeta donde puedas guardar archivos.", file=sys.stderr)
        if sys.stdin is not None and sys.stdin.isatty():
            input("Presiona Enter para cerrar...")
        raise SystemExit(1)
