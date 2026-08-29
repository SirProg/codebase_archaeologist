[English](./README.en.md) | [Español](./README.es.md)

# 🕵️ Codebase Archaeologist

> Un agente autónomo que lee la historia de un repositorio de GitHub y escribe un relato épico sobre cómo evolucionó ese código.

Le pasas la URL de cualquier repositorio público. El agente recupera los últimos commits y el README, se los entrega a Amazon Nova con la instrucción de actuar como un historiador dramático, y publica el resultado como una página HTML estática en S3. Te devuelve el link.

---

## El problema que resuelve

Leer un repositorio ajeno es aburrido y desorientador. El historial de commits contiene una narrativa real — decisiones, refactors de pánico, features abandonadas — pero está enterrada en mensajes de una línea. Este agente la desentierra y la convierte en algo que da ganas de leer.

---

## Arquitectura

```
Usuario
  │
  │  POST { "repo_url": "https://github.com/owner/repo" }
  ▼
API Gateway (HTTP API)
  │
  ▼
AWS Lambda  ──────► SSM Parameter Store   (token de GitHub)
  │  │
  │  ├──────────► GitHub REST API         (commits + README)
  │  │
  │  ├──────────► Amazon Bedrock / Nova   (generación del relato)
  │  │
  │  └──────────► Amazon S3               (HTML estático)
  │
  ▼
{ "url": "https://bucket.s3.amazonaws.com/...html?X-Amz-..." }
```

### Componentes

| Servicio | Rol |
|---|---|
| **API Gateway (HTTP API)** | Endpoint público `POST /excavate`. Más barato y simple que REST API. |
| **AWS Lambda** | Toda la lógica del agente: parseo de URL, llamadas a GitHub, prompt a Bedrock, render de HTML, subida a S3. |
| **Amazon Bedrock (Nova Lite)** | Genera el relato histórico a partir de los commits. |
| **Amazon S3** | Aloja los expedientes generados como HTML estático. |
| **SSM Parameter Store** | Guarda el Personal Access Token de GitHub como SecureString. |

---

## Estructura del repositorio

```
codebase-archaeologist/
├── README.md
├── CONFIGURACION.md          # Setup de cuentas, permisos y entorno
├── FASES.md                  # Plan de desarrollo por fases
├── template.yaml             # Infraestructura como código (AWS SAM)
├── samconfig.toml            # Parámetros de despliegue (generado por sam deploy --guided)
├── .gitignore
├── requirements-dev.txt      # Dependencias para el script local
│
├── src/
│   ├── app.py                # lambda_handler — punto de entrada
│   ├── github_client.py      # Cliente de la API de GitHub
│   ├── narrator.py           # Prompt y llamada a Bedrock
│   ├── renderer.py           # Markdown → HTML con plantilla
│   ├── storage.py            # Subida a S3 y URL prefirmada
│   ├── template.html         # Plantilla del expediente
│   └── requirements.txt      # Dependencias de la Lambda
│
├── scripts/
│   └── local_run.py          # Ejecuta el flujo completo sin AWS desplegado
│
└── web/
    └── index.html            # Frontend mínimo (input + fetch)
```

---

## Quickstart

Requisitos completos en [`CONFIGURACION.md`](./CONFIGURACION.md). En resumen:

```bash
# 1. Clonar e instalar dependencias locales
git clone <tu-repo> && cd codebase-archaeologist
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Probar la lógica sin desplegar nada
export GITHUB_TOKEN="ghp_..."
python scripts/local_run.py https://github.com/psf/requests

# 3. Desplegar
sam build
sam deploy --guided
```

El despliegue te devuelve la URL del endpoint en los outputs.

---

## Uso

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
  "commits_analizados": 10,
  "expira_en": "7 días"
}
```

---

## Decisiones de diseño

**Nova Lite en lugar de Nova Pro.** API Gateway corta las conexiones a los 29 segundos. Nova Lite genera 1200 tokens en un rango cómodo dentro de ese límite; Nova Pro es mejor escritor pero se acerca peligrosamente al timeout. Si prefieres calidad sobre latencia, la alternativa es una Lambda Function URL, que soporta hasta 15 minutos.

**URLs prefirmadas en lugar de bucket público.** S3 bloquea el acceso público por defecto y desactivarlo requiere tocar cuatro configuraciones. Una URL prefirmada de 7 días resuelve el caso de uso sin abrir el bucket. Si quieres links permanentes, la vía correcta es CloudFront con Origin Access Control.

**Converse API en lugar de `invoke_model`.** `converse()` unifica el formato de request y response entre modelos de Bedrock. Cambiar de Nova a Claude o a Llama es cambiar un string, no reescribir el parseo.

**Solo 10 commits.** No es una limitación técnica sino narrativa: con más contexto el modelo tiende a resumir en lugar de dramatizar. Diez commits dan suficiente material para una historia sin diluir el tono.

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

⚠️ El riesgo real no es el costo por ejecución, sino dejar un endpoint público sin límites. Configura throttling en API Gateway y una alarma de facturación. Ver [`CONFIGURACION.md`](./CONFIGURACION.md#protección-contra-abuso).

---

## Roadmap

- [ ] Cache en S3: si el repo ya fue excavado hoy, devolver el expediente existente
- [ ] Streaming de la respuesta con Lambda Function URL
- [ ] Análisis de contribuidores ("los personajes de esta historia")
- [ ] Detección de "momentos dramáticos": commits con `revert`, `hotfix`, `WIP`, `fix fix fix`
- [ ] Múltiples voces narrativas: noir, épica nórdica, documental de naturaleza
- [ ] CloudFront + dominio propio para links permanentes

---

## Documentación

- [`CONFIGURACION.md`](./CONFIGURACION.md) — Cuentas, permisos, IAM, variables de entorno y troubleshooting
- [`FASES.md`](./FASES.md) — Plan de desarrollo dividido en fases con criterios de aceptación
