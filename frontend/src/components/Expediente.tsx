import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { TEXTOS, type Idioma } from "../i18n";
import type { ExpedienteResponse } from "../types";

interface Props {
  datos: ExpedienteResponse;
  idioma: Idioma;
  onNuevo: () => void;
}

export function Expediente({ datos, idioma, onNuevo }: Props) {
  const t = TEXTOS[idioma];
  return (
    <article className="expediente">
      <header className="membrete">
        <div className="clasificacion">
          <span>{t.clasificacion}</span>
          <span>{t.estratos(datos.commits_analizados)}</span>
        </div>
        <div className="sujeto">{datos.repo}</div>
        <div className="sellos">
          <span className="sello">{t.selloExcavado}</span>
          {datos.cache && <span className="sello sello-tenue">{t.selloArchivo}</span>}
        </div>
      </header>

      {/* El relato viene del modelo en el idioma pedido; se marca para que
          lectores de pantalla y la partición silábica lo traten bien. */}
      <div className="cuerpo" lang={datos.idioma || idioma}>
        <Markdown remarkPlugins={[remarkGfm]}>{datos.narrativa}</Markdown>
      </div>

      <footer className="acciones">
        <a className="boton" href={datos.url} target="_blank" rel="noopener noreferrer">
          {t.abrirExpediente}
        </a>
        <button className="boton boton-secundario" type="button" onClick={onNuevo}>
          {t.excavarOtro}
        </button>
        <p className="nota">{t.notaCaducidad(datos.expira_en)}</p>
      </footer>
    </article>
  );
}
