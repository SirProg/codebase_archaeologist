[English](./CONFIGURATION.md) | [Español](./CONFIGURACION.md)

# ⚙️ Configuración del proyecto

Todo lo que hay que dejar listo **antes** de escribir código. El orden importa: los pasos 1 y 2 dependen de aprobaciones externas y conviene lanzarlos primero.

---

## 1. Acceso a modelos en Amazon Bedrock

**Este es el paso que más gente olvida y el que rompe todo silenciosamente.** Bedrock no permite invocar ningún modelo hasta que solicitas acceso explícitamente desde la consola.

1. Entra a la consola de AWS y selecciona la región **us-east-1 (N. Virginia)**. Es la región con mejor disponibilidad de modelos Nova y la que asumen todos los ejemplos de este proyecto.
2. Ve a **Amazon Bedrock → Model access** (menú lateral izquierdo).
3. Click en **Modify model access** / **Enable specific models**.
4. Marca los modelos de la familia **Amazon Nova**: `Nova Micro`, `Nova Lite` y `Nova Pro`.
5. Guarda. El acceso a los modelos de Amazon suele concederse de inmediato.

Verifica desde tu terminal:

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'nova')].modelId"
```

Y prueba una invocación real:

```bash
aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Di hola en una frase."}]}]'
```

Si esto responde, Bedrock está listo. Si falla, salta a [Troubleshooting](#troubleshooting).

### IDs de modelo

| Modelo | ID | Uso recomendado |
|---|---|---|
| Nova Micro | `amazon.nova-micro-v1:0` | Solo texto, el más rápido y barato |
| **Nova Lite** | `amazon.nova-lite-v1:0` | **Default del proyecto** — buen balance |
| Nova Pro | `amazon.nova-pro-v1:0` | Mejor prosa, más lento |

> **Nota sobre inference profiles:** en varias regiones Nova exige invocarse a través de un perfil de inferencia cross-region, cuyo ID lleva un prefijo de región: `us.amazon.nova-lite-v1:0`. Si `converse` falla pidiendo un inference profile, usa el ID con prefijo. Esto también cambia el ARN que necesitas en la política IAM (ver sección 5).

---

## 2. Personal Access Token de GitHub

Sin token, la API de GitHub te da **60 requests por hora por IP**. Como Lambda comparte IPs, ese límite se agota rapidísimo. Con token subes a **5000 por hora**.

1. GitHub → **Settings → Developer settings → Personal access tokens → Tokens (classic)**.
2. **Generate new token (classic)**.
3. Nombre: `codebase-archaeologist`. Expiración: 90 días.
4. Scopes: **ninguno**. Para leer repositorios públicos no necesitas ningún scope marcado; un token sin permisos ya te sube el rate limit.
5. Copia el token (empieza con `ghp_`). No lo volverás a ver.

### Guardarlo en SSM Parameter Store

Usamos Parameter Store en lugar de Secrets Manager porque los parámetros estándar son **gratuitos**, mientras que Secrets Manager cobra por secreto por mes.

```bash
aws ssm put-parameter \
  --name "/codebase-archaeologist/github-token" \
  --value "ghp_TU_TOKEN_AQUI" \
  --type SecureString \
  --region us-east-1
```

⚠️ **El nombre debe empezar por `/`.** La política IAM del template construye el ARN concatenando `parameter` + este nombre, así que un parámetro llamado `token_github` (sin barra) produciría `arn:...:parametertoken_github`, un ARN malformado: el deploy funcionaría y la Lambda fallaría con `AccessDenied` en runtime, ya en producción. El template lo rechaza de antemano con un `AllowedPattern`, pero es mejor crear el parámetro bien desde el principio.

Si usas otro nombre, pásalo al desplegar:

```bash
sam deploy --parameter-overrides GitHubTokenParam=/tu/nombre/de/parametro
```

Comprueba que quedó bien:

```bash
aws ssm get-parameter --name "/codebase-archaeologist/github-token" \
  --with-decryption --query "Parameter.{Nombre:Name,Tipo:Type}"
```

Si el error es `ParameterNotFound` tienes permiso pero el parámetro no existe (o se llama distinto). Si es `AccessDeniedException`, lo que falta es el permiso.

Para desarrollo local, exporta el token como variable de entorno en lugar de leerlo de SSM:

```bash
export GITHUB_TOKEN="ghp_TU_TOKEN_AQUI"
```

⚠️ Añade `.env` y cualquier archivo con el token a `.gitignore` antes del primer commit.

---

## 3. Herramientas locales

| Herramienta | Versión | Verificación |
|---|---|---|
| Python | 3.12 | `python --version` |
| Node.js | 20 o superior | `node --version` |
| npm | 10 o superior | `npm --version` |
| AWS CLI | v2 | `aws --version` |
| AWS SAM CLI | reciente | `sam --version` |
| Docker | opcional | `docker --version` |

Node solo hace falta para el frontend; el backend no lo usa. Docker solo hace falta para `sam local invoke` y para `sam build --use-container`. Si tus dependencias son puro Python (lo son en este proyecto), puedes prescindir de él.

> **`sam build` exige el intérprete exacto del runtime.** No basta con "un Python parecido": si tu `python3` es 3.13 o 3.14, el build falla con
>
> ```
> PythonPipBuilder:Validation - searched for python in ['/usr/bin/python', '/usr/bin/python3']
> which did not satisfy constraints for runtime: python3.12
> ```
>
> La salida más rápida es instalar solo esa versión, sin tocar el Python del sistema:
>
> ```bash
> uv python install 3.12      # deja el shim en ~/.local/bin/python3.12
> ```
>
> Tarda menos de un segundo y `sam build` pasa a funcionar sin Docker. Si no usas `uv`, valen igual `pyenv install 3.12` o el paquete de tu distribución.
>
> La alternativa es `sam build --use-container`, que compila dentro de la imagen oficial del runtime. Funciona, pero descarga ~3.6 GB y, si tu máquina es x86_64 y la función es `arm64`, corre emulada y tarda muchísimo. Úsala solo si no puedes instalar el intérprete.

> **Sobre `arm64` y las dependencias compiladas.** Aunque construyas en x86_64, pip resuelve las wheels para la arquitectura *destino*, no la tuya. En este proyecto `charset_normalizer` (dependencia transitiva de `requests`) trae extensiones en C, y el artefacto acaba con `md.cpython-312-aarch64-linux-gnu.so` — correcto para la Lambda. Puedes verificarlo tú mismo:
>
> ```bash
> find .aws-sam/build -name "*.so"
> ```

### Instalación de AWS CLI y SAM CLI

**Arch Linux / derivadas**

```bash
sudo pacman -S aws-cli-v2      # ⚠️ NO "aws-cli" a secas: ese es la v1
yay -S aws-sam-cli-bin         # SAM no está en repos oficiales, solo en AUR
```

Del AUR existen `aws-sam-cli` y `aws-sam-cli-bin`. Usa el `-bin`: suele ir varias versiones por delante y no tiene que compilar nada.

**macOS**

```bash
brew install awscli aws-sam-cli
```

**Otras distribuciones de Linux** (instaladores oficiales)

```bash
# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip && sudo ./aws/install

# SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
```

**Windows:** descarga los instaladores MSI desde las páginas de releases de AWS CLI y AWS SAM.

### Credenciales de AWS

```bash
aws configure
# AWS Access Key ID:     ...
# AWS Secret Access Key: ...
# Default region name:   us-east-1
# Default output format:  json

aws sts get-caller-identity   # debe devolver tu cuenta y ARN
```

Si tu acceso es por SSO / Identity Center, usa `aws configure sso` en su lugar, y `aws sso login` cuando caduque la sesión.

Usa un usuario IAM con permisos de administrador para desarrollar, o al menos con acceso a: IAM, Lambda, S3, Bedrock, API Gateway, CloudFormation y SSM.

Para descartar de golpe los permisos de **lectura**:

```bash
probe() { printf "%-28s " "$1"; shift; "$@" >/dev/null 2>&1 && echo "OK" || echo "FALTA"; }
probe "bedrock:InvokeModel"       aws bedrock-runtime converse --region us-east-1 \
  --model-id amazon.nova-lite-v1:0 --messages '[{"role":"user","content":[{"text":"hi"}]}]'
probe "s3"                        aws s3api list-buckets
probe "lambda"                    aws lambda list-functions --max-items 1
probe "cloudformation"            aws cloudformation list-stacks --max-items 1
probe "apigatewayv2"              aws apigatewayv2 get-apis --max-results 1
probe "ssm"                       aws ssm describe-parameters --max-results 1
```

⚠️ **Este bloque no prueba que puedas desplegar.** Todas esas llamadas son de lectura, y un usuario acotado puede pasarlas enteras y aun así fallar en el `sam deploy`. El caso típico es IAM: `iam:ListRoles` funciona, pero **`iam:CreateRole` no**, y el despliegue muere a medio camino con un rollback.

No hay forma de comprobar `iam:CreateRole` sin crear un rol de verdad (IAM no tiene *dry run*, y `iam:SimulatePrincipalPolicy` es a su vez un permiso que un usuario acotado no suele tener). Así que la única prueba real es el propio despliegue — o pedir los permisos por adelantado.

### Permisos necesarios para desplegar

Además de los de lectura, `sam deploy` necesita crear y etiquetar el rol de ejecución de la Lambda. Esta política, acotada a los roles de este stack, es lo que hay que pedirle al administrador de la cuenta:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SamDeployRoles",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PassRole",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies"
      ],
      "Resource": "arn:aws:iam::TU_ACCOUNT_ID:role/codebase-archaeologist-*"
    }
  ]
}
```

Tres detalles que evitan una segunda ronda de peticiones:

- **`iam:TagRole` no es opcional.** CloudFormation etiqueta cada recurso que crea; sin esa acción el deploy falla con `UnauthorizedTaggingOperation` aunque tengas `CreateRole`.
- **`iam:PassRole`** hace falta para entregarle el rol a Lambda.
- Las acciones de borrado son necesarias para el rollback y para `sam delete`. Sin ellas, un fallo futuro te deja el stack atascado.

El `Resource` acotado a `codebase-archaeologist-*` suele bastar para que lo aprueben sin discusión: no da poder sobre ningún otro rol de la cuenta.

Un usuario acotado también suele fallar en SSM, que es donde vive el token.

---

## 4. Entorno de Python

Todo lo de esta sección corre **dentro de `backend/`**.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

**`backend/requirements-dev.txt`** (para el script local):

```
boto3>=1.34.0
requests>=2.31.0
markdown>=3.5
```

**`backend/src/requirements.txt`** (para la Lambda):

```
requests>=2.31.0
markdown>=3.5
```

`boto3` no se incluye en el paquete de la Lambda: el runtime de Python en Lambda ya lo trae preinstalado, y empaquetarlo solo agranda el ZIP. La versión incluida en el runtime a veces va un poco por detrás de la última publicada; si necesitas una API muy reciente de boto3, entonces sí agrégalo explícitamente.

---

## 5. Permisos IAM de la Lambda

La función necesita exactamente cuatro cosas. Nada de `Resource: "*"` — en una evaluación técnica lo notan. Todo esto vive ya en `backend/template.yaml`; lo que sigue explica por qué está escrito así.

```yaml
Policies:
  # Escribir logs en CloudWatch
  - AWSLambdaBasicExecutionRole

  # Invocar el modelo de Bedrock
  - Statement:
      - Effect: Allow
        Action:
          - bedrock:InvokeModel
        Resource:
          - arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0

  # Escribir y leer los expedientes generados
  - Statement:
      - Effect: Allow
        Action:
          - s3:PutObject
          - s3:GetObject
        Resource: !Sub "${ExpedientesBucket.Arn}/*"

  # Leer el token de GitHub
  - Statement:
      - Effect: Allow
        Action:
          - ssm:GetParameter
        Resource: !Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/codebase-archaeologist/*"
```

Detalles que importan:

- El ARN de un foundation model **no lleva account ID** — fíjate en el doble `::`. Los ARN de inference profiles sí lo llevan: `arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.amazon.nova-lite-v1:0`. Si usas el ID con prefijo de región, necesitas ambos ARN en la política (el del perfil y el del modelo subyacente).
- El permiso de S3 apunta a `bucket/*`, no al bucket. Para operaciones sobre objetos el recurso es la clave del objeto.
- `s3:GetObject` es necesario aunque solo subas archivos, porque la URL prefirmada de descarga se firma contra ese permiso.
- El ARN del parámetro SSM se construye como `parameter` + el nombre, que por eso **debe empezar por `/`**. El template lo fuerza con un `AllowedPattern`, de modo que un nombre mal formado falla en el deploy y no en runtime.

---

## 6. Configuración de la Lambda

| Parámetro | Valor | Por qué |
|---|---|---|
| Runtime | `python3.12` | |
| Timeout | **60 s** | El default de 3 s es insuficiente y falla de inmediato |
| Memoria | **512 MB** | En Lambda la CPU escala con la memoria; 512 MB acelera el parseo y el render sin costo real |
| Arquitectura | `arm64` | Graviton es más barato por milisegundo |

### Variables de entorno

```yaml
Environment:
  Variables:
    BUCKET_NAME: !Ref ExpedientesBucket
    MODEL_ID: amazon.nova-lite-v1:0
    GITHUB_TOKEN_PARAM: /codebase-archaeologist/github-token
    MAX_COMMITS: "10"
    MAX_README_CHARS: "4000"
    MAX_TOKENS: "1500"
    URL_EXPIRACION_SEGUNDOS: "604800"
```

Todas están ya declaradas en `backend/template.yaml`.

Nunca pongas el token de GitHub como variable de entorno en producción: las variables de entorno de Lambda son visibles para cualquiera que pueda leer la configuración de la función. Para desarrollo local sí es cómodo: si `GITHUB_TOKEN` está definido, `app.py` lo usa y se salta SSM.

---

## 7. Configuración de S3

El bucket **no debe ser público**. Mantén Block Public Access activado y sirve los expedientes con URLs prefirmadas.

```yaml
ExpedientesBucket:
  Type: AWS::S3::Bucket
  Properties:
    PublicAccessBlockConfiguration:
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true
    LifecycleConfiguration:
      Rules:
        - Id: BorrarExpedientesViejos
          Status: Enabled
          ExpirationInDays: 30
```

La regla de ciclo de vida evita que el bucket acumule basura indefinidamente durante las pruebas.

De cada excavación se guardan dos objetos: `expedientes/{owner}-{repo}-{fecha}.html` (lo que abre el enlace prefirmado) y el `.md` con el mismo nombre. El Markdown existe para que un acierto de cache pueda devolverle también el relato al frontend, que es quien lo renderiza.

Al subir el HTML, especifica el content type o el navegador lo descargará en vez de renderizarlo:

```python
s3.put_object(
    Bucket=BUCKET,
    Key=key,
    Body=html.encode("utf-8"),
    ContentType="text/html; charset=utf-8",
)
```

---

## 8. CORS

El frontend vive en Vercel y el endpoint en API Gateway: son orígenes distintos, así que el navegador exige CORS. Como el dominio del frontend es conocido, no hace falta abrir el endpoint a `"*"`.

`backend/template.yaml` lo declara como parámetro:

```yaml
Parameters:
  AllowedOrigins:
    Type: CommaDelimitedList
    Default: "http://localhost:5173"

Resources:
  ArchaeologistApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      CorsConfiguration:
        AllowOrigins: !Ref AllowedOrigins
        AllowHeaders: [Content-Type]
        AllowMethods: [POST, OPTIONS]
```

En el despliegue pasas los orígenes reales:

```bash
sam deploy --parameter-overrides \
  'AllowedOrigins="https://tu-app.vercel.app,http://localhost:5173"'
```

Detalles que importan:

- Los **deploy previews de Vercel** usan un subdominio distinto en cada push (`tu-app-git-rama-usuario.vercel.app`). CORS no acepta comodines de subdominio, así que si quieres probar desde un preview tienes que añadir ese origen explícitamente.
- El origen debe ir **sin barra final** y con el esquema incluido.
- Con HTTP API (`AWS::Serverless::HttpApi`) el preflight lo maneja API Gateway. Con REST API tendrías que devolver los headers CORS manualmente desde la Lambda en cada respuesta, incluidos los errores.

---

## 9. Despliegue del frontend en Vercel

1. En Vercel, **Add New → Project** e importa el repositorio.
2. **Root Directory: `frontend`.** Es el paso que más se olvida: sin esto Vercel busca el `package.json` en la raíz y el build falla.
3. Framework preset: **Vite**. Build command `npm run build`, output directory `dist`. Vercel los detecta solo.
4. **Environment Variables** → añade `VITE_API_URL` con el output `ApiUrl` del despliegue de SAM, sin la ruta `/excavate` y sin barra final:

   ```
   VITE_API_URL = https://xxxxx.execute-api.us-east-1.amazonaws.com
   ```

5. Deploy. Anota el dominio que te asigna.
6. **Vuelve al backend** y redespliega con ese dominio en `AllowedOrigins` (sección 8). Hasta que hagas esto, el navegador bloqueará todas las peticiones.

Para desarrollo local, `frontend/.env.local` (ignorado por git):

```bash
cd frontend
cp .env.example .env.local     # y edita VITE_API_URL
npm run dev
```

⚠️ Las variables `VITE_*` se **hornean en el bundle en tiempo de build y son públicas**: cualquiera puede leerlas en el JavaScript servido. Ahí solo va la URL del endpoint, que ya es pública de todos modos. El token de GitHub nunca toca el frontend — vive en SSM y solo lo lee la Lambda.

`frontend/vercel.json` incluye un rewrite de todas las rutas a `index.html`. Hoy la app es una sola pantalla y no lo necesita, pero evita un 404 el día que añadas rutas.

---

## 10. Protección contra abuso

Un endpoint público que invoca un LLM es una invitación a que alguien te queme la cuenta.

**Throttling en API Gateway** (ya declarado en `backend/template.yaml`):

```yaml
ArchaeologistApi:
  Type: AWS::Serverless::HttpApi
  Properties:
    DefaultRouteSettings:
      ThrottlingBurstLimit: 5
      ThrottlingRateLimit: 2
```

**Alarma de facturación:** en CloudWatch (región us-east-1, que es donde viven las métricas de billing), crea una alarma sobre la métrica `EstimatedCharges` con umbral en unos pocos dólares. Requiere activar antes las alertas de facturación en Billing preferences.

**Validación en el código:** rechaza URLs que no sean de `github.com`, limita la longitud del input y valida que `owner/repo` cumpla el formato esperado antes de hacer cualquier llamada externa.

---

## 11. `.gitignore`

Un solo `.gitignore` en la raíz cubre backend y frontend:

```gitignore
# Python
.venv/
__pycache__/
*.pyc

# AWS SAM
.aws-sam/
backend/.aws-sam/
backend/samconfig.toml

# Secretos y salidas locales
.env
*.local.json
salida_local.html

# Node / frontend
node_modules/
frontend/dist/
*.tsbuildinfo
frontend/.env
frontend/.env.local

# Vercel
.vercel/
```

`samconfig.toml` puede contener nombres de buckets y parámetros de tu cuenta. Si vas a publicar el repo, mejor fuera.

---

## Troubleshooting

| Error | Causa | Solución |
|---|---|---|
| `AccessDeniedException` al llamar a Bedrock | Model access no solicitado | Paso 1 de este documento |
| `ValidationException: ... inference profile` | El modelo requiere perfil cross-region en esa región | Usa `us.amazon.nova-lite-v1:0` y ajusta el ARN en IAM |
| `ResourceNotFoundException` con el modelId | Región equivocada o ID mal escrito | Verifica con `list-foundation-models` |
| Timeout a los 29 s exactos | Límite de API Gateway | Baja `MAX_TOKENS`, usa Nova Lite, o migra a Lambda Function URL |
| `Task timed out after 3.00 seconds` | Timeout de Lambda en el default | Sube `Timeout` a 60 en `template.yaml` |
| `Your account is currently being verified` | Cuenta de AWS recién creada | No es configuración tuya: AWS tarda hasta 2 h. Si persiste, escribe a aws-verification@amazon.com |
| `PythonPipBuilder:Validation ... did not satisfy constraints for runtime: python3.12` | Tu Python local no es 3.12 | `uv python install 3.12` (sección 3) |
| `ParameterNotFound` al leer el token | Tienes permiso, pero el parámetro no existe o se llama distinto | Sección 2 |
| `arn:...:parametertoken_...` en una política | Nombre de parámetro sin `/` inicial | Sección 2 |
| `403` de GitHub con mensaje de rate limit | Token ausente o mal leído | Revisa que la Lambda lea el parámetro SSM correctamente |
| `404` de GitHub en `/readme` | El repo no tiene README | Trátalo como caso válido, no como error |
| El navegador descarga el HTML en vez de mostrarlo | Falta `ContentType` | Añádelo al `put_object` |
| CORS error en el frontend | Preflight no configurado | Sección 8 |
| `AccessDenied` al subir a S3 | ARN de la política apunta al bucket, no a `bucket/*` | Sección 5 |
| `not authorized to perform: iam:CreateRole` en el deploy | Tu usuario puede leer roles pero no crearlos | Pide la política de la sección 3. Los permisos de lectura no bastan |
| `UnauthorizedTaggingOperation` al crear el rol | Falta `iam:TagRole` | Va en la misma política de la sección 3 |
| El stack queda en `ROLLBACK_COMPLETE` | Falló la creación y CloudFormation deshizo todo | Bórralo antes de reintentar: `aws cloudformation delete-stack --stack-name codebase-archaeologist`. Un stack en ese estado no se puede actualizar |
| `401 Bad credentials` de GitHub | El PAT caducó (se emiten a 90 días) | Genera uno nuevo y actualiza el parámetro SSM |
| El frontend dice «Falta VITE_API_URL» | La variable no está definida en el build | Sección 9 |
| Build de Vercel: no encuentra `package.json` | Root Directory sin configurar | Ponlo en `frontend` (sección 9) |
| Cambias `VITE_API_URL` y no surte efecto | Las `VITE_*` se hornean en build time | Redespliega en Vercel; no basta con guardar la variable |

### Dónde mirar cuando algo falla

```bash
# Logs en vivo de la función (desde backend/)
sam logs -n ArchaeologistFunction --stack-name codebase-archaeologist --tail

# Últimos eventos del stack (útil si falla el despliegue)
aws cloudformation describe-stack-events \
  --stack-name codebase-archaeologist \
  --max-items 20
```

---

## Checklist previo al desarrollo

**Backend**

- [ ] Model access de Nova concedido en us-east-1
- [ ] `aws bedrock-runtime converse` responde correctamente
- [ ] PAT de GitHub creado y guardado en SSM como SecureString
- [ ] `GITHUB_TOKEN` exportado en el entorno local
- [ ] AWS CLI configurado y `sts get-caller-identity` funciona
- [ ] Permisos de **escritura** para desplegar, no solo de lectura (`iam:CreateRole` y `iam:TagRole` incluidos — sección 3)
- [ ] SAM CLI instalado
- [ ] Python 3.12 disponible (`sam build` exige la versión exacta)
- [ ] Virtualenv creado en `backend/` con las dependencias
- [ ] `.gitignore` en su sitio antes del primer commit
- [ ] Alerta de facturación activada

**Frontend**

- [ ] Node 20+ y npm instalados
- [ ] Cuenta de Vercel creada
- [ ] `frontend/.env.local` con `VITE_API_URL` apuntando al endpoint
- [ ] Dominio de Vercel añadido a `AllowedOrigins` del backend
