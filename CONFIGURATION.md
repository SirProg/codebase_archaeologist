[English](./CONFIGURATION.md) | [Español](./CONFIGURACION.md)

# ⚙️ Project setup

Everything that needs to be in place **before** writing any code. Order matters: steps 1 and 2 depend on external approvals, so start them first.

---

## 1. Model access in Amazon Bedrock

**This is the step most people forget, and the one that silently breaks everything.** Bedrock won't let you invoke any model until you explicitly request access from the console.

1. Open the AWS console and select the **us-east-1 (N. Virginia)** region. It has the best Nova availability and every example in this project assumes it.
2. Go to **Amazon Bedrock → Model access** (left sidebar).
3. Click **Modify model access** / **Enable specific models**.
4. Check the **Amazon Nova** family: `Nova Micro`, `Nova Lite` and `Nova Pro`.
5. Save. Access to Amazon's own models is usually granted immediately.

Verify from your terminal:

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'nova')].modelId"
```

And check the access status of the model itself:

```bash
aws bedrock get-foundation-model-availability \
  --region us-east-1 --model-id amazon.nova-lite-v1:0
```

`authorizationStatus: AUTHORIZED` means access is granted. Then try a real invocation:

```bash
aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Say hello in one sentence."}]}]'
```

If that responds, Bedrock is ready. If it fails, jump to [Troubleshooting](#troubleshooting).

### Model IDs

| Model | ID | Recommended use |
|---|---|---|
| Nova Micro | `amazon.nova-micro-v1:0` | Text only, fastest and cheapest |
| **Nova Lite** | `amazon.nova-lite-v1:0` | **Project default** — good balance |
| Nova Pro | `amazon.nova-pro-v1:0` | Better prose, slower |

> **A note on inference profiles:** in several regions Nova must be invoked through a cross-region inference profile, whose ID carries a region prefix: `us.amazon.nova-lite-v1:0`. If `converse` fails asking for an inference profile, use the prefixed ID. That also changes the ARN you need in the IAM policy (see section 5).

---

## 2. GitHub Personal Access Token

Without a token, the GitHub API gives you **60 requests per hour per IP**. Since Lambda shares IPs, that limit burns out fast. With a token you get **5000 per hour**.

1. GitHub → **Settings → Developer settings → Personal access tokens → Tokens (classic)**.
2. **Generate new token (classic)**.
3. Name: `codebase-archaeologist`. Expiration: 90 days.
4. Scopes: **none**. Reading public repositories requires no scope at all; a permissionless token already raises your rate limit.
5. Copy the token (starts with `ghp_`). You won't see it again.

### Storing it in SSM Parameter Store

We use Parameter Store rather than Secrets Manager because standard parameters are **free**, while Secrets Manager charges per secret per month.

```bash
aws ssm put-parameter \
  --name "/codebase-archaeologist/github-token" \
  --value "ghp_YOUR_TOKEN_HERE" \
  --type SecureString \
  --region us-east-1
```

⚠️ **The name must start with `/`.** The template's IAM policy builds the ARN by concatenating `parameter` + this name, so a parameter called `token_github` (no slash) would produce `arn:...:parametertoken_github` — a malformed ARN: the deploy would succeed and the Lambda would fail with `AccessDenied` at runtime, already in production. The template rejects that up front with an `AllowedPattern`, but it's better to create the parameter correctly from the start.

If you use a different name, pass it at deploy time:

```bash
sam deploy --parameter-overrides GitHubTokenParam=/your/parameter/name
```

Check that it landed correctly:

```bash
aws ssm get-parameter --name "/codebase-archaeologist/github-token" \
  --with-decryption --query "Parameter.{Name:Name,Type:Type}"
```

If the error is `ParameterNotFound` you have permission but the parameter doesn't exist (or is named differently). If it's `AccessDeniedException`, what you're missing is the permission.

For local development, export the token as an environment variable instead of reading it from SSM:

```bash
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
```

⚠️ Add `.env` and any file containing the token to `.gitignore` before your first commit.

---

## 3. Local tooling

| Tool | Version | Check |
|---|---|---|
| Python | 3.12 | `python --version` |
| Node.js | 20 or later | `node --version` |
| npm | 10 or later | `npm --version` |
| AWS CLI | v2 | `aws --version` |
| AWS SAM CLI | recent | `sam --version` |
| Docker | optional | `docker --version` |

Node is only needed for the frontend; the backend doesn't use it. Docker is only needed for `sam local invoke` and `sam build --use-container`.

> **`sam build` requires the runtime's exact interpreter.** "A similar Python" is not enough: if your `python3` is 3.13 or 3.14, the build fails with
>
> ```
> PythonPipBuilder:Validation - searched for python in ['/usr/bin/python', '/usr/bin/python3']
> which did not satisfy constraints for runtime: python3.12
> ```
>
> The fastest way out is to install just that version, without touching your system Python:
>
> ```bash
> uv python install 3.12      # drops a shim at ~/.local/bin/python3.12
> ```
>
> It takes under a second and `sam build` starts working with no Docker. If you don't use `uv`, `pyenv install 3.12` or your distribution's package work just as well.
>
> The alternative is `sam build --use-container`, which builds inside the official runtime image. It works, but downloads ~3.6 GB and, if your machine is x86_64 and the function is `arm64`, it runs emulated and takes forever. Use it only if you can't install the interpreter.

> **On `arm64` and compiled dependencies.** Even when you build on x86_64, pip resolves wheels for the *target* architecture, not yours. In this project `charset_normalizer` (a transitive dependency of `requests`) ships C extensions, and the artifact ends up with `md.cpython-312-aarch64-linux-gnu.so` — correct for the Lambda. You can verify it yourself:
>
> ```bash
> find .aws-sam/build -name "*.so"
> ```

### Installing AWS CLI and SAM CLI

**Arch Linux / derivatives**

```bash
sudo pacman -S aws-cli-v2      # ⚠️ NOT plain "aws-cli": that one is v1
yay -S aws-sam-cli-bin         # SAM isn't in the official repos, only in the AUR
```

The AUR has both `aws-sam-cli` and `aws-sam-cli-bin`. Use the `-bin` one: it's usually several versions ahead and doesn't have to compile anything.

**macOS**

```bash
brew install awscli aws-sam-cli
```

**Other Linux distributions** (official installers)

```bash
# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip && sudo ./aws/install

# SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
```

**Windows:** download the MSI installers from the AWS CLI and AWS SAM release pages.

### AWS credentials

```bash
aws configure
# AWS Access Key ID:     ...
# AWS Secret Access Key: ...
# Default region name:   us-east-1
# Default output format:  json

aws sts get-caller-identity   # should return your account and ARN
```

If your access is through SSO / Identity Center, use `aws configure sso` instead, and `aws sso login` whenever the session expires.

Use an IAM user with administrator permissions for development, or at least with access to: IAM, Lambda, S3, Bedrock, API Gateway, CloudFormation and SSM.

To check none of them is missing, all at once:

```bash
probe() { printf "%-28s " "$1"; shift; "$@" >/dev/null 2>&1 && echo "OK" || echo "MISSING"; }
probe "bedrock:InvokeModel"       aws bedrock-runtime converse --region us-east-1 \
  --model-id amazon.nova-lite-v1:0 --messages '[{"role":"user","content":[{"text":"hi"}]}]'
probe "s3"                        aws s3api list-buckets
probe "lambda"                    aws lambda list-functions --max-items 1
probe "cloudformation"            aws cloudformation list-stacks --max-items 1
probe "iam"                       aws iam list-roles --max-items 1
probe "apigatewayv2"              aws apigatewayv2 get-apis --max-results 1
probe "ssm"                       aws ssm describe-parameters --max-results 1
```

A scoped-down user typically fails precisely on SSM, which is where the token lives.

---

## 4. Python environment

Everything in this section runs **inside `backend/`**.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

**`backend/requirements-dev.txt`** (for the local script):

```
boto3>=1.34.0
requests>=2.31.0
markdown>=3.5
```

**`backend/src/requirements.txt`** (for the Lambda):

```
requests>=2.31.0
markdown>=3.5
```

`boto3` isn't bundled into the Lambda package: the Python runtime in Lambda already ships it, and packaging it only bloats the ZIP. The bundled version sometimes lags a little behind the latest release; if you need a very recent boto3 API, then do add it explicitly.

---

## 5. Lambda IAM permissions

The function needs exactly four things. No `Resource: "*"` — in a technical review people notice. All of this already lives in `backend/template.yaml`; what follows explains why it's written that way.

```yaml
Policies:
  # Write logs to CloudWatch
  - AWSLambdaBasicExecutionRole

  # Invoke the Bedrock model
  - Statement:
      - Effect: Allow
        Action:
          - bedrock:InvokeModel
        Resource:
          - arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0

  # Write and read the generated case files
  - Statement:
      - Effect: Allow
        Action:
          - s3:PutObject
          - s3:GetObject
        Resource: !Sub "${ExpedientesBucket.Arn}/*"

  # Read the GitHub token
  - Statement:
      - Effect: Allow
        Action:
          - ssm:GetParameter
        Resource: !Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/codebase-archaeologist/*"
```

Details that matter:

- A foundation model's ARN carries **no account ID** — note the double `::`. Inference profile ARNs do: `arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.amazon.nova-lite-v1:0`. If you use the region-prefixed ID, you need both ARNs in the policy (the profile's and the underlying model's).
- The S3 permission points at `bucket/*`, not the bucket. For object operations the resource is the object key.
- `s3:GetObject` is required even if you only upload, because the presigned download URL is signed against that permission.
- The SSM parameter's ARN is built as `parameter` + the name, which is why it **must start with `/`**. The template enforces this with an `AllowedPattern`, so a malformed name fails at deploy time rather than at runtime.

---

## 6. Lambda configuration

| Setting | Value | Why |
|---|---|---|
| Runtime | `python3.12` | |
| Timeout | **60 s** | The 3 s default is not enough and fails immediately |
| Memory | **512 MB** | In Lambda, CPU scales with memory; 512 MB speeds up parsing and rendering at no real cost |
| Architecture | `arm64` | Graviton is cheaper per millisecond |

### Environment variables

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

They are all declared in `backend/template.yaml`.

Never put the GitHub token in a Lambda environment variable in production: environment variables are visible to anyone who can read the function's configuration. For local development it is convenient: if `GITHUB_TOKEN` is set, `app.py` uses it and skips SSM.

---

## 7. S3 configuration

The bucket **must not be public**. Keep Block Public Access on and serve the case files through presigned URLs.

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

The lifecycle rule stops the bucket from accumulating junk indefinitely during testing.

Each excavation stores two objects: `expedientes/{owner}-{repo}-{date}.html` (what the presigned link opens) and the `.md` with the same name. The Markdown exists so that a cache hit can also return the narrative to the frontend, which is what renders it.

When uploading the HTML, set the content type or the browser will download it instead of rendering it:

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

The frontend lives on Vercel and the endpoint on API Gateway: different origins, so the browser requires CORS. Since the frontend's domain is known, there's no need to open the endpoint to `"*"`.

`backend/template.yaml` declares it as a parameter:

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

At deploy time you pass the real origins:

```bash
sam deploy --parameter-overrides \
  'AllowedOrigins="https://your-app.vercel.app,http://localhost:5173"'
```

Details that matter:

- **Vercel deploy previews** use a different subdomain on every push (`your-app-git-branch-user.vercel.app`). CORS does not accept subdomain wildcards, so if you want to test from a preview you must add that origin explicitly.
- The origin must have **no trailing slash** and must include the scheme.
- With HTTP API (`AWS::Serverless::HttpApi`) API Gateway handles the preflight. With REST API you'd have to return the CORS headers manually from the Lambda on every response, errors included.

---

## 9. Deploying the frontend on Vercel

1. In Vercel, **Add New → Project** and import the repository.
2. **Root Directory: `frontend`.** This is the most commonly forgotten step: without it Vercel looks for `package.json` at the repo root and the build fails.
3. Framework preset: **Vite**. Build command `npm run build`, output directory `dist`. Vercel detects these on its own.
4. **Environment Variables** → add `VITE_API_URL` with the `ApiUrl` output from the SAM deploy, without the `/excavate` path and without a trailing slash:

   ```
   VITE_API_URL = https://xxxxx.execute-api.us-east-1.amazonaws.com
   ```

5. Deploy. Note the domain it assigns you.
6. **Go back to the backend** and redeploy with that domain in `AllowedOrigins` (section 8). Until you do, the browser will block every request.

For local development, `frontend/.env.local` (git-ignored):

```bash
cd frontend
cp .env.example .env.local     # then edit VITE_API_URL
npm run dev
```

⚠️ `VITE_*` variables are **baked into the bundle at build time and are public**: anyone can read them in the served JavaScript. Only the endpoint URL goes there, which is public anyway. The GitHub token never touches the frontend — it lives in SSM and only the Lambda reads it.

`frontend/vercel.json` includes a rewrite of all routes to `index.html`. The app is a single screen today and doesn't need it, but it avoids a 404 the day you add routes.

---

## 10. Abuse protection

A public endpoint that invokes an LLM is an invitation for someone to burn through your account.

**API Gateway throttling** (already declared in `backend/template.yaml`):

```yaml
ArchaeologistApi:
  Type: AWS::Serverless::HttpApi
  Properties:
    DefaultRouteSettings:
      ThrottlingBurstLimit: 5
      ThrottlingRateLimit: 2
```

**Billing alarm:** in CloudWatch (region us-east-1, where billing metrics live), create an alarm on the `EstimatedCharges` metric with a threshold of a few dollars. You need to enable billing alerts in Billing preferences first.

**Validation in code:** reject URLs that aren't from `github.com`, cap the input length, and validate that `owner/repo` matches the expected format before making any external call.

---

## 11. `.gitignore`

A single `.gitignore` at the root covers backend and frontend:

```gitignore
# Python
.venv/
__pycache__/
*.pyc

# AWS SAM
.aws-sam/
backend/.aws-sam/
backend/samconfig.toml

# Secrets and local output
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

`samconfig.toml` may contain bucket names and parameters from your account. If you're publishing the repo, better to leave it out.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `AccessDeniedException` calling Bedrock | Model access not requested | Step 1 of this document |
| `Your account is currently being verified` | Brand-new AWS account | Not your configuration: AWS takes up to 2 h. If it persists, write to aws-verification@amazon.com |
| `ValidationException: ... inference profile` | The model requires a cross-region profile in that region | Use `us.amazon.nova-lite-v1:0` and adjust the ARN in IAM |
| `ResourceNotFoundException` with the modelId | Wrong region or misspelled ID | Check with `list-foundation-models` |
| `PythonPipBuilder:Validation ... did not satisfy constraints for runtime: python3.12` | Your local Python isn't 3.12 | `uv python install 3.12` (section 3) |
| Timeout at exactly 29 s | API Gateway limit | Lower `MAX_TOKENS`, use Nova Lite, or move to a Lambda Function URL |
| `Task timed out after 3.00 seconds` | Lambda timeout left at the default | Raise `Timeout` to 60 in `template.yaml` |
| `403` from GitHub with a rate limit message | Token missing or misread | Check that the Lambda reads the SSM parameter correctly |
| `401 Bad credentials` from GitHub | The PAT expired (they're issued for 90 days) | Generate a new one and update the SSM parameter |
| `ParameterNotFound` reading the token | You have permission, but the parameter doesn't exist or is named differently | Section 2 |
| `arn:...:parametertoken_...` in a policy | Parameter name without a leading `/` | Section 2 |
| `404` from GitHub on `/readme` | The repo has no README | Treat it as a valid case, not an error |
| The browser downloads the HTML instead of showing it | Missing `ContentType` | Add it to `put_object` |
| CORS error in the frontend | Preflight not configured | Section 8 |
| The frontend says "VITE_API_URL is missing" | The variable isn't set in the build | Section 9 |
| Vercel build: can't find `package.json` | Root Directory not configured | Set it to `frontend` (section 9) |
| You change `VITE_API_URL` and nothing happens | `VITE_*` are baked in at build time | Redeploy on Vercel; saving the variable isn't enough |
| `AccessDenied` uploading to S3 | The policy ARN points at the bucket, not `bucket/*` | Section 5 |

### Where to look when something breaks

```bash
# Live function logs (from backend/)
sam logs -n ArchaeologistFunction --stack-name codebase-archaeologist --tail

# Latest stack events (useful when a deploy fails)
aws cloudformation describe-stack-events \
  --stack-name codebase-archaeologist \
  --max-items 20
```

---

## Pre-development checklist

**Backend**

- [ ] Nova model access granted in us-east-1
- [ ] `aws bedrock-runtime converse` responds correctly
- [ ] GitHub PAT created and stored in SSM as a SecureString
- [ ] `GITHUB_TOKEN` exported in your local environment
- [ ] AWS CLI configured and `sts get-caller-identity` works
- [ ] SAM CLI installed
- [ ] Python 3.12 available (`sam build` requires the exact version)
- [ ] Virtualenv created in `backend/` with the dependencies
- [ ] `.gitignore` in place before the first commit
- [ ] Billing alert enabled

**Frontend**

- [ ] Node 20+ and npm installed
- [ ] Vercel account created
- [ ] `frontend/.env.local` with `VITE_API_URL` pointing at the endpoint
- [ ] Vercel domain added to the backend's `AllowedOrigins`
