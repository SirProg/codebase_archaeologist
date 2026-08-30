import type { CodigoError } from "../types";

interface Props {
  codigo: CodigoError;
  mensaje: string;
  onReintentar?: () => void;
}

/* El backend ya manda un mensaje legible; el título le da contexto de un vistazo. */
const TITULOS: Record<CodigoError, string> = {
  url_invalida: "URL no válida",
  repo_no_encontrado: "No hay nada que excavar aquí",
  rate_limit: "Demasiadas excavaciones",
  github_no_responde: "GitHub no contesta",
  narrador_no_responde: "El historiador enmudeció",
  token_invalido: "Problema de configuración del servicio",
  error_interno: "Algo se derrumbó",
  sin_configurar: "Frontend sin configurar",
  red: "No se pudo llegar al servicio",
};

/* Solo tiene sentido reintentar lo que puede salir distinto la próxima vez. */
const REINTENTABLES: CodigoError[] = [
  "narrador_no_responde",
  "github_no_responde",
  "error_interno",
  "red",
];

export function ErrorBanner({ codigo, mensaje, onReintentar }: Props) {
  return (
    <div className="error" role="alert">
      <p className="error-titulo">{TITULOS[codigo] ?? "Error"}</p>
      <p className="error-mensaje">{mensaje}</p>
      {onReintentar && REINTENTABLES.includes(codigo) && (
        <button className="boton boton-secundario" type="button" onClick={onReintentar}>
          Reintentar
        </button>
      )}
    </div>
  );
}
