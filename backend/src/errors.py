"""Excepciones tipadas del agente.

Cada una lleva el código HTTP y el identificador que verá el frontend, más el
mensaje en los idiomas soportados. Se lanzan con la clave de una variante
(`raise UrlInvalida("vacia")`) en lugar de con un texto literal, para que el
idioma se resuelva al serializar la respuesta y no al construir el error.
"""

IDIOMAS = ("es", "en")
IDIOMA_DEFECTO = "es"


def normalizar_idioma(valor: object) -> str:
    """Acepta 'en', 'EN', 'en-US'… y cae al defecto ante cualquier otra cosa."""
    if not isinstance(valor, str):
        return IDIOMA_DEFECTO
    corto = valor.strip().lower().replace("_", "-").split("-")[0]
    return corto if corto in IDIOMAS else IDIOMA_DEFECTO


class ArqueologoError(Exception):
    """Base de todos los errores esperados del flujo."""

    codigo_http = 500
    codigo = "error_interno"
    variantes: dict = {
        None: {
            "es": "Algo salió mal durante la excavación.",
            "en": "Something went wrong during the excavation.",
        }
    }

    def __init__(self, variante: str | None = None, **formato):
        self.variante = variante
        self.formato = formato
        super().__init__(self.mensaje(IDIOMA_DEFECTO))

    def mensaje(self, idioma: str = IDIOMA_DEFECTO) -> str:
        idioma = normalizar_idioma(idioma)
        textos = self.variantes.get(self.variante) or self.variantes[None]
        return textos.get(idioma, textos[IDIOMA_DEFECTO]).format(**self.formato)

    def as_dict(self, idioma: str = IDIOMA_DEFECTO) -> dict:
        return {"error": self.codigo, "mensaje": self.mensaje(idioma)}


class UrlInvalida(ArqueologoError):
    codigo_http = 400
    codigo = "url_invalida"
    variantes = {
        None: {
            "es": "Esa URL no parece un repositorio de GitHub.",
            "en": "That URL doesn't look like a GitHub repository.",
        },
        "vacia": {
            "es": "Pega la URL de un repositorio para empezar.",
            "en": "Paste a repository URL to get started.",
        },
        "larga": {
            "es": "Esa URL es demasiado larga.",
            "en": "That URL is too long.",
        },
        "no_github": {
            "es": "Solo se pueden excavar repositorios de github.com.",
            "en": "Only github.com repositories can be excavated.",
        },
        "sin_repo": {
            "es": "Falta el nombre del repositorio en la URL.",
            "en": "The repository name is missing from the URL.",
        },
        "formato": {
            "es": "El formato owner/repo de esa URL no es válido.",
            "en": "The owner/repo format of that URL is not valid.",
        },
        "json": {
            "es": "El cuerpo de la petición no es JSON válido.",
            "en": "The request body is not valid JSON.",
        },
    }


class RepoNoEncontrado(ArqueologoError):
    codigo_http = 404
    codigo = "repo_no_encontrado"
    variantes = {
        None: {
            "es": "El repositorio no existe o es privado.",
            "en": "The repository doesn't exist or is private.",
        }
    }


class RateLimit(ArqueologoError):
    codigo_http = 429
    codigo = "rate_limit"
    variantes = {
        None: {
            "es": "GitHub nos cortó el paso por exceso de peticiones. Intenta en unos minutos.",
            "en": "GitHub cut us off for too many requests. Try again in a few minutes.",
        }
    }


class TokenInvalido(ArqueologoError):
    """El PAT de GitHub caducó o está mal guardado en SSM.

    Es un fallo de configuración del servicio, no del usuario: se distingue del
    resto para que el operador sepa que hay que rotar el token.
    """

    codigo_http = 500
    codigo = "token_invalido"
    variantes = {
        None: {
            "es": "El servicio no puede autenticarse contra GitHub. Avisa a quien lo mantiene.",
            "en": "The service can't authenticate against GitHub. Let its maintainer know.",
        }
    }


class GitHubCaido(ArqueologoError):
    codigo_http = 502
    codigo = "github_no_responde"
    variantes = {
        None: {
            "es": "GitHub no respondió a tiempo.",
            "en": "GitHub didn't respond in time.",
        },
        "timeout": {
            "es": "GitHub tardó demasiado en responder.",
            "en": "GitHub took too long to respond.",
        },
        "status": {
            "es": "GitHub respondió {status}.",
            "en": "GitHub responded {status}.",
        },
    }


class NarradorCaido(ArqueologoError):
    codigo_http = 502
    codigo = "narrador_no_responde"
    variantes = {
        None: {
            "es": "El historiador no pudo redactar el expediente. Intenta de nuevo.",
            "en": "The historian couldn't write the case file. Try again.",
        },
        "vacio": {
            "es": "El modelo devolvió una respuesta vacía.",
            "en": "The model returned an empty response.",
        },
    }
