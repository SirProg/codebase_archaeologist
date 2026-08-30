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

export async function excavar(repoUrl: string): Promise<ExpedienteResponse> {
  if (!BASE) {
    throw new ExcavacionError(
      "sin_configurar",
      "Falta VITE_API_URL. Copia .env.example a .env.local y apúntalo a tu endpoint.",
    );
  }

  const control = new AbortController();
  const reloj = setTimeout(() => control.abort(), TIMEOUT_MS);

  let resp: Response;
  try {
    resp = await fetch(`${BASE.replace(/\/$/, "")}/excavate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl.trim() }),
      signal: control.signal,
    });
  } catch (err) {
    // AbortError, fallo de DNS o un preflight de CORS rechazado caen aquí.
    const abortado = err instanceof DOMException && err.name === "AbortError";
    throw new ExcavacionError(
      "red",
      abortado
        ? "La excavación tardó demasiado. Prueba con un repositorio más pequeño."
        : "No se pudo contactar con el servicio. Revisa tu conexión o la configuración de CORS.",
    );
  } finally {
    clearTimeout(reloj);
  }

  let cuerpo: unknown;
  try {
    cuerpo = await resp.json();
  } catch {
    throw new ExcavacionError("error_interno", "El servicio devolvió una respuesta ilegible.");
  }

  if (!resp.ok) {
    const e = cuerpo as Partial<{ error: CodigoError; mensaje: string }>;
    throw new ExcavacionError(
      e?.error ?? "error_interno",
      e?.mensaje ?? `El servicio respondió ${resp.status}.`,
    );
  }

  return cuerpo as ExpedienteResponse;
}
