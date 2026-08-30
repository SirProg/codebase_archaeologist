"""Excepciones tipadas del agente.

Cada una lleva el código HTTP y el identificador que verá el frontend, de modo
que `app.py` nunca tenga que adivinar qué devolver ni filtrar un stack trace
hacia el usuario.
"""


class ArqueologoError(Exception):
    """Base de todos los errores esperados del flujo."""

    codigo_http = 500
    codigo = "error_interno"
    mensaje_default = "Algo salió mal durante la excavación."

    def __init__(self, mensaje: str | None = None):
        self.mensaje = mensaje or self.mensaje_default
        super().__init__(self.mensaje)

    def as_dict(self) -> dict:
        return {"error": self.codigo, "mensaje": self.mensaje}


class UrlInvalida(ArqueologoError):
    codigo_http = 400
    codigo = "url_invalida"
    mensaje_default = "Esa URL no parece un repositorio de GitHub."


class RepoNoEncontrado(ArqueologoError):
    codigo_http = 404
    codigo = "repo_no_encontrado"
    mensaje_default = "El repositorio no existe o es privado."


class RateLimit(ArqueologoError):
    codigo_http = 429
    codigo = "rate_limit"
    mensaje_default = "GitHub nos cortó el paso por exceso de peticiones. Intenta en unos minutos."


class TokenInvalido(ArqueologoError):
    """El PAT de GitHub caducó o está mal guardado en SSM.

    Es un fallo de configuración del servicio, no del usuario: se distingue del
    resto para que el operador sepa que hay que rotar el token.
    """

    codigo_http = 500
    codigo = "token_invalido"
    mensaje_default = "El servicio no puede autenticarse contra GitHub. Avisa a quien lo mantiene."


class GitHubCaido(ArqueologoError):
    codigo_http = 502
    codigo = "github_no_responde"
    mensaje_default = "GitHub no respondió a tiempo."


class NarradorCaido(ArqueologoError):
    codigo_http = 502
    codigo = "narrador_no_responde"
    mensaje_default = "El historiador no pudo redactar el expediente. Intenta de nuevo."
