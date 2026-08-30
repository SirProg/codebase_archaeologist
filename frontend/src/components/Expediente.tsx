import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ExpedienteResponse } from "../types";

interface Props {
  datos: ExpedienteResponse;
  onNuevo: () => void;
}

export function Expediente({ datos, onNuevo }: Props) {
  return (
    <article className="expediente">
      <header className="membrete">
        <div className="clasificacion">
          <span>Expediente de arqueología de software</span>
          <span>{datos.commits_analizados} estratos examinados</span>
        </div>
        <div className="sujeto">{datos.repo}</div>
        <div className="sellos">
          <span className="sello">Excavado</span>
          {datos.cache && <span className="sello sello-tenue">De archivo</span>}
        </div>
      </header>

      <div className="cuerpo">
        <Markdown remarkPlugins={[remarkGfm]}>{datos.narrativa}</Markdown>
      </div>

      <footer className="acciones">
        <a className="boton" href={datos.url} target="_blank" rel="noopener noreferrer">
          Abrir expediente completo
        </a>
        <button className="boton boton-secundario" type="button" onClick={onNuevo}>
          Excavar otro repositorio
        </button>
        <p className="nota">
          El enlace del expediente caduca en {datos.expira_en}. La página que abre es un archivo
          independiente que puedes compartir mientras siga vigente.
        </p>
      </footer>
    </article>
  );
}
