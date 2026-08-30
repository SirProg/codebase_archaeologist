"""El prompt y la llamada a Bedrock. Aquí vive el producto."""

import logging
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from errors import NarradorCaido

log = logging.getLogger(__name__)

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "amazon.nova-lite-v1:0")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1500"))

SYSTEM_PROMPT = """Eres un historiador dramático especializado en arqueología de software.
Escribes crónicas épicas sobre la evolución de proyectos de código,
tratando cada commit como un acontecimiento histórico y a cada
desarrollador como un personaje con motivaciones.

Reglas:
- Escribe en español, en Markdown.
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
- Máximo 800 palabras.
"""

_cliente = None


def _bedrock():
    """Cliente cacheado entre invocaciones tibias de la Lambda."""
    global _cliente
    if _cliente is None:
        _cliente = boto3.client("bedrock-runtime", region_name=REGION)
    return _cliente


def construir_prompt(meta: dict[str, Any], readme: str, commits: list[dict[str, str]]) -> str:
    # GitHub los devuelve del más nuevo al más viejo. Se invierten para que el
    # modelo los lea en el mismo sentido en que va a narrarlos; sin esto tiende
    # a tomar el primero de la lista por el commit fundacional del proyecto.
    cronologicos = list(reversed(commits))
    lineas = "\n".join(
        f"- {c['sha']} · {c['fecha']} · {c['autor']}: {c['mensaje']}" for c in cronologicos
    ) or "(el repositorio no tiene commits legibles)"

    if cronologicos:
        rango = f"del {cronologicos[0]['fecha']} al {cronologicos[-1]['fecha']}"
        encabezado = (
            f"Los {len(cronologicos)} commits MÁS RECIENTES, del más antiguo al más "
            f"reciente ({rango}). El repositorio se creó el {meta['creado']}; "
            "todo lo anterior a esta ventana no está en tus registros."
        )
    else:
        encabezado = "No hay commits legibles."

    return f"""<repositorio>
Nombre: {meta['nombre']}
Descripción: {meta['descripcion']}
Lenguaje: {meta['lenguaje']}
Estrellas: {meta['estrellas']}
Creado: {meta['creado']}
</repositorio>

<readme>
{readme or '(este repositorio no tiene README)'}
</readme>

<commits>
{encabezado}

{lineas}
</commits>

Escribe la crónica de este repositorio."""


def narrar(meta: dict[str, Any], readme: str, commits: list[dict[str, str]]) -> tuple[str, dict]:
    """Devuelve (relato_markdown, uso_de_tokens)."""
    prompt = construir_prompt(meta, readme, commits)

    try:
        resp = _bedrock().converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
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
        raise NarradorCaido("El modelo devolvió una respuesta vacía.") from exc

    if not relato:
        raise NarradorCaido("El modelo devolvió una respuesta vacía.")

    return relato, resp.get("usage", {})
