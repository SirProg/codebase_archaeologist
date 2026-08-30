[English](./PHASES.md) | [Español](./FASES.md)

# 🗺️ Phased development plan

Total estimate: **9 to 13 hours**, spreadable over a weekend.

The principle that orders this whole plan: **don't deploy anything until the logic works on your machine.** Debugging a prompt inside a Lambda is slow and frustrating; debugging it in a local script takes seconds. Phases 0 through 2 don't touch AWS beyond Bedrock.

| Phase | What it produces | Time |
|---|---|---|
| 0 | Environment ready, access granted | 30–45 min |
| 1 | Local script that prints the narrative to the console | 2–3 h |
| 2 | HTML rendered and saved to disk | 1–1.5 h |
| 3 | Lambda running locally with SAM | 1 h |
| 4 | Infrastructure deployed and endpoint live | 1–1.5 h |
| 5 | React frontend deployed on Vercel | ~2 h |
| 6 | Robustness, limits and cleanup | 1–2 h |
| 7 | Demo and documentation | 1 h |

---

## Phase 0 — Preparation

**Goal:** remove every third-party blocker before writing a single line of code.

### Tasks

1. Request Nova model access in Bedrock (us-east-1).
2. Create the GitHub PAT and store it in SSM.
3. Install and verify Python, AWS CLI and SAM CLI.
4. Create the repository with the `backend/` + `frontend/` structure and the `.gitignore`.
5. Create the virtualenv in `backend/` and install dependencies.
6. Create a Vercel account (not needed until Phase 5, but it's free and removes a blocker).

Full details in [`CONFIGURATION.md`](./CONFIGURATION.md).

### Acceptance criterion

```bash
aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"hello"}]}]'
```

returns a response from the model. If this doesn't work, **do not move on**: everything else depends on it.

---

## Phase 1 — The local script

**Goal:** a single file that takes a URL as an argument and spits the narrative to the console. 70% of the project's value lives here.

### 1.1 Parse the URL

Write a function that extracts `owner` and `repo`. The cases it must support:

```
https://github.com/psf/requests
https://github.com/psf/requests/
https://github.com/psf/requests.git
git@github.com:psf/requests.git
https://github.com/psf/requests/tree/main/src
github.com/psf/requests
```

And cleanly reject anything that isn't GitHub. A regular expression over the path solves almost everything; remember to strip the `.git` suffix and discard segments after the repo name.

### 1.2 GitHub client

Three calls:

```
GET https://api.github.com/repos/{owner}/{repo}/commits?per_page=10
GET https://api.github.com/repos/{owner}/{repo}/readme
GET https://api.github.com/repos/{owner}/{repo}          ← metadata, optional but useful
```

Headers on all of them:

```python
{
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
}
```

Concrete traps:

- **The README comes back base64-encoded.** The endpoint returns JSON with an encoded `content` field; decode it with `base64.b64decode(...).decode("utf-8")`.
- **A repo may have no README.** The endpoint answers `404`. That's a valid case, not an error: carry on with an empty README.
- **Commit messages can be enormous.** Many include the whole body along with the title. Keep only the first line of `commit.message`.
- **`commit.author` can be `null`** when the author has no linked GitHub account. Fall back to `commit.commit.author.name`.

Extract per commit: short SHA, author, date and the first line of the message.

### 1.3 The prompt

This is the creative part and where you'll iterate the most. Recommended structure:

**System prompt** — defines the voice and the constraints:

```
You are a dramatic historian specializing in software archaeology.
You write epic chronicles about how code projects evolved, treating
every commit as a historical event and every developer as a
character with motivations.

Rules:
- Write in Spanish, in Markdown.
- Structure: an epic title, an introduction that situates the project,
  3 or 4 narrative sections, and a closing that looks to the future.
- Mention real SHAs and authors; never invent commits or people.
- The tone is dramatic but the content is factual.
- Maximum 800 words.
```

**User message** — the raw data, clearly delimited:

```
<repositorio>
Nombre: {owner}/{repo}
Descripción: {description}
Lenguaje: {language}
Estrellas: {stars}
</repositorio>

<readme>
{truncated_readme}
</readme>

<commits>
{formatted list of the 10 commits}
</commits>
```

Truncate the README to about 4000 characters. Many exceed 20,000, and the excess only dilutes the model's attention away from the commits, which are the story's real raw material.

**Label the commit ordering.** GitHub returns commits newest-first. If you hand them over in that order without saying so, the model reads them top-to-bottom as chronological and calls the most recent commit the project's founding one. Reverse them into chronological order and state explicitly that these are the *most recent* commits, not the beginning of the project, and that the repository's creation date is a separate fact from any commit date.

### 1.4 Calling Bedrock

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

narrative = resp["output"]["message"]["content"][0]["text"]
```

High `temperature` (0.7–0.9) because you want creative prose, not factual precision. The `system` goes in its own parameter, not inside `messages`.

### 1.5 Iterate the prompt

Test with at least five repositories of different profiles:

- A huge, veteran one (`torvalds/linux`)
- A mid-sized, tidy one (`psf/requests`)
- A brand-new one with three commits
- One with no README
- One with useless commit messages (`update`, `fix`, `asdf`)

That last case is what breaks naive prompts. If the model has no material, it tends to invent. Add an explicit instruction for that scenario: have it acknowledge the scarcity of information and turn it into part of the narrative ("the records of this era are fragmentary…") instead of fabricating facts.

### Acceptance criterion

From `backend/`, `python scripts/local_run.py https://github.com/psf/requests` prints a coherent narrative, in Markdown, mentioning real commits from the repository.

---

## Phase 2 — Render to HTML

**Goal:** turn the Markdown into a page that's a pleasure to open.

### Tasks

1. Convert Markdown to HTML:

```python
import markdown
body = markdown.markdown(narrative, extensions=["extra", "nl2br"])
```

2. Create `backend/src/template.html` with embedded CSS — a single file, no external dependencies, no CDNs. Placeholders for the title, the repo name, the body and the generation date.

3. Suggested aesthetic: aged paper, serif typography for the body, monospace for the SHAs. Line width of 65–75 characters. It's a detective's case file, not a dashboard.

4. Write the result to disk and open it in the browser.

### Acceptance criterion

`salida_local.html` opens in the browser and looks deliberately designed. This file is your demo material — invest time in it, because it's the only thing people are going to look at.

---

## Phase 3 — Wrap it in a Lambda

**Goal:** the same logic, now as a function, tested locally with SAM.

### Tasks

1. Reorganize the script into the `backend/src/` modules: `github_client.py`, `narrator.py`, `renderer.py`, `storage.py`.
2. Write `app.py` with the handler:

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

3. Implement `storage.py`: S3 upload with the right `ContentType` and presigned URL generation via `generate_presigned_url("get_object", ...)`.

4. Read the token from SSM with `with_decryption=True`, and cache it in a global variable outside the handler to reuse across warm invocations.

5. Write `backend/template.yaml` with the function, the bucket, the API and the IAM policies (all detailed in `CONFIGURATION.md`).

6. Create `backend/events/test.json` and test:

```bash
cd backend
sam build
sam local invoke ArchaeologistFunction -e events/test.json
```

### Traps

- `sam local invoke` uses your local credentials, not the function's IAM role. Working locally **does not guarantee** the permissions are right. That gets validated in Phase 4.
- `sam local invoke` requires Docker, unlike `sam build`.
- The API Gateway event body is a string, not an object. Always `json.loads`.
- The only writable path in Lambda is `/tmp`. If you generate temporary files, they go there.

### Acceptance criterion

`sam local invoke` returns JSON with an S3 URL, and that URL opens the case file.

---

## Phase 4 — Deployment

**Goal:** a working public endpoint.

### Tasks

```bash
cd backend
sam build
sam deploy --guided
```

In the wizard: stack name `codebase-archaeologist`, region `us-east-1`, and accept the creation of IAM roles. Save the configuration to `samconfig.toml`.

Note the **`ApiUrl`** output: that's what goes into `VITE_API_URL` in Phase 5.

Test the deployed endpoint:

```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/excavate \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/psf/requests"}'
```

Subsequent redeploys are just `sam build && sam deploy`.

### Traps

- **This is where the IAM errors that `sam local` hid show up.** `sam logs --tail` is your best friend.
- Measure the real response time. If it gets close to 29 seconds, lower `maxTokens` or switch to a Lambda Function URL before it becomes a problem during the demo.
- Cold start: the first invocation after a period of inactivity takes longer. In a live demo, make a warm-up call before you begin.

### Acceptance criterion

A `curl` from any machine returns a URL that opens a case file.

---

## Phase 5 — Frontend (React + Vite + TypeScript, on Vercel)

**Goal:** make the demo something other than a `curl`, and let the narrative be read in the app itself.

### 5.1 Scaffold

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install react-markdown remark-gfm
```

Nothing more. No UI or state library: it's three states on one screen, and `useState` is more than enough.

### 5.2 The contract with the backend

The Lambda returns the Markdown alongside the S3 link, and the frontend renders it:

```json
{
  "url": "https://...s3...?X-Amz-...",
  "repo": "owner/repo",
  "narrativa": "# Epic title\n\n...",
  "commits_analizados": 10,
  "expira_en": "7 días",
  "cache": false
}
```

Declare that contract in `src/types.ts` and don't duplicate it anywhere else. If `app.py` changes, it changes there.

### 5.3 Structure

```
src/
├── App.tsx          # idle → loading → success / error
├── api.ts           # fetch, timeout and HTTP-status-to-domain-error mapping
├── types.ts
├── styles.css
└── components/
    ├── RepoForm.tsx
    ├── LoadingState.tsx
    ├── Expediente.tsx
    └── ErrorBanner.tsx
```

### 5.4 What actually matters

**The loading state.** It's a 10–20 second wait. Without visual feedback the user assumes it broke. Rotating messages every ~3 s: "excavating the history…", "consulting the archives…", "drafting the case file…". Stop on the last one rather than cycling: a loop that repeats gives away that nobody knows how long is left.

**Distinguishable errors.** The backend already sends typed `{error, mensaje}`; the frontend only has to give them a title and decide whether to offer "Retry". A nonexistent repo won't fix itself on retry; a Bedrock failure might.

**Client-side validation before the fetch.** A URL that obviously isn't from GitHub doesn't deserve a round trip or a Lambda invocation.

**The `fetch` timeout.** Use `AbortController`, set above the real excavation time (45 s works well). Without it, a hung request leaves the app "loading" forever.

**The aesthetic.** Reuse the palette and typography from `backend/src/template.html`. Having the case file look the same inside the app and on the S3 page is what makes it feel like a product rather than two things glued together.

### 5.5 Deploy on Vercel

Import the repo → **Root Directory `frontend`** → Vite preset → `VITE_API_URL` variable. Then redeploy the backend with the Vercel domain in `AllowedOrigins`. Full details in [`CONFIGURATION.md`](./CONFIGURATION.md#9-deploying-the-frontend-on-vercel).

### Traps

- `VITE_*` variables are baked in at build time. Changing them in the dashboard does **not** affect an existing deploy: you have to redeploy.
- If you forget the Root Directory, Vercel looks for `package.json` at the repo root and the build fails without explaining why.
- A CORS error in the browser console is almost never a frontend bug: it means the origin isn't in `AllowedOrigins`.

### Acceptance criterion

Someone who doesn't know the project can paste a URL on the Vercel domain and get their case file without you explaining anything, seeing at all times that something is happening.

---

## Phase 6 — Robustness

**Goal:** don't crash during the demo.

### Tasks

- **Input validation:** reject non-GitHub domains, cap the length, validate the `owner/repo` format before any external call.
- **Typed errors:** repo not found → 404 with a clear message; rate limit → 429; Bedrock failure → 502; expired PAT → 500 with its own code, so it's distinguishable from a user error. Never a raw stack trace to the user.
- **Explicit timeouts** on the GitHub calls (`requests.get(..., timeout=10)`). Without them, one hung request eats the Lambda's entire timeout.
- **Cache:** before excavating, check whether `expedientes/{owner}-{repo}-{date}.html` already exists in S3. If it does, return it. Also store the `.md` next to the HTML: without it, a cache hit can't return the narrative to the frontend. It saves tokens and makes repeat demos instantaneous.
- **Throttling** in API Gateway and a **billing alarm**.
- **CORS restricted** to the Vercel domain, not `"*"`.
- **Structured logging:** log the repo, the duration and the token usage (it comes in `resp["usage"]`). Useful for debugging and for showing off metrics.

### Acceptance criterion

These five inputs return clear errors instead of a 500:

```
https://github.com/esto/no-existe-jamas
https://gitlab.com/algo/otro
no soy una url
""  (empty)
https://github.com/  (no repo)
```

---

## Phase 7 — Demo and documentation

**Goal:** the project should be understandable in two minutes.

### Tasks

1. Update the READMEs (`README.md` and `README.es.md`) with the real Vercel frontend URL and screenshots of a generated case file.
2. Generate 3 or 4 case files for recognizable repos and save the links. They're your best argument.
3. Architecture diagram. An ASCII diagram in the README works; one made in draw.io looks better.
4. A 2-minute video: problem → live demo → architecture → one interesting technical decision.
5. Documented cleanup commands: `sam delete --stack-name codebase-archaeologist` from `backend/`, and delete the project on Vercel.

### Acceptance criterion

Someone landing on the repo understands what it does, why it exists and how it's built, without running anything.

---

## Suggested schedule

**Friday evening (1 h)** — Phase 0. Request model access and create the token. Close the laptop.

**Saturday morning (4 h)** — Phases 1 and 2. It's the longest block and the one demanding the most focus. You finish with a good-looking HTML file on your disk.

**Saturday afternoon (3 h)** — Phases 3 and 4. By the end of Saturday you have a working public endpoint.

**Sunday morning (4 h)** — Phases 5 and 6.

**Sunday afternoon (1 h)** — Phase 7.

---

## How to cut scope if you're running out of time

In order of what to sacrifice first:

1. **Frontend** — deploy the backend only and demo with `curl`. You lose the pretty demo, not the functionality.
2. **Cache** — it's an optimization, not a feature.
3. **API Gateway** — a Lambda Function URL gives you an HTTPS endpoint with one line of YAML and also eliminates the 29 s timeout problem.

What is **not** cut under any circumstances:

- The quality of the prompt. It is the entire product.
- The design of the case file. It's the only thing people are going to look at.
- The error handling in Phase 6. A demo that crashes live erases everything else.
