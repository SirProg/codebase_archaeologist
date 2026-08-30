import { useState } from "react";
import { pareceRepoGitHub } from "../api";

interface Props {
  cargando: boolean;
  onSubmit: (url: string) => void;
}

export function RepoForm({ cargando, onSubmit }: Props) {
  const [valor, setValor] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (cargando) return;

    if (!pareceRepoGitHub(valor)) {
      setAviso("Necesito una URL de github.com con la forma owner/repo.");
      return;
    }
    setAviso(null);
    onSubmit(valor);
  }

  return (
    <form className="formulario" onSubmit={enviar} noValidate>
      <label className="etiqueta" htmlFor="repo">
        Sujeto de la excavación
      </label>
      <div className="fila">
        <input
          id="repo"
          className="entrada"
          type="text"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          placeholder="https://github.com/psf/requests"
          value={valor}
          disabled={cargando}
          aria-invalid={aviso !== null}
          aria-describedby={aviso ? "aviso-form" : undefined}
          onChange={(e) => {
            setValor(e.target.value);
            if (aviso) setAviso(null);
          }}
        />
        <button className="boton" type="submit" disabled={cargando || valor.trim() === ""}>
          {cargando ? "Excavando…" : "Excavar"}
        </button>
      </div>
      {aviso && (
        <p className="aviso" id="aviso-form" role="alert">
          {aviso}
        </p>
      )}
    </form>
  );
}
