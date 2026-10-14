#!/usr/bin/env python3
"""Serve o dashboard e o CSV localmente, sem dependencias externas."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
ENDERECO = "127.0.0.1"
PORTA = 8000


def main() -> None:
    handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(  # noqa: E731
        *args, directory=str(RAIZ), **kwargs
    )
    servidor = ThreadingHTTPServer((ENDERECO, PORTA), handler)
    url = f"http://{ENDERECO}:{PORTA}/visualization/dashboard.html"
    print(f"Dashboard disponível em: {url}")
    print("Pressione Ctrl+C para encerrar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
