import { useState } from "react";
import { ExcavacionError, excavar } from "./api";
import { ErrorBanner } from "./components/ErrorBanner";
import { Expediente } from "./components/Expediente";
import { LoadingState } from "./components/LoadingState";
import { RepoForm } from "./components/RepoForm";
import type { ErrorExpediente, ExpedienteResponse } from "./types";

type Estado =
  | { fase: "idle" }
  | { fase: "loading" }
  | { fase: "success"; datos: ExpedienteResponse }
  | { fase: "error"; error: ErrorExpediente };

export default function App() {
  const [estado, setEstado] = useState<Estado>({ fase: "idle" });
  const [ultimaUrl, setUltimaUrl] = useState("");

  async function lanzar(url: string) {
    setUltimaUrl(url);
    setEstado({ fase: "loading" });
    try {
      const datos = await excavar(url);
      setEstado({ fase: "success", datos });
    } catch (err) {
      const error: ErrorExpediente =
        err instanceof ExcavacionError
          ? { codigo: err.codigo, mensaje: err.message }
          : { codigo: "error_interno", mensaje: "Algo salió mal durante la excavación." };
      setEstado({ fase: "error", error });
    }
  }

  return (
    <div className="pagina">
      <header className="cabecera">
        <p className="kicker">Codebase Archaeologist</p>
        <h1>El historial de un repositorio, contado como se merece.</h1>
        <p className="subtitulo">
          Pega la URL de cualquier repositorio público de GitHub. Se leen sus últimos commits y su
          README, y se redacta con ellos una crónica de cómo llegó ese código a ser lo que es.
        </p>
      </header>

      {estado.fase !== "success" && (
        <RepoForm cargando={estado.fase === "loading"} onSubmit={lanzar} />
      )}

      {estado.fase === "loading" && <LoadingState />}

      {estado.fase === "error" && (
        <ErrorBanner
          codigo={estado.error.codigo}
          mensaje={estado.error.mensaje}
          onReintentar={ultimaUrl ? () => lanzar(ultimaUrl) : undefined}
        />
      )}

      {estado.fase === "success" && (
        <Expediente datos={estado.datos} onNuevo={() => setEstado({ fase: "idle" })} />
      )}

      <footer className="pie-pagina">
        <span>Amazon Bedrock · Nova Lite</span>
        <span>Los expedientes se archivan durante 7 días.</span>
      </footer>
    </div>
  );
}
