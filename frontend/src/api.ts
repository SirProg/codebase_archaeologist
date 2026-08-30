import { TEXTOS, type Idioma } from "./i18n";
import type { CodigoError, ExpedienteResponse } from "./types";

const BASE = import.meta.env.VITE_API_URL as string | undefined;

/** La excavación tarda 10-20 s; cortamos bastante después, no antes. */
const TIMEOUT_MS = 45_000;

export class ExcavacionError extends Error {
  codigo: CodigoError;

  constructor(codigo: CodigoError, mensaje: string) {
    super(mensaje);
    this.name = "ExcavacionError";
    this.codigo = codigo;
  }
}

/** Filtro barato en cliente: evita un viaje al servidor por una URL obviamente mala. */
export function pareceRepoGitHub(valor: string): boolean {
  const limpio = valor.trim();
  if (!limpio || limpio.length > 300) return false;
  return /^(https?:\/\/)?(www\.)?github\.com\/[A-Za-z0-9][A-Za-z0-9-]*\/[A-Za-z0-9._-]+/i.test(
    limpio,
  );
}

export async function excavar(repoUrl: string, idioma: Idioma): Promise<ExpedienteResponse> {
  const t = TEXTOS[idioma];

  if (!BASE) {
    throw new ExcavacionError("sin_configurar", t.errorSinConfigurar);
  }

  const control = new AbortController();
  const reloj = setTimeout(() => control.abort(), TIMEOUT_MS);

  let resp: Response;
  try {
    resp = await fetch(`${BASE.replace(/\/$/, "")}/excavate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl.trim(), idioma }),
      signal: control.signal,
    });
  } catch (err) {
    // AbortError, fallo de DNS o un preflight de CORS rechazado caen aquí.
    const abortado = err instanceof DOMException && err.name === "AbortError";
    throw new ExcavacionError("red", abortado ? t.errorTimeout : t.errorRed);
  } finally {
    clearTimeout(reloj);
  }

  let cuerpo: unknown;
  try {
    cuerpo = await resp.json();
  } catch {
    throw new ExcavacionError("error_interno", t.errorIlegible);
  }

  if (!resp.ok) {
    const e = cuerpo as Partial<{ error: CodigoError; mensaje: string }>;
    // El backend ya devuelve `mensaje` en el idioma pedido; el fallback es
    // por si la respuesta no trae cuerpo legible.
    throw new ExcavacionError(e?.error ?? "error_interno", e?.mensaje ?? t.errorServicio(resp.status));
  }

  return cuerpo as ExpedienteResponse;
}
