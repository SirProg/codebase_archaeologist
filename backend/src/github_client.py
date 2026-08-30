"""Parseo de URLs de GitHub y lectura del repositorio vía API REST."""

import base64
import logging
import re
from typing import Any

import requests

from errors import GitHubCaido, RateLimit, RepoNoEncontrado, TokenInvalido, UrlInvalida

log = logging.getLogger(__name__)

API = "https://api.github.com"
TIMEOUT = 10  # sin esto, una petición colgada se come el timeout entero de la Lambda

# Un input absurdamente largo se rechaza antes de tocar ninguna red.
MAX_URL_CHARS = 300

_HOSTS = {"github.com", "www.github.com"}
_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extrae (owner, repo) de cualquiera de las formas habituales de URL.

    Soporta https, ssh estilo scp, sufijo .git, barra final y rutas profundas
    del tipo /tree/main/src. Lanza UrlInvalida para cualquier otra cosa.
    """
    if not isinstance(url, str):
        raise UrlInvalida()

    url = url.strip()
    if not url:
        raise UrlInvalida("vacia")
    if len(url) > MAX_URL_CHARS:
        raise UrlInvalida("larga")

    # git@github.com:owner/repo.git → github.com/owner/repo.git
    scp = re.match(r"^[A-Za-z0-9_.-]+@([^:]+):(.+)$", url)
    if scp:
        url = f"{scp.group(1)}/{scp.group(2)}"

    url = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", url)  # quita el esquema
    url = url.split("?", 1)[0].split("#", 1)[0]

    partes = [p for p in url.split("/") if p]
    if not partes:
        raise UrlInvalida()

    host = partes[0].lower()
    if host not in _HOSTS:
        # Sin host reconocible tampoco aceptamos "owner/repo" a secas: es
        # demasiado fácil colar ahí una ruta de otro servicio.
        raise UrlInvalida("no_github")

    if len(partes) < 3:
        raise UrlInvalida("sin_repo")

    owner = partes[1]
    repo = re.sub(r"\.git$", "", partes[2])  # los segmentos posteriores se descartan

    if not _OWNER.match(owner) or not _REPO.match(repo):
        raise UrlInvalida("formato")

    return owner, repo


def _headers(token: str) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "codebase-archaeologist",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path: str, token: str) -> requests.Response:
    try:
        resp = requests.get(f"{API}{path}", headers=_headers(token), timeout=TIMEOUT)
    except requests.Timeout as exc:
        raise GitHubCaido("timeout") from exc
    except requests.RequestException as exc:
        raise GitHubCaido() from exc

    if resp.status_code == 401:
        # El PAT caducó (GitHub los emite a 90 días) o se leyó mal desde SSM.
        log.error("GitHub rechazó las credenciales en %s", path)
        raise TokenInvalido()
    if resp.status_code == 404:
        raise RepoNoEncontrado()
    if resp.status_code in (403, 429) and "rate limit" in resp.text.lower():
        raise RateLimit()
    if resp.status_code >= 400:
        log.warning("GitHub %s devolvió %s: %s", path, resp.status_code, resp.text[:200])
        raise GitHubCaido("status", status=resp.status_code)

    return resp


def get_metadata(owner: str, repo: str, token: str) -> dict[str, Any]:
    d = _get(f"/repos/{owner}/{repo}", token).json()
    return {
        "nombre": d.get("full_name") or f"{owner}/{repo}",
        "descripcion": d.get("description") or "Sin descripción.",
        "lenguaje": d.get("language") or "desconocido",
        "estrellas": d.get("stargazers_count", 0),
        "creado": (d.get("created_at") or "")[:10],
    }


def get_commits(owner: str, repo: str, token: str, limite: int = 10) -> list[dict[str, str]]:
    datos = _get(f"/repos/{owner}/{repo}/commits?per_page={limite}", token).json()

    commits = []
    for c in datos:
        info = c.get("commit", {})
        # `author` (la cuenta de GitHub) es null si el autor no tiene cuenta
        # vinculada; el nombre del commit siempre está.
        autor = (c.get("author") or {}).get("login") or (info.get("author") or {}).get("name") or "anónimo"
        mensaje = (info.get("message") or "").strip().splitlines()
        commits.append(
            {
                "sha": (c.get("sha") or "")[:7],
                "autor": autor,
                "fecha": ((info.get("author") or {}).get("date") or "")[:10],
                "mensaje": mensaje[0] if mensaje else "(sin mensaje)",
            }
        )
    return commits


def get_readme(owner: str, repo: str, token: str, max_chars: int = 4000) -> str:
    """Devuelve el README decodificado, o cadena vacía si el repo no tiene."""
    try:
        d = _get(f"/repos/{owner}/{repo}/readme", token).json()
    except RepoNoEncontrado:
        return ""  # un repo sin README es un caso válido, no un error

    contenido = d.get("content") or ""
    try:
        texto = base64.b64decode(contenido).decode("utf-8", errors="replace")
    except Exception:
        log.warning("No se pudo decodificar el README de %s/%s", owner, repo)
        return ""

    return texto[:max_chars]
