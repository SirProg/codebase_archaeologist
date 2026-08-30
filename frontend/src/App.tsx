import { useEffect, useState } from "react";
import { ExcavacionError, excavar } from "./api";
import { ErrorBanner } from "./components/ErrorBanner";
import { Expediente } from "./components/Expediente";
import { LoadingState } from "./components/LoadingState";
import { RepoForm } from "./components/RepoForm";
import { guardarIdioma, idiomaInicial, TEXTOS, type Idioma } from "./i18n";
import type { ErrorExpediente, ExpedienteResponse } from "./types";

type Estado =
  | { fase: "idle" }
  | { fase: "loading" }
  | { fase: "success"; datos: ExpedienteResponse }
  | { fase: "error"; error: ErrorExpediente };

export default function App() {
  const [idioma, setIdioma] = useState<Idioma>(idiomaInicial);
  const [estado, setEstado] = useState<Estado>({ fase: "idle" });
  const [ultimaUrl, setUltimaUrl] = useState("");
  const t = TEXTOS[idioma];

  // El <html lang> lo lee el navegador para la partición silábica y los
  // lectores de pantalla, así que tiene que seguir al idioma elegido.
  useEffect(() => {
    document.documentElement.lang = t.htmlLang;
    document.title = "Codebase Archaeologist";
  }, [t.htmlLang]);

  async function lanzar(url: string, lang: Idioma = idioma) {
    setUltimaUrl(url);
    setEstado({ fase: "loading" });
    try {
      const datos = await excavar(url, lang);
      setEstado({ fase: "success", datos });
    } catch (err) {
      const error: ErrorExpediente =
        err instanceof ExcavacionError
          ? { codigo: err.codigo, mensaje: err.message }
          : { codigo: "error_interno", mensaje: TEXTOS[lang].errorGenerico };
      setEstado({ fase: "error", error });
    }
  }

  function cambiarIdioma() {
    const nuevo: Idioma = idioma === "es" ? "en" : "es";
    setIdioma(nuevo);
    guardarIdioma(nuevo);

    // Un relato en español bajo una interfaz en inglés queda incoherente, así
    // que se vuelve a excavar. El backend cachea por idioma, de modo que
    // volver al anterior es instantáneo.
    if (estado.fase === "success" && ultimaUrl) {
      void lanzar(ultimaUrl, nuevo);
    }
  }

  return (
    <div className="pagina">
      <header className="cabecera">
        <div className="cabecera-fila">
          <p className="kicker">{t.kicker}</p>
          <button
            className="idioma"
            type="button"
            onClick={cambiarIdioma}
            aria-label={t.cambiarIdioma}
            title={t.cambiarIdioma}
          >
            <span className={idioma === "es" ? "idioma-activo" : ""}>ES</span>
            <span aria-hidden="true">·</span>
            <span className={idioma === "en" ? "idioma-activo" : ""}>EN</span>
          </button>
        </div>
        <h1>{t.titulo}</h1>
        <p className="subtitulo">{t.subtitulo}</p>
      </header>

      {estado.fase !== "success" && (
        <RepoForm cargando={estado.fase === "loading"} idioma={idioma} onSubmit={lanzar} />
      )}

      {estado.fase === "loading" && <LoadingState idioma={idioma} />}

      {estado.fase === "error" && (
        <ErrorBanner
          codigo={estado.error.codigo}
          mensaje={estado.error.mensaje}
          idioma={idioma}
          onReintentar={ultimaUrl ? () => lanzar(ultimaUrl) : undefined}
        />
      )}

      {estado.fase === "success" && (
        <Expediente
          datos={estado.datos}
          idioma={idioma}
          onNuevo={() => setEstado({ fase: "idle" })}
        />
      )}

      <footer className="pie-pagina">
        <span>{t.pieModelo}</span>
        <span>{t.pieArchivo}</span>
      </footer>
    </div>
  );
}
