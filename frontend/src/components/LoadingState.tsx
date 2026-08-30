import { useEffect, useState } from "react";
import { TEXTOS, type Idioma } from "../i18n";

interface Props {
  idioma: Idioma;
}

/* Son 10-20 s de espera. Sin feedback el usuario asume que la app se rompió. */
export function LoadingState({ idioma }: Props) {
  const [i, setI] = useState(0);
  const mensajes = TEXTOS[idioma].cargando;

  useEffect(() => {
    const id = setInterval(() => {
      // Se detiene en el último mensaje en vez de dar vueltas: un ciclo que
      // se repite delata que nadie sabe cuánto falta.
      setI((n) => Math.min(n + 1, mensajes.length - 1));
    }, 3500);
    return () => clearInterval(id);
  }, [mensajes.length]);

  return (
    <div className="cargando" role="status" aria-live="polite">
      <div className="pala" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="cargando-texto">{mensajes[i]}</p>
      <p className="cargando-nota">{TEXTOS[idioma].cargandoNota}</p>
    </div>
  );
}
