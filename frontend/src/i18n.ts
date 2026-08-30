import type { CodigoError } from "./types";

export const IDIOMAS = ["es", "en"] as const;
export type Idioma = (typeof IDIOMAS)[number];

const CLAVE_ALMACEN = "codebase-archaeologist:idioma";

/** Idioma inicial: lo que el usuario eligió antes, si no el del navegador. */
export function idiomaInicial(): Idioma {
  try {
    const guardado = localStorage.getItem(CLAVE_ALMACEN);
    if (guardado === "es" || guardado === "en") return guardado;
  } catch {
    // Ventana privada o cookies bloqueadas: se cae a la detección del navegador.
  }
  const nav = typeof navigator !== "undefined" ? navigator.language : "";
  return nav.toLowerCase().startsWith("es") ? "es" : "en";
}

export function guardarIdioma(idioma: Idioma): void {
  try {
    localStorage.setItem(CLAVE_ALMACEN, idioma);
  } catch {
    // Que no se pueda recordar la preferencia no debe romper la app.
  }
}

interface Textos {
  htmlLang: string;
  kicker: string;
  titulo: string;
  subtitulo: string;
  etiquetaCampo: string;
  placeholder: string;
  botonExcavar: string;
  botonExcavando: string;
  avisoUrl: string;
  cargando: string[];
  cargandoNota: string;
  clasificacion: string;
  estratos: (n: number) => string;
  selloExcavado: string;
  selloArchivo: string;
  abrirExpediente: string;
  excavarOtro: string;
  notaCaducidad: (plazo: string) => string;
  reintentar: string;
  errores: Record<CodigoError, string>;
  errorSinConfigurar: string;
  errorTimeout: string;
  errorRed: string;
  errorIlegible: string;
  errorGenerico: string;
  errorServicio: (status: number) => string;
  pieModelo: string;
  pieArchivo: string;
  cambiarIdioma: string;
}

export const TEXTOS: Record<Idioma, Textos> = {
  es: {
    htmlLang: "es",
    kicker: "Codebase Archaeologist",
    titulo: "El historial de un repositorio, contado como se merece.",
    subtitulo:
      "Pega la URL de cualquier repositorio público de GitHub. Se leen sus últimos commits y su README, y se redacta con ellos una crónica de cómo llegó ese código a ser lo que es.",
    etiquetaCampo: "Sujeto de la excavación",
    placeholder: "https://github.com/psf/requests",
    botonExcavar: "Excavar",
    botonExcavando: "Excavando…",
    avisoUrl: "Necesito una URL de github.com con la forma owner/repo.",
    cargando: [
      "Excavando el historial…",
      "Consultando los archivos…",
      "Datando los estratos de commits…",
      "Identificando a los protagonistas…",
      "Redactando el expediente…",
    ],
    cargandoNota: "Esto suele tardar entre 10 y 20 segundos.",
    clasificacion: "Expediente de arqueología de software",
    estratos: (n) => `${n} estratos examinados`,
    selloExcavado: "Excavado",
    selloArchivo: "De archivo",
    abrirExpediente: "Abrir expediente completo",
    excavarOtro: "Excavar otro repositorio",
    notaCaducidad: (plazo) =>
      `El enlace del expediente caduca en ${plazo}. La página que abre es un archivo independiente que puedes compartir mientras siga vigente.`,
    reintentar: "Reintentar",
    errores: {
      url_invalida: "URL no válida",
      repo_no_encontrado: "No hay nada que excavar aquí",
      rate_limit: "Demasiadas excavaciones",
      github_no_responde: "GitHub no contesta",
      narrador_no_responde: "El historiador enmudeció",
      token_invalido: "Problema de configuración del servicio",
      error_interno: "Algo se derrumbó",
      sin_configurar: "Frontend sin configurar",
      red: "No se pudo llegar al servicio",
    },
    errorSinConfigurar:
      "Falta VITE_API_URL. Copia .env.example a .env.local y apúntalo a tu endpoint.",
    errorTimeout: "La excavación tardó demasiado. Prueba con un repositorio más pequeño.",
    errorRed:
      "No se pudo contactar con el servicio. Revisa tu conexión o la configuración de CORS.",
    errorIlegible: "El servicio devolvió una respuesta ilegible.",
    errorGenerico: "Algo salió mal durante la excavación.",
    errorServicio: (status) => `El servicio respondió ${status}.`,
    pieModelo: "Amazon Bedrock · Nova Lite",
    pieArchivo: "Los expedientes se archivan durante 7 días.",
    cambiarIdioma: "Cambiar a inglés",
  },
  en: {
    htmlLang: "en",
    kicker: "Codebase Archaeologist",
    titulo: "A repository's history, told the way it deserves.",
    subtitulo:
      "Paste the URL of any public GitHub repository. Its latest commits and README are read, and from them a chronicle is written of how that code became what it is.",
    etiquetaCampo: "Subject of the excavation",
    placeholder: "https://github.com/psf/requests",
    botonExcavar: "Excavate",
    botonExcavando: "Excavating…",
    avisoUrl: "I need a github.com URL in the form owner/repo.",
    cargando: [
      "Excavating the history…",
      "Consulting the archives…",
      "Dating the commit strata…",
      "Identifying the protagonists…",
      "Drafting the case file…",
    ],
    cargandoNota: "This usually takes between 10 and 20 seconds.",
    clasificacion: "Software archaeology case file",
    estratos: (n) => `${n} strata examined`,
    selloExcavado: "Excavated",
    selloArchivo: "From archive",
    abrirExpediente: "Open full case file",
    excavarOtro: "Excavate another repository",
    notaCaducidad: (plazo) =>
      `The case file link expires in ${plazo}. The page it opens is a standalone file you can share while it remains valid.`,
    reintentar: "Retry",
    errores: {
      url_invalida: "Invalid URL",
      repo_no_encontrado: "Nothing to excavate here",
      rate_limit: "Too many excavations",
      github_no_responde: "GitHub isn't answering",
      narrador_no_responde: "The historian fell silent",
      token_invalido: "Service configuration problem",
      error_interno: "Something collapsed",
      sin_configurar: "Frontend not configured",
      red: "Couldn't reach the service",
    },
    errorSinConfigurar:
      "VITE_API_URL is missing. Copy .env.example to .env.local and point it at your endpoint.",
    errorTimeout: "The excavation took too long. Try a smaller repository.",
    errorRed: "Couldn't contact the service. Check your connection or the CORS configuration.",
    errorIlegible: "The service returned an unreadable response.",
    errorGenerico: "Something went wrong during the excavation.",
    errorServicio: (status) => `The service responded ${status}.`,
    pieModelo: "Amazon Bedrock · Nova Lite",
    pieArchivo: "Case files are archived for 7 days.",
    cambiarIdioma: "Switch to Spanish",
  },
};
