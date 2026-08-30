import { useState } from "react";
import { pareceRepoGitHub } from "../api";
import { TEXTOS, type Idioma } from "../i18n";

interface Props {
  cargando: boolean;
  idioma: Idioma;
  onSubmit: (url: string) => void;
}

export function RepoForm({ cargando, idioma, onSubmit }: Props) {
  const [valor, setValor] = useState("");
  const [aviso, setAviso] = useState(false);
  const t = TEXTOS[idioma];

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (cargando) return;

    if (!pareceRepoGitHub(valor)) {
      setAviso(true);
      return;
    }
    setAviso(false);
    onSubmit(valor);
  }

  return (
    <form className="formulario" onSubmit={enviar} noValidate>
      <label className="etiqueta" htmlFor="repo">
        {t.etiquetaCampo}
      </label>
      <div className="fila">
        <input
          id="repo"
          className="entrada"
          type="text"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          placeholder={t.placeholder}
          value={valor}
          disabled={cargando}
          aria-invalid={aviso}
          aria-describedby={aviso ? "aviso-form" : undefined}
          onChange={(e) => {
            setValor(e.target.value);
            if (aviso) setAviso(false);
          }}
        />
        <button className="boton" type="submit" disabled={cargando || valor.trim() === ""}>
          {cargando ? t.botonExcavando : t.botonExcavar}
        </button>
      </div>
      {/* El aviso se guarda como booleano, no como texto: así se traduce solo
          cuando el usuario cambia de idioma con el aviso en pantalla. */}
      {aviso && (
        <p className="aviso" id="aviso-form" role="alert">
          {t.avisoUrl}
        </p>
      )}
    </form>
  );
}
