"""El flujo completo de una excavación, independiente de dónde se ejecute.

`app.py` (Lambda) y `scripts/local_run.py` comparten esta función; así el
script local prueba exactamente el mismo camino que corre en producción.
"""

import logging
import os
import time
from typing import Any

import github_client
import narrator
import renderer
from errors import IDIOMA_DEFECTO, normalizar_idioma

log = logging.getLogger(__name__)

MAX_COMMITS = int(os.environ.get("MAX_COMMITS", "10"))
MAX_README_CHARS = int(os.environ.get("MAX_README_CHARS", "4000"))


def excavar(repo_url: str, token: str, idioma: str = IDIOMA_DEFECTO) -> dict[str, Any]:
    """Devuelve {repo, narrativa, html, commits, idioma}. Lanza ArqueologoError."""
    inicio = time.monotonic()
    idioma = normalizar_idioma(idioma)

    owner, nombre = github_client.parse_repo_url(repo_url)
    repo = f"{owner}/{nombre}"

    meta = github_client.get_metadata(owner, nombre, token)
    commits = github_client.get_commits(owner, nombre, token, MAX_COMMITS)
    readme = github_client.get_readme(owner, nombre, token, MAX_README_CHARS)

    relato, uso = narrator.narrar(meta, readme, commits, idioma)
    html = renderer.render(relato, repo, commits, idioma)

    log.info(
        "excavado repo=%s idioma=%s commits=%d readme_chars=%d tokens_in=%s tokens_out=%s duracion=%.1fs",
        repo,
        idioma,
        len(commits),
        len(readme),
        uso.get("inputTokens"),
        uso.get("outputTokens"),
        time.monotonic() - inicio,
    )

    return {"repo": repo, "narrativa": relato, "html": html, "commits": commits, "idioma": idioma}
