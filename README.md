[English](./README.md) | [Español](./README.es.md)

# 🕵️ Codebase Archaeologist

> An autonomous agent that reads a GitHub repository's history and writes an epic account of how that code evolved.

**▶ Try it live: [codebase-archaeologist-two.vercel.app](https://codebase-archaeologist-two.vercel.app)**

Give it the URL of any public repository. The agent pulls the latest commits and the README, hands them to Amazon Nova with instructions to act as a dramatic historian, and returns the account — rendered in the app and archived as a standalone HTML case file on S3.

---

## The problem it solves

Reading someone else's repository is boring and disorienting. Commit history holds a real narrative — decisions, panic refactors, abandoned features — but it's buried in one-line messages. This agent digs it out and turns it into something worth reading.

---

## Architecture

```
Frontend (React + Vite on Vercel)
  │
  │  POST /excavate { "repo_url": "https://github.com/owner/repo" }
  ▼
API Gateway (HTTP API)          CORS restricted to the Vercel domain
  │
  ▼
AWS Lambda  ──────► SSM Parameter Store   (GitHub token)
  │  │
  │  ├──────────► GitHub REST API         (commits + README)
  │  │
  │  ├──────────► Amazon Bedrock / Nova   (narrative generation)
  │  │
  │  └──────────► Amazon S3               (HTML case file + Markdown)
  │
  ▼
{ "url": "...presigned...", "narrativa": "# ...", "repo": "owner/repo" }
  │
  ▼
The SPA renders the Markdown and links to the archived case file.
```

### Components

| Service | Role |
|---|---|
| **Vercel** | Hosts the React frontend. Free, independent of the AWS stack, and gives CORS a known origin to allow. |
| **API Gateway (HTTP API)** | Public `POST /excavate` endpoint. Cheaper and simpler than REST API. |
| **AWS Lambda** | All agent logic: URL parsing, GitHub calls, Bedrock prompt, HTML rendering, S3 upload. |
| **Amazon Bedrock (Nova Lite)** | Generates the historical account from the commits. |
| **Amazon S3** | Archives each case file as static HTML, plus the Markdown for the cache. |
| **SSM Parameter Store** | Stores the GitHub Personal Access Token as a SecureString. |

---

## Repository structure

```
codebase-archaeologist/
├── README.md
├── README.es.md
├── CONFIGURATION.md              # Accounts, permissions and environment setup
├── CONFIGURACION.md              # (español)
├── .gitignore
│
├── backend/                      # Everything that runs on AWS
│   ├── template.yaml             # Infrastructure as code (AWS SAM)
│   ├── requirements-dev.txt      # Dependencies for the local script
│   ├── events/test.json          # Sample event for `sam local invoke`
│   ├── src/
│   │   ├── app.py                # lambda_handler — entry point
│   │   ├── excavacion.py         # The full flow, shared with the local script
│   │   ├── github_client.py      # URL parsing + GitHub API client
│   │   ├── narrator.py           # Prompt and Bedrock call
│   │   ├── renderer.py           # Markdown → HTML with template
│   │   ├── storage.py            # S3 upload, presigned URL and cache
│   │   ├── errors.py             # Typed errors → HTTP status codes
│   │   ├── template.html         # Case file template
│   │   └── requirements.txt      # Lambda dependencies
│   └── scripts/
│       └── local_run.py          # Runs the full flow without deploying to AWS
│
└── frontend/                     # React + Vite + TypeScript, deployed on Vercel
    ├── vercel.json
    ├── .env.example              # VITE_API_URL
    └── src/
        ├── App.tsx               # idle → loading → success / error
        ├── api.ts                # fetch and HTTP-status-to-domain-error mapping
        ├── types.ts              # Contract shared with the Lambda
        ├── styles.css
        └── components/           # RepoForm · LoadingState · Expediente · ErrorBanner
```

---

## Quickstart

Full requirements in [`CONFIGURATION.md`](./CONFIGURATION.md). In short:

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 1. Test the whole flow without deploying anything
export GITHUB_TOKEN="ghp_..."
python scripts/local_run.py https://github.com/psf/requests --abrir

# 2. Deploy
sam build
sam deploy --guided
```

The deployment returns the endpoint URL in the `ApiUrl` output. This instance runs at
`https://lt9c01rdwe.execute-api.us-east-1.amazonaws.com`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local        # point VITE_API_URL at the ApiUrl output
npm run dev                       # http://localhost:5173
```

To deploy: import the repo on Vercel, set **Root Directory** to `frontend`, add `VITE_API_URL`, and redeploy the backend with your Vercel domain in `AllowedOrigins`. See [`CONFIGURATION.md`](./CONFIGURATION.md#9-deploying-the-frontend-on-vercel).

---

## Usage

The frontend is the intended way in, but the live endpoint stands on its own:

```bash
curl -X POST https://lt9c01rdwe.execute-api.us-east-1.amazonaws.com/excavate \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/torvalds/linux"}'
```

Response:

```json
{
  "url": "https://codebase-archaeologist-xxxx.s3.amazonaws.com/expedientes/torvalds-linux-20260829.html?X-Amz-Algorithm=...",
  "repo": "torvalds/linux",
  "narrativa": "# The Chronicle of the Monolith\n\n...",
  "commits_analizados": 10,
  "expira_en": "7 días",
  "cache": false
}
```

Errors always come back in the same shape, never as a raw stack trace:

```json
{ "error": "repo_no_encontrado", "mensaje": "El repositorio no existe o es privado." }
```

| Code | HTTP | When |
|---|---|---|
| `url_invalida` | 400 | Not a GitHub URL, malformed, empty or too long |
| `repo_no_encontrado` | 404 | The repo doesn't exist or is private |
| `rate_limit` | 429 | GitHub's rate limit was hit |
| `github_no_responde` | 502 | GitHub timed out or failed |
| `narrador_no_responde` | 502 | Bedrock failed or returned nothing |
| `token_invalido` | 500 | The PAT expired — a service misconfiguration, not a user error |

---

## Design decisions

**A React SPA on Vercel instead of a single HTML file on S3.** The narrative is returned as Markdown and rendered in the app, so the result appears without a round trip to another tab — and the 10–20 second wait gets a real loading state instead of a frozen button. Hosting is free and fully separate from the AWS stack, and because the frontend lives at a known domain, CORS allows one origin rather than `*`. The presigned S3 case file remains as the shareable, archived artifact.

**Nova Lite instead of Nova Pro.** API Gateway drops connections at 29 seconds. Nova Lite generates 1200 tokens comfortably within that limit; Nova Pro writes better prose but runs dangerously close to the timeout. If you'd rather have quality than latency, the alternative is a Lambda Function URL, which supports up to 15 minutes.

**Presigned URLs instead of a public bucket.** S3 blocks public access by default and disabling it means touching four separate settings. A 7-day presigned URL covers the use case without opening the bucket. If you want permanent links, the right path is CloudFront with Origin Access Control.

**Converse API instead of `invoke_model`.** `converse()` unifies request and response formats across Bedrock models. Switching from Nova to Claude or Llama means changing one string, not rewriting the parsing.

**Only 10 commits.** This isn't a technical limitation but a narrative one: with more context the model tends to summarize rather than dramatize. Ten commits give it enough material for a story without diluting the tone.

**The flow lives in `excavacion.py`, not in the handler.** `local_run.py` and `app.py` call the same function, so the local script exercises exactly the path that runs in production. The handler only deals with HTTP, the cache and secrets.

---

## Costs

At demo-level usage the project costs essentially nothing:

| Service | Approximate cost |
|---|---|
| Bedrock / Nova Lite | Fractions of a cent per run |
| Lambda | Covered by the free tier |
| S3 | Covered by the free tier |
| API Gateway | Covered by the free tier (first year) |
| SSM Parameter Store | Free (standard parameters) |
| Vercel | Free (Hobby plan) |

⚠️ The real risk isn't per-run cost, it's leaving a public endpoint without limits. Throttling is already set in `template.yaml`; add a billing alarm too. See [`CONFIGURATION.md`](./CONFIGURATION.md#10-abuse-protection).

---

## Documentation

- [`CONFIGURATION.md`](./CONFIGURATION.md) — Accounts, permissions, IAM, environment variables, Vercel and troubleshooting
