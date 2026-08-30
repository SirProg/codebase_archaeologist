import { useEffect, useState } from "react";

/* Son 10-20 s de espera. Sin feedback el usuario asume que la app se rompió. */
const MENSAJES = [
  "Excavando el historial…",
  "Consultando los archivos…",
  "Datando los estratos de commits…",
  "Identificando a los protagonistas…",
  "Redactando el expediente…",
];

export function LoadingState() {
  const [i, setI] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      // Se detiene en el último mensaje en vez de dar vueltas: un ciclo que
      // se repite delata que nadie sabe cuánto falta.
      setI((n) => Math.min(n + 1, MENSAJES.length - 1));
    }, 3500);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="cargando" role="status" aria-live="polite">
      <div className="pala" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="cargando-texto">{MENSAJES[i]}</p>
      <p className="cargando-nota">Esto suele tardar entre 10 y 20 segundos.</p>
    </div>
  );
}
