"""El prompt y la llamada a Bedrock. Aquí vive el producto."""

import logging
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from errors import IDIOMA_DEFECTO, NarradorCaido, normalizar_idioma

log = logging.getLogger(__name__)

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "amazon.nova-lite-v1:0")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1500"))

_REGLAS_COMUNES_ES = """
- Estructura: un título épico (encabezado nivel 1), una introducción que sitúe
  el proyecto, 3 o 4 secciones narrativas con encabezados, y un cierre que mire
  al futuro.
- Menciona SHAs y autores reales; nunca inventes commits ni personas.
- El tono es dramático pero el contenido es factual.
- Los commits que recibes son los MÁS RECIENTES del repositorio, no los
  primeros. Salvo que la fecha de creación coincida con el commit más
  antiguo de la lista, NO son el origen del proyecto: son su última etapa.
  Nunca llames "primer commit" ni "nacimiento del proyecto" a ninguno de ellos.
- La fecha de creación del repositorio y las fechas de los commits son datos
  distintos. No atribuyas la fecha de creación a un commit concreto.
- Si los mensajes de commit son pobres, vagos o repetitivos ("update", "fix",
  "asdf"), NO rellenes el vacío con hechos inventados. Convierte esa escasez en
  parte de la narrativa: los registros de esta era son fragmentarios, el
  cronista debe conjeturar, los escribas fueron parcos. Nombra explícitamente
  lo que no se puede saber.
- Máximo 800 palabras."""

_REGLAS_COMUNES_EN = """
- Structure: an epic title (level 1 heading), an introduction that situates the
  project, 3 or 4 narrative sections with headings, and a closing that looks to
  the future.
- Mention real SHAs and authors; never invent commits or people.
- The tone is dramatic but the content is factual.
- The commits you receive are the MOST RECENT ones in the repository, not the
  first. Unless the creation date matches the oldest commit in the list, they
  are NOT the project's origin: they are its latest chapter. Never call any of
  them "the first commit" or "the birth of the project".
- The repository's creation date and the commit dates are separate facts. Do
  not attribute the creation date to a specific commit.
- If the commit messages are poor, vague or repetitive ("update", "fix",
  "asdf"), do NOT fill the gap with invented facts. Turn that scarcity into
  part of the narrative: the records of this era are fragmentary, the chronicler
  must conjecture, the scribes were terse. Name explicitly what cannot be known.
- Maximum 800 words."""

SYSTEM_PROMPTS = {
    "es": """Eres un historiador dramático especializado en arqueología de software.
Escribes crónicas épicas sobre la evolución de proyectos de código,
tratando cada commit como un acontecimiento histórico y a cada
desarrollador como un personaje con motivaciones.

Reglas:
- Escribe en ESPAÑOL, en Markdown."""
    + _REGLAS_COMUNES_ES,
    "en": """You are a dramatic historian specializing in software archaeology.
You write epic chronicles about how code projects evolved, treating
every commit as a historical event and every developer as a character
with motivations.

Rules:
- Write in ENGLISH, in Markdown."""
    + _REGLAS_COMUNES_EN,
}

_cliente = None


def _bedrock():
    """Cliente cacheado entre invocaciones tibias de la Lambda."""
    global _cliente
    if _cliente is None:
        _cliente = boto3.client("bedrock-runtime", region_name=REGION)
    return _cliente


def construir_prompt(
    meta: dict[str, Any],
    readme: str,
    commits: list[dict[str, str]],
    idioma: str = IDIOMA_DEFECTO,
) -> str:
    # GitHub los devuelve del más nuevo al más viejo. Se invierten para que el
    # modelo los lea en el mismo sentido en que va a narrarlos; sin esto tiende
    # a tomar el primero de la lista por el commit fundacional del proyecto.
    cronologicos = list(reversed(commits))
    lineas = "\n".join(
        f"- {c['sha']} · {c['fecha']} · {c['autor']}: {c['mensaje']}" for c in cronologicos
    ) or ("(el repositorio no tiene commits legibles)" if idioma == "es"
          else "(the repository has no readable commits)")

    if cronologicos:
        desde, hasta = cronologicos[0]["fecha"], cronologicos[-1]["fecha"]
        if idioma == "es":
            encabezado = (
                f"Los {len(cronologicos)} commits MÁS RECIENTES, del más antiguo al más "
                f"reciente (del {desde} al {hasta}). El repositorio se creó el "
                f"{meta['creado']}; todo lo anterior a esta ventana no está en tus registros."
            )
        else:
            encabezado = (
                f"The {len(cronologicos)} MOST RECENT commits, oldest to newest "
                f"(from {desde} to {hasta}). The repository was created on "
                f"{meta['creado']}; anything before this window is not in your records."
            )
    else:
        encabezado = "No hay commits legibles." if idioma == "es" else "No readable commits."

    etiquetas = {
        "es": ("Nombre", "Descripción", "Lenguaje", "Estrellas", "Creado",
               "(este repositorio no tiene README)", "Escribe la crónica de este repositorio."),
        "en": ("Name", "Description", "Language", "Stars", "Created",
               "(this repository has no README)", "Write the chronicle of this repository."),
    }[idioma]
    nombre, desc, leng, estrellas, creado, sin_readme, instruccion = etiquetas

    return f"""<repositorio>
{nombre}: {meta['nombre']}
{desc}: {meta['descripcion']}
{leng}: {meta['lenguaje']}
{estrellas}: {meta['estrellas']}
{creado}: {meta['creado']}
</repositorio>

<readme>
{readme or sin_readme}
</readme>

<commits>
{encabezado}

{lineas}
</commits>

{instruccion}"""


def narrar(
    meta: dict[str, Any],
    readme: str,
    commits: list[dict[str, str]],
    idioma: str = IDIOMA_DEFECTO,
) -> tuple[str, dict]:
    """Devuelve (relato_markdown, uso_de_tokens)."""
    idioma = normalizar_idioma(idioma)
    prompt = construir_prompt(meta, readme, commits, idioma)

    try:
        resp = _bedrock().converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPTS[idioma]}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                # Temperatura alta: queremos prosa creativa, no precisión factual
                # (los hechos ya vienen dados en el prompt).
                "maxTokens": MAX_TOKENS,
                "temperature": 0.8,
                "topP": 0.9,
            },
        )
    except (ClientError, BotoCoreError) as exc:
        log.error("Bedrock falló con %s: %s", MODEL_ID, exc)
        raise NarradorCaido() from exc

    try:
        relato = resp["output"]["message"]["content"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        raise NarradorCaido("vacio") from exc

    if not relato:
        raise NarradorCaido("vacio")

    return relato, resp.get("usage", {})
