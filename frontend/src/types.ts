/** Contrato con la Lambda. Debe reflejar exactamente lo que devuelve app.py. */

export interface ExpedienteResponse {
  /** URL prefirmada de S3 con el HTML del expediente. Caduca en 7 días. */
  url: string;
  /** "owner/repo" */
  repo: string;
  /** El relato en Markdown, que es lo que renderiza la app. */
  narrativa: string;
  commits_analizados: number;
  expira_en: string;
  /** Idioma en el que se generó el relato. */
  idioma: string;
  /** true si el expediente ya existía en S3 y no se volvió a generar. */
  cache: boolean;
}

/** Códigos que emite errors.py en el backend, más los propios del cliente. */
export type CodigoError =
  | "url_invalida"
  | "repo_no_encontrado"
  | "rate_limit"
  | "github_no_responde"
  | "narrador_no_responde"
  | "token_invalido"
  | "error_interno"
  | "sin_configurar"
  | "red";

export interface ErrorExpediente {
  codigo: CodigoError;
  mensaje: string;
}
