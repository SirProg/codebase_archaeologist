"""Markdown → HTML del expediente, usando template.html."""

import html
from datetime import datetime, timezone
from pathlib import Path

import markdown

PLANTILLA = Path(__file__).with_name("template.html")


def _commits_html(commits: list[dict[str, str]]) -> str:
    filas = []
    for c in commits:
        filas.append(
            "<li>"
            f'<span class="sha">{html.escape(c["sha"])}</span> · '
            f'{html.escape(c["fecha"])} · '
            f'<span class="autor">{html.escape(c["autor"])}</span> · '
            f'{html.escape(c["mensaje"])}'
            "</li>"
        )
    return "\n        ".join(filas) or "<li>(sin commits legibles)</li>"


def render(relato_md: str, repo: str, commits: list[dict[str, str]]) -> str:
    cuerpo = markdown.markdown(relato_md, extensions=["extra", "nl2br"])
    ahora = datetime.now(timezone.utc)

    plantilla = PLANTILLA.read_text(encoding="utf-8")
    # str.replace y no str.format: la plantilla está llena de llaves de CSS.
    return (
        plantilla.replace("{{REPO}}", html.escape(repo))
        .replace("{{REF}}", ref(repo))
        .replace("{{CUERPO}}", cuerpo)
        .replace("{{COMMITS}}", _commits_html(commits))
        .replace("{{FECHA}}", ahora.strftime("%d/%m/%Y %H:%M UTC"))
    )


def ref(repo: str) -> str:
    """Referencia estable del expediente: owner-repo-AAAAMMDD."""
    slug = repo.replace("/", "-")
    return f"{slug}-{datetime.now(timezone.utc):%Y%m%d}"


def key_html(repo: str) -> str:
    return f"expedientes/{ref(repo)}.html"


def key_md(repo: str) -> str:
    """El Markdown se guarda junto al HTML para que un acierto de cache
    pueda devolver también el relato que el frontend renderiza."""
    return f"expedientes/{ref(repo)}.md"
