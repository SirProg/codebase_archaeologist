[English](./README.md) | [Español](./README.es.md)

# 🕵️ Codebase Archaeologist

> Un agente autónomo que lee la historia de un repositorio de GitHub y escribe un relato épico sobre cómo evolucionó ese código.

Le pasas la URL de cualquier repositorio público. El agente recupera los últimos commits y el README, se los entrega a Amazon Nova con la instrucción de actuar como un historiador dramático, y te devuelve el relato — renderizado en la app y archivado como expediente HTML independiente en S3.

---

## El problema que resuelve

Leer un repositorio ajeno es aburrido y desorientador. El historial de commits contiene una narrativa real — decisiones, refactors de pánico, features abandonadas — pero está enterrada en mensajes de una línea. Este agente la desentierra y la convierte en algo que da ganas de leer.

---

## Arquitectura

```
Frontend (React + Vite en Vercel)
  │
  │  POST /excavate { "repo_url": "https://github.com/owner/repo" }
  ▼
API Gateway (HTTP API)          CORS restringido al dominio de Vercel
  │
  ▼
AWS Lambda  ──────► SSM Parameter Store   (token de GitHub)
  │  │
  │  ├──────────► GitHub REST API         (commits + README)
  │  │
  │  ├──────────► Amazon Bedrock / Nova   (generación del relato)
  │  │
  │  └──────────► Amazon S3               (expediente HTML + Markdown)
  │
  ▼
{ "url": "...prefirmada...", "narrativa": "# ...", "repo": "owner/repo" }
  │
  ▼
La SPA renderiza el Markdown y enlaza al expediente archivado.
```

### Componentes

| Servicio | Rol |
|---|---|
| **Vercel** | Aloja el frontend de React. Gratis, independiente del stack de AWS, y le da a CORS un origen conocido que permitir. |
| **API Gateway (HTTP API)** | Endpoint público `POST /excavate`. Más barato y simple que REST API. |
| **AWS Lambda** | Toda la lógica del agente: parseo de URL, llamadas a GitHub, prompt a Bedrock, render de HTML, subida a S3. |
| **Amazon Bedrock (Nova Lite)** | Genera el relato histórico a partir de los commits. |
| **Amazon S3** | Archiva cada expediente como HTML estático, más el Markdown para la cache. |
| **SSM Parameter Store** | Guarda el Personal Access Token de GitHub como SecureString. |

---

## Estructura del repositorio

```
codebase-archaeologist/
├── README.md
├── README.es.md
├── CONFIGURACION.md              # Setup de cuentas, permisos y entorno
├── CONFIGURATION.md              # (English)
├── FASES.md                      # Plan de desarrollo, fase por fase
├── PHASES.md                     # (English)
├── .gitignore
│
├── backend/                      # Todo lo que corre en AWS
│   ├── template.yaml             # Infraestructura como código (AWS SAM)
│   ├── requirements-dev.txt      # Dependencias para el script local
│   ├── events/test.json          # Evento de ejemplo para `sam local invoke`
│   ├── src/
│   │   ├── app.py                # lambda_handler — punto de entrada
│   │   ├── excavacion.py         # El flujo completo, compartido con el script local
│   │   ├── github_client.py      # Parseo de URL + cliente de la API de GitHub
│   │   ├── narrator.py           # Prompt y llamada a Bedrock
│   │   ├── renderer.py           # Markdown → HTML con plantilla
│   │   ├── storage.py            # Subida a S3, URL prefirmada y cache
│   │   ├── errors.py             # Errores tipados → códigos HTTP
│   │   ├── template.html         # Plantilla del expediente
│   │   └── requirements.txt      # Dependencias de la Lambda
│   └── scripts/
│       └── local_run.py          # Ejecuta el flujo completo sin AWS desplegado
│
└── frontend/                     # React + Vite + TypeScript, desplegado en Vercel
    ├── vercel.json
    ├── .env.example              # VITE_API_URL
    └── src/
        ├── App.tsx               # idle → loading → success / error
        ├── api.ts                # fetch y traducción de códigos HTTP a errores
        ├── types.ts              # Contrato compartido con la Lambda
        ├── styles.css
        └── components/           # RepoForm · LoadingState · Expediente · ErrorBanner
```

---

## Quickstart

Requisitos completos en [`CONFIGURACION.md`](./CONFIGURACION.md). En resumen:

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 1. Probar el flujo entero sin desplegar nada
export GITHUB_TOKEN="ghp_..."
python scripts/local_run.py https://github.com/psf/requests --abrir

# 2. Desplegar
sam build
sam deploy --guided
```

El despliegue te devuelve la URL del endpoint en el output `ApiUrl`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local        # apunta VITE_API_URL al output ApiUrl
npm run dev                       # http://localhost:5173
```

Para desplegar: importa el repo en Vercel, pon **Root Directory** en `frontend`, añade `VITE_API_URL`, y redespliega el backend con tu dominio de Vercel en `AllowedOrigins`. Ver [`CONFIGURACION.md`](./CONFIGURACION.md#9-despliegue-del-frontend-en-vercel).

---

## Uso

El frontend es la vía prevista, pero el endpoint se sostiene solo:

```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/excavate \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/torvalds/linux"}'
```

Respuesta:

```json
{
  "url": "https://codebase-archaeologist-xxxx.s3.amazonaws.com/expedientes/torvalds-linux-20260829.html?X-Amz-Algorithm=...",
  "repo": "torvalds/linux",
  "narrativa": "# La Crónica del Monolito\n\n...",
  "commits_analizados": 10,
  "expira_en": "7 días",
  "cache": false
}
```

Los errores siempre vienen con la misma forma, nunca como un stack trace crudo:

```json
{ "error": "repo_no_encontrado", "mensaje": "El repositorio no existe o es privado." }
```

| Código | HTTP | Cuándo |
|---|---|---|
| `url_invalida` | 400 | No es una URL de GitHub, está malformada, vacía o es demasiado larga |
| `repo_no_encontrado` | 404 | El repositorio no existe o es privado |
| `rate_limit` | 429 | Se agotó el límite de peticiones de GitHub |
| `github_no_responde` | 502 | GitHub dio timeout o falló |
| `narrador_no_responde` | 502 | Bedrock falló o no devolvió nada |
| `token_invalido` | 500 | El PAT caducó — es un fallo de configuración del servicio, no del usuario |

---

## Decisiones de diseño

**Una SPA de React en Vercel en lugar de un HTML suelto en S3.** El relato se devuelve como Markdown y se renderiza en la app, así que el resultado aparece sin saltar a otra pestaña — y los 10–20 segundos de espera tienen un estado de carga real en vez de un botón congelado. El hosting es gratis y totalmente separado del stack de AWS, y como el frontend vive en un dominio conocido, CORS permite un solo origen en lugar de `*`. El expediente prefirmado de S3 sigue existiendo como el artefacto archivado y compartible.

**Nova Lite en lugar de Nova Pro.** API Gateway corta las conexiones a los 29 segundos. Nova Lite genera 1200 tokens en un rango cómodo dentro de ese límite; Nova Pro es mejor escritor pero se acerca peligrosamente al timeout. Si prefieres calidad sobre latencia, la alternativa es una Lambda Function URL, que soporta hasta 15 minutos.

**URLs prefirmadas en lugar de bucket público.** S3 bloquea el acceso público por defecto y desactivarlo requiere tocar cuatro configuraciones. Una URL prefirmada de 7 días resuelve el caso de uso sin abrir el bucket. Si quieres links permanentes, la vía correcta es CloudFront con Origin Access Control.

**Converse API en lugar de `invoke_model`.** `converse()` unifica el formato de request y response entre modelos de Bedrock. Cambiar de Nova a Claude o a Llama es cambiar un string, no reescribir el parseo.

**Solo 10 commits.** No es una limitación técnica sino narrativa: con más contexto el modelo tiende a resumir en lugar de dramatizar. Diez commits dan suficiente material para una historia sin diluir el tono.

**El flujo vive en `excavacion.py`, no en el handler.** `local_run.py` y `app.py` llaman a la misma función, así que el script local ejercita exactamente el camino que corre en producción. El handler solo se ocupa de HTTP, la cache y los secretos.

---

## Costos

Con el uso de un demo, el proyecto cuesta esencialmente nada:

| Servicio | Costo aproximado |
|---|---|
| Bedrock / Nova Lite | Fracciones de centavo por ejecución |
| Lambda | Cubierto por el free tier |
| S3 | Cubierto por el free tier |
| API Gateway | Cubierto por el free tier (primer año) |
| SSM Parameter Store | Gratis (parámetros estándar) |
| Vercel | Gratis (plan Hobby) |

⚠️ El riesgo real no es el costo por ejecución, sino dejar un endpoint público sin límites. El throttling ya está puesto en `template.yaml`; añade además una alarma de facturación. Ver [`CONFIGURACION.md`](./CONFIGURACION.md#10-protección-contra-abuso).

---

## Roadmap

- [x] Cache en S3: si el repo ya fue excavado hoy, devolver el expediente existente
- [ ] Streaming de la respuesta con Lambda Function URL
- [ ] Análisis de contribuidores ("los personajes de esta historia")
- [ ] Detección de "momentos dramáticos": commits con `revert`, `hotfix`, `WIP`, `fix fix fix`
- [ ] Múltiples voces narrativas: noir, épica nórdica, documental de naturaleza
- [ ] CloudFront + dominio propio para links permanentes

---

## Documentación

- [`CONFIGURACION.md`](./CONFIGURACION.md) — Cuentas, permisos, IAM, variables de entorno, Vercel y troubleshooting
- [`FASES.md`](./FASES.md) — Plan de desarrollo dividido en fases con criterios de aceptación
