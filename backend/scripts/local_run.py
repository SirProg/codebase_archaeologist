#!/usr/bin/env python3
"""Ejecuta el flujo completo sin AWS desplegado.

    export GITHUB_TOKEN="ghp_..."
    python scripts/local_run.py https://github.com/psf/requests

Imprime el relato en consola y escribe salida_local.html en el directorio
actual. Solo necesita credenciales de AWS para Bedrock; ni Lambda, ni S3, ni
API Gateway intervienen.
"""

import argparse
import logging
import os
import pathlib
import sys
import webbrowser

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import excavacion  # noqa: E402
from errors import ArqueologoError  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Excava un repositorio de GitHub.")
    ap.add_argument("repo_url", help="URL del repositorio a excavar")
    ap.add_argument("-o", "--output", default="salida_local.html", help="archivo HTML de salida")
    ap.add_argument("--abrir", action="store_true", help="abrir el resultado en el navegador")
    ap.add_argument("-v", "--verbose", action="store_true", help="mostrar logs de la excavación")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print(
            "⚠️  GITHUB_TOKEN no está definido: GitHub limitará a 60 peticiones/hora.\n",
            file=sys.stderr,
        )

    try:
        resultado = excavacion.excavar(args.repo_url, token)
    except ArqueologoError as exc:
        print(f"❌ [{exc.codigo}] {exc.mensaje}", file=sys.stderr)
        return 1

    print(resultado["narrativa"])

    destino = pathlib.Path(args.output)
    destino.write_text(resultado["html"], encoding="utf-8")
    print(f"\n📄 Expediente escrito en {destino.resolve()}", file=sys.stderr)

    if args.abrir:
        webbrowser.open(destino.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
