import { TEXTOS, type Idioma } from "../i18n";
import type { CodigoError } from "../types";

interface Props {
  codigo: CodigoError;
  mensaje: string;
  idioma: Idioma;
  onReintentar?: () => void;
}

/* Solo tiene sentido reintentar lo que puede salir distinto la próxima vez. */
const REINTENTABLES: CodigoError[] = [
  "narrador_no_responde",
  "github_no_responde",
  "error_interno",
  "red",
];

export function ErrorBanner({ codigo, mensaje, idioma, onReintentar }: Props) {
  const t = TEXTOS[idioma];
  return (
    <div className="error" role="alert">
      {/* El título lo pone el frontend; el detalle viene del backend, que ya
          lo devuelve en el idioma que se le pidió. */}
      <p className="error-titulo">{t.errores[codigo] ?? t.errores.error_interno}</p>
      <p className="error-mensaje">{mensaje}</p>
      {onReintentar && REINTENTABLES.includes(codigo) && (
        <button className="boton boton-secundario" type="button" onClick={onReintentar}>
          {t.reintentar}
        </button>
      )}
    </div>
  );
}
