"""lambda_handler — punto de entrada del agente."""

import json
import logging
import os

import boto3

import excavacion
import github_client
import renderer
import storage
from errors import ArqueologoError, UrlInvalida

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)

TOKEN_PARAM = os.environ.get("GITHUB_TOKEN_PARAM", "/codebase-archaeologist/github-token")
EXPIRACION_TEXTO = "7 días"

# Cacheados fuera del handler para reutilizarlos entre invocaciones tibias.
_token: str | None = None
_ssm = None


def _github_token() -> str:
    global _token, _ssm
    if _token is None:
        if os.environ.get("GITHUB_TOKEN"):
            _token = os.environ["GITHUB_TOKEN"]
        else:
            if _ssm is None:
                _ssm = boto3.client("ssm")
            resp = _ssm.get_parameter(Name=TOKEN_PARAM, WithDecryption=True)
            _token = resp["Parameter"]["Value"]
    return _token


def _respuesta(status: int, cuerpo: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(cuerpo, ensure_ascii=False),
    }


def lambda_handler(event, context):
    # El body de API Gateway es un string, nunca un objeto.
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _respuesta(400, UrlInvalida("El cuerpo de la petición no es JSON válido.").as_dict())

    repo_url = body.get("repo_url") or ""

    try:
        # Se valida y parsea aquí para poder mirar la cache antes de gastar
        # una sola llamada a GitHub o a Bedrock.
        owner, nombre = github_client.parse_repo_url(repo_url)
        owner_repo = f"{owner}/{nombre}"

        key_html = renderer.key_html(owner_repo)
        key_md = renderer.key_md(owner_repo)

        # Cache: si ya excavamos este repo hoy, devolvemos el expediente guardado.
        if storage.existe(key_html) and storage.existe(key_md):
            log.info("cache hit repo=%s", owner_repo)
            return _respuesta(
                200,
                {
                    "url": storage.url_prefirmada(key_html),
                    "repo": owner_repo,
                    "narrativa": storage.leer(key_md),
                    "commits_analizados": excavacion.MAX_COMMITS,
                    "expira_en": EXPIRACION_TEXTO,
                    "cache": True,
                },
            )

        resultado = excavacion.excavar(repo_url, _github_token())

        storage.subir(key_html, resultado["html"])
        storage.subir(key_md, resultado["narrativa"], "text/markdown; charset=utf-8")

        return _respuesta(
            200,
            {
                "url": storage.url_prefirmada(key_html),
                "repo": resultado["repo"],
                "narrativa": resultado["narrativa"],
                "commits_analizados": len(resultado["commits"]),
                "expira_en": EXPIRACION_TEXTO,
                "cache": False,
            },
        )

    except ArqueologoError as exc:
        log.warning("error esperado repo_url=%r: %s", repo_url[:120], exc.mensaje)
        return _respuesta(exc.codigo_http, exc.as_dict())
    except Exception:
        # Nunca un stack trace crudo hacia el usuario.
        log.exception("error inesperado repo_url=%r", repo_url[:120])
        return _respuesta(500, ArqueologoError().as_dict())
