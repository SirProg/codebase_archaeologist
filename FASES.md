[English](./PHASES.md) | [Español](./FASES.md)

# 🗺️ Plan de desarrollo por fases

Estimación total: **9 a 13 horas**, repartibles en un fin de semana.

El principio que ordena todo este plan: **no despliegues nada hasta que la lógica funcione en tu máquina.** Depurar un prompt dentro de una Lambda es lento y frustrante; depurarlo en un script local toma segundos. Las fases 0 a 2 no tocan AWS más allá de Bedrock.

| Fase | Qué produce | Tiempo |
|---|---|---|
| 0 | Entorno listo, accesos concedidos | 30–45 min |
| 1 | Script local que imprime el relato en consola | 2–3 h |
| 2 | HTML renderizado y guardado en disco | 1–1.5 h |
| 3 | Lambda funcionando en local con SAM | 1 h |
| 4 | Infraestructura desplegada y endpoint vivo | 1–1.5 h |
| 5 | Frontend React desplegado en Vercel | ~2 h |
| 6 | Robustez, límites y limpieza | 1–2 h |
| 7 | Demo y documentación | 1 h |

---

## Fase 0 — Preparación

**Objetivo:** eliminar todos los bloqueos que dependen de terceros antes de escribir una línea de código.

### Tareas

1. Solicitar model access de Nova en Bedrock (us-east-1).
2. Crear el PAT de GitHub y guardarlo en SSM.
3. Instalar y verificar Python, AWS CLI y SAM CLI.
4. Crear el repositorio con la estructura `backend/` + `frontend/` y el `.gitignore`.
5. Crear el virtualenv en `backend/` e instalar dependencias.
6. Crear la cuenta de Vercel (no hace falta hasta la Fase 5, pero es gratis y quita un bloqueo).

Detalle completo en [`CONFIGURACION.md`](./CONFIGURACION.md).

### Criterio de aceptación

```bash
aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"hola"}]}]'
```

devuelve una respuesta del modelo. Si esto no funciona, **no avances**: todo lo demás depende de ello.

---

## Fase 1 — El script local

**Objetivo:** un solo archivo que reciba una URL por argumento y escupa el relato en la consola. Aquí vive el 70% del valor del proyecto.

### 1.1 Parsear la URL

Escribe una función que extraiga `owner` y `repo`. Los casos que debe soportar:

```
https://github.com/psf/requests
https://github.com/psf/requests/
https://github.com/psf/requests.git
git@github.com:psf/requests.git
https://github.com/psf/requests/tree/main/src
github.com/psf/requests
```

Y rechazar limpiamente lo que no sea GitHub. Una expresión regular sobre el path resuelve casi todo; recuerda quitar el sufijo `.git` y descartar segmentos posteriores al nombre del repo.

### 1.2 Cliente de GitHub

Dos llamadas:

```
GET https://api.github.com/repos/{owner}/{repo}/commits?per_page=10
GET https://api.github.com/repos/{owner}/{repo}/readme
GET https://api.github.com/repos/{owner}/{repo}          ← metadatos, opcional pero útil
```

Headers en todas:

```python
{
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
}
```

Trampas concretas:

- **El README viene en base64.** El endpoint devuelve un JSON con el campo `content` codificado; hay que decodificarlo con `base64.b64decode(...).decode("utf-8")`.
- **Un repo puede no tener README.** El endpoint responde `404`. Es un caso válido, no un error: continúa con un README vacío.
- **Los mensajes de commit pueden ser larguísimos.** Muchos incluyen el cuerpo entero además del título. Quédate con la primera línea de `commit.message`.
- **`commit.author` puede ser `null`** cuando el autor no tiene cuenta de GitHub vinculada. Usa `commit.commit.author.name` como fallback.

Extrae por cada commit: SHA corto, autor, fecha y primera línea del mensaje.

### 1.3 El prompt

Esta es la parte creativa y donde más vas a iterar. Estructura recomendada:

**System prompt** — define la voz y las restricciones:

```
Eres un historiador dramático especializado en arqueología de software.
Escribes crónicas épicas sobre la evolución de proyectos de código,
tratando cada commit como un acontecimiento histórico y a cada
desarrollador como un personaje con motivaciones.

Reglas:
- Escribe en español, en Markdown.
- Estructura: un título épico, una introducción que sitúe el proyecto,
  3 o 4 secciones narrativas, y un cierre que mire al futuro.
- Menciona SHAs y autores reales; nunca inventes commits ni personas.
- El tono es dramático pero el contenido es factual.
- Máximo 800 palabras.
```

**User message** — los datos crudos, claramente delimitados:

```
<repositorio>
Nombre: {owner}/{repo}
Descripción: {description}
Lenguaje: {language}
Estrellas: {stars}
</repositorio>

<readme>
{readme_truncado}
</readme>

<commits>
{lista formateada de los 10 commits}
</commits>
```

Corta el README a unos 4000 caracteres. Muchos superan los 20.000 y el exceso solo diluye la atención del modelo sobre los commits, que son la materia prima real de la historia.

**Etiqueta el orden de los commits.** GitHub los devuelve del más nuevo al más viejo. Si se los pasas en ese orden sin decirlo, el modelo los lee de arriba abajo como si fueran cronológicos y llama "primer commit" al más reciente. Inviértelos a orden cronológico y di explícitamente que son los commits *más recientes*, no el origen del proyecto, y que la fecha de creación del repositorio es un dato distinto de la fecha de cualquier commit.

### 1.4 Llamada a Bedrock

```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

resp = client.converse(
    modelId="amazon.nova-lite-v1:0",
    system=[{"text": SYSTEM_PROMPT}],
    messages=[{"role": "user", "content": [{"text": user_prompt}]}],
    inferenceConfig={
        "maxTokens": 1500,
        "temperature": 0.8,
        "topP": 0.9,
    },
)

relato = resp["output"]["message"]["content"][0]["text"]
```

`temperature` alta (0.7–0.9) porque quieres prosa creativa, no precisión factual. El `system` va en su propio parámetro, no dentro de `messages`.

### 1.5 Iterar el prompt

Prueba con al menos cinco repositorios de perfiles distintos:

- Uno enorme y veterano (`torvalds/linux`)
- Uno mediano y ordenado (`psf/requests`)
- Uno recién creado con tres commits
- Uno sin README
- Uno con mensajes de commit inútiles (`update`, `fix`, `asdf`)

El último caso es el que rompe los prompts ingenuos. Si el modelo no tiene material, tiende a inventar. Añade una instrucción explícita para ese escenario: que reconozca la escasez de información y la convierta en parte de la narrativa ("los registros de esta era son fragmentarios...") en lugar de fabricar hechos.

### Criterio de aceptación

Desde `backend/`, `python scripts/local_run.py https://github.com/psf/requests` imprime un relato coherente, en Markdown, que menciona commits reales del repositorio.

---

## Fase 2 — Render a HTML

**Objetivo:** convertir el Markdown en una página que dé gusto abrir.

### Tareas

1. Convertir Markdown a HTML:

```python
import markdown
cuerpo = markdown.markdown(relato, extensions=["extra", "nl2br"])
```

2. Crear `backend/src/template.html` con CSS embebido — un solo archivo, sin dependencias externas, sin CDNs. Placeholders para el título, el nombre del repo, el cuerpo y la fecha de generación.

3. Estética sugerida: papel envejecido, tipografía serif para el cuerpo, monoespaciada para los SHAs. Ancho de línea de 65–75 caracteres. Es un expediente de detective, no un dashboard.

4. Escribir el resultado a disco y abrirlo en el navegador.

### Criterio de aceptación

`salida_local.html` se abre en el navegador y se ve deliberadamente diseñado. Este archivo es tu material de demo — inviértele tiempo, porque es lo único que la gente va a ver.

---

## Fase 3 — Envolver en Lambda

**Objetivo:** la misma lógica, ahora como función, probada localmente con SAM.

### Tareas

1. Reorganizar el script en los módulos de `backend/src/`: `github_client.py`, `narrator.py`, `renderer.py`, `storage.py`.
2. Escribir `app.py` con el handler:

```python
def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    repo_url = body.get("repo_url")
    ...
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"url": url, "repo": f"{owner}/{repo}"}),
    }
```

3. Implementar `storage.py`: subida a S3 con `ContentType` correcto y generación de URL prefirmada con `generate_presigned_url("get_object", ...)`.

4. Leer el token desde SSM con `with_decryption=True`, y cachearlo en una variable global fuera del handler para reutilizarlo entre invocaciones tibias.

5. Escribir `backend/template.yaml` con la función, el bucket, la API y las políticas IAM (todo detallado en `CONFIGURACION.md`).

6. Crear `backend/events/test.json` y probar:

```bash
cd backend
sam build
sam local invoke ArchaeologistFunction -e events/test.json
```

### Trampas

- `sam local invoke` usa tus credenciales locales, no el rol IAM de la función. Que funcione en local **no garantiza** que los permisos estén bien. Eso se valida en la Fase 4.
- El body del evento de API Gateway es un string, no un objeto. Siempre `json.loads`.
- La única ruta escribible en Lambda es `/tmp`. Si generas archivos temporales, va ahí.

### Criterio de aceptación

`sam local invoke` devuelve un JSON con una URL de S3, y esa URL abre el expediente.

---

## Fase 4 — Despliegue

**Objetivo:** endpoint público funcionando.

### Tareas

```bash
cd backend
sam build
sam deploy --guided
```

En el asistente: nombre del stack `codebase-archaeologist`, región `us-east-1`, y acepta la creación de roles IAM. Guarda la configuración en `samconfig.toml`.

Anota el output **`ApiUrl`**: es lo que va en `VITE_API_URL` en la Fase 5.

Prueba el endpoint desplegado:

```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/excavate \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/psf/requests"}'
```

Los redespliegues posteriores son solo `sam build && sam deploy`.

### Trampas

- **Aquí es donde aparecen los errores de IAM** que `sam local` ocultaba. `sam logs --tail` es tu mejor amigo.
- **El fallo más probable del primer deploy es `iam:CreateRole`.** Tener permisos de lectura sobre IAM no implica poder crear el rol de ejecución, y las comprobaciones previas de la Fase 0 no lo detectan. Si tu usuario está acotado, pide la política de `CONFIGURACION.md` §3 antes de intentarlo.
- Si el deploy falla, el stack queda en `ROLLBACK_COMPLETE` y **no se puede reintentar sin borrarlo**: `aws cloudformation delete-stack --stack-name codebase-archaeologist`.
- Mide el tiempo real de respuesta. Si se acerca a 29 segundos, baja `maxTokens` o cambia a Lambda Function URL antes de que sea un problema en la demo.
- Cold start: la primera invocación tras un rato de inactividad tarda más. En una demo en vivo, haz una llamada de calentamiento antes de empezar.

### Criterio de aceptación

Un `curl` desde una máquina cualquiera devuelve una URL que abre un expediente.

---

## Fase 5 — Frontend (React + Vite + TypeScript, en Vercel)

**Objetivo:** que la demo no sea un `curl`, y que el relato se lea en la propia app.

### 5.1 Scaffold

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install react-markdown remark-gfm
```

Nada más. Sin librería de UI ni de estado: son tres estados en una pantalla, y `useState` sobra para eso.

### 5.2 El contrato con el backend

La Lambda devuelve el Markdown además del enlace de S3, y el frontend lo renderiza:

```json
{
  "url": "https://...s3...?X-Amz-...",
  "repo": "owner/repo",
  "narrativa": "# Título épico\n\n...",
  "commits_analizados": 10,
  "expira_en": "7 días",
  "cache": false
}
```

Declara ese contrato en `src/types.ts` y no lo dupliques en ningún otro sitio. Si cambia `app.py`, cambia ahí.

### 5.3 Estructura

```
src/
├── App.tsx          # idle → loading → success / error
├── api.ts           # fetch, timeout y traducción de códigos HTTP a errores
├── types.ts
├── styles.css
└── components/
    ├── RepoForm.tsx
    ├── LoadingState.tsx
    ├── Expediente.tsx
    └── ErrorBanner.tsx
```

### 5.4 Lo que de verdad importa

**El estado de carga.** Son 10–20 segundos de espera. Sin feedback visual el usuario asume que se rompió. Mensajes rotativos cada ~3 s: "excavando el historial...", "consultando los archivos...", "redactando el expediente...". Deja de rotar en el último en vez de dar vueltas: un ciclo que se repite delata que nadie sabe cuánto falta.

**Errores distinguibles.** El backend ya manda `{error, mensaje}` tipados; el frontend solo tiene que ponerles un título y decidir si ofrecer «Reintentar». Un repo inexistente no se arregla reintentando; un fallo de Bedrock sí.

**Validación en cliente antes del fetch.** Una URL que obviamente no es de GitHub no merece un viaje de ida y vuelta ni una invocación de Lambda.

**El timeout del `fetch`.** Con `AbortController`, por encima del tiempo real de la excavación (45 s va bien). Sin él, una petición colgada deja la app en «cargando» para siempre.

**La estética.** Reutiliza la paleta y la tipografía de `backend/src/template.html`. Que el expediente se vea igual dentro de la app y en la página de S3 es lo que hace que parezca un producto y no dos cosas pegadas.

### 5.5 Desplegar en Vercel

Import del repo → **Root Directory `frontend`** → preset Vite → variable `VITE_API_URL`. Después, redespliega el backend con el dominio de Vercel en `AllowedOrigins`. Detalle completo en [`CONFIGURACION.md`](./CONFIGURACION.md#9-despliegue-del-frontend-en-vercel).

### Trampas

- Las variables `VITE_*` se hornean en tiempo de build. Cambiarlas en el dashboard **no** afecta a un deploy ya hecho: hay que redesplegar.
- Si olvidas el Root Directory, Vercel busca `package.json` en la raíz del repo y el build falla sin explicar por qué.
- Un error de CORS en la consola del navegador casi nunca es un bug del frontend: es que el origen no está en `AllowedOrigins`.

### Criterio de aceptación

Alguien que no conoce el proyecto puede pegar una URL en el dominio de Vercel y obtener su expediente sin que le expliques nada, viendo en todo momento que algo está pasando.

---

## Fase 6 — Robustez

**Objetivo:** que no se caiga durante la demo.

### Tareas

- **Validación de entrada:** rechazar dominios que no sean GitHub, limitar longitud, validar formato `owner/repo` antes de cualquier llamada externa.
- **Errores tipados:** repo no encontrado → 404 con mensaje claro; rate limit → 429; fallo de Bedrock → 502; PAT caducado → 500 con su propio código, para que se distinga de un fallo del usuario. Nunca un stack trace crudo hacia el usuario.
- **Timeouts explícitos** en las llamadas a GitHub (`requests.get(..., timeout=10)`). Sin esto, una petición colgada consume todo el timeout de la Lambda.
- **Cache:** antes de excavar, comprueba si ya existe `expedientes/{owner}-{repo}-{fecha}.html` en S3. Si está, devuélvelo. Guarda también el `.md` junto al HTML: sin él, un acierto de cache no puede devolverle el relato al frontend. Ahorra tokens y hace las demos repetidas instantáneas.
- **Throttling** en API Gateway y **alarma de facturación**.
- **CORS restringido** al dominio de Vercel, no a `"*"`.
- **Logging estructurado:** loguea el repo, la duración y el uso de tokens (viene en `resp["usage"]`). Te sirve para depurar y para presumir métricas.

### Criterio de aceptación

Estos cinco inputs devuelven errores claros en lugar de un 500:

```
https://github.com/esto/no-existe-jamas
https://gitlab.com/algo/otro
no soy una url
""  (vacío)
https://github.com/  (sin repo)
```

---

## Fase 7 — Demo y documentación

**Objetivo:** que el proyecto se entienda en dos minutos.

### Tareas

1. Actualizar los README (`README.md` y `README.es.md`) con la URL real del frontend en Vercel y capturas del expediente generado.
2. Generar 3 o 4 expedientes de repos reconocibles y guardar los links. Son tu mejor argumento.
3. Diagrama de arquitectura. Un diagrama ASCII en el README sirve; uno hecho en draw.io se ve mejor.
4. Video de 2 minutos: problema → demo en vivo → arquitectura → una decisión técnica interesante.
5. Comandos de limpieza documentados: `sam delete --stack-name codebase-archaeologist` desde `backend/`, y borrar el proyecto en Vercel.

### Criterio de aceptación

Alguien que llega al repo entiende qué hace, por qué existe y cómo está construido, sin ejecutar nada.

---

## Cronograma sugerido

**Viernes noche (1 h)** — Fase 0. Solicita el model access y crea el token. Cierra la laptop.

**Sábado mañana (4 h)** — Fases 1 y 2. Es el bloque más largo y el que más concentración pide. Terminas con un HTML bonito en tu disco.

**Sábado tarde (3 h)** — Fases 3 y 4. Al final del sábado tienes un endpoint público funcionando.

**Domingo mañana (4 h)** — Fases 5 y 6.

**Domingo tarde (1 h)** — Fase 7.

---

## Cómo recortar si vas mal de tiempo

En orden de qué sacrificar primero:

1. **Frontend** — despliega solo el backend y demuestra con `curl`. Pierdes la demo bonita, no la funcionalidad.
2. **Cache** — es optimización, no funcionalidad.
3. **API Gateway** — una Lambda Function URL da un endpoint HTTPS con una línea de YAML y además elimina el problema del timeout de 29 s.

Lo que **no** se recorta bajo ninguna circunstancia:

- La calidad del prompt. Es el producto entero.
- El diseño del expediente. Es lo único que la gente va a mirar.
- El manejo de errores en la Fase 6. Una demo que se cae en vivo borra todo lo demás.
