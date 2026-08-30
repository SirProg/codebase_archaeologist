"""Markdown → HTML del expediente, usando template.html."""

import html
from datetime import datetime, timezone
from pathlib import Path

import markdown

from errors import IDIOMA_DEFECTO, normalizar_idioma

PLANTILLA = Path(__file__).with_name("template.html")

# Todo el texto fijo del expediente. El relato viene del modelo ya en el idioma
# pedido; esto es solo el marco que lo rodea.
TEXTOS = {
    "es": {
        "titulo": "Expediente",
        "clasificacion": "Expediente de arqueología de software",
        "etiqueta_ref": "Ref.",
        "sello": "Excavado",
        "anexo": "Anexo · Estratos examinados",
        "pie": "Redactado el",
        "sin_commits": "(sin commits legibles)",
    },
    "en": {
        "titulo": "Case file",
        "clasificacion": "Software archaeology case file",
        "etiqueta_ref": "Ref.",
        "sello": "Excavated",
        "anexo": "Appendix · Strata examined",
        "pie": "Filed on",
        "sin_commits": "(no readable commits)",
    },
}

FORMATO_FECHA = {"es": "%d/%m/%Y %H:%M UTC", "en": "%Y-%m-%d %H:%M UTC"}


def _commits_html(commits: list[dict[str, str]], idioma: str) -> str:
    filas = [
        "<li>"
        f'<span class="sha">{html.escape(c["sha"])}</span> · '
        f'{html.escape(c["fecha"])} · '
        f'<span class="autor">{html.escape(c["autor"])}</span> · '
        f'{html.escape(c["mensaje"])}'
        "</li>"
        for c in commits
    ]
    return "\n        ".join(filas) or f"<li>{TEXTOS[idioma]['sin_commits']}</li>"


def render(
    relato_md: str,
    repo: str,
    commits: list[dict[str, str]],
    idioma: str = IDIOMA_DEFECTO,
) -> str:
    idioma = normalizar_idioma(idioma)
    t = TEXTOS[idioma]
    cuerpo = markdown.markdown(relato_md, extensions=["extra", "nl2br"])
    ahora = datetime.now(timezone.utc)

    plantilla = PLANTILLA.read_text(encoding="utf-8")
    # str.replace y no str.format: la plantilla está llena de llaves de CSS.
    return (
        plantilla.replace("{{LANG}}", idioma)
        .replace("{{TITULO}}", t["titulo"])
        .replace("{{CLASIFICACION}}", t["clasificacion"])
        .replace("{{ETIQUETA_REF}}", t["etiqueta_ref"])
        .replace("{{SELLO}}", t["sello"])
        .replace("{{ANEXO}}", t["anexo"])
        .replace("{{PIE}}", t["pie"])
        .replace("{{REPO}}", html.escape(repo))
        .replace("{{REF}}", ref(repo, idioma))
        .replace("{{CUERPO}}", cuerpo)
        .replace("{{COMMITS}}", _commits_html(commits, idioma))
        .replace("{{FECHA}}", ahora.strftime(FORMATO_FECHA[idioma]))
    )


def ref(repo: str, idioma: str = IDIOMA_DEFECTO) -> str:
    """Referencia del expediente: owner-repo-AAAAMMDD-idioma.

    El idioma forma parte de la referencia porque un mismo repo excavado el
    mismo día en dos idiomas son dos expedientes distintos.
    """
    slug = repo.replace("/", "-")
    return f"{slug}-{datetime.now(timezone.utc):%Y%m%d}-{normalizar_idioma(idioma)}"


def key_html(repo: str, idioma: str = IDIOMA_DEFECTO) -> str:
    return f"expedientes/{ref(repo, idioma)}.html"


def key_md(repo: str, idioma: str = IDIOMA_DEFECTO) -> str:
    """El Markdown se guarda junto al HTML para que un acierto de cache
    pueda devolver también el relato que el frontend renderiza."""
    return f"expedientes/{ref(repo, idioma)}.md"
