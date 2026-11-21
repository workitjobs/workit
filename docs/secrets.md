# Secrets: Infisical

KAN-899. Every secret the team shares lives in Infisical (Infisical Cloud,
US region, Free plan). GitHub and Cloudflare hold copies that Infisical or a
workflow writes. A copy can be lost; the value in Infisical cannot.

**Status (2026-11-20): Infisical holds the values, nothing reads them yet.**
The GitHub syncs, the `deploy.yml` and `publish-engine.yml` changes and
`npm run env` are still open (end of this file). Until each one lands, the
old way in `.github/CLAUDE.md` still applies to it: GitHub secrets are set
with `gh secret set`, and the API's values go in `CF_API_SECRETS_JSON`.

## Rules

- **Infisical is the only place a person types a secret.** Once a folder's
  sync is on, never set its GitHub secrets or Worker secrets by hand: the
  next sync or deploy overwrites them.
- **"Every key, folder by folder" below is the list.** A key goes in the
  folder its table names and nowhere else. A new key joins a table in the
  same PR that first reads it.
- **Never send a secret over Slack, email or a PR.** Give access instead, or
  use Infisical's secret sharing (a one-time link). A message that says
  "pull, `DATABASE_URL` changed" carries no value and is fine.
- **One Infisical account per person.** Nobody shares a login. Each account
  turns on two-factor sign-in.
- **Rotate every value that was ever sent over Slack** (issue a new one at
  the provider, put it in Infisical, revoke the old one).

## Layout

The Free plan allows 5 identities (people and machine identities together),
any number of projects, 3 environments per project and 10 syncs. The
built-in roles (Admin, Member, Viewer, No Access) cover a whole project, so
the split by who may read is a split into projects.

| Project | Who | Environment (slug) | Folders |
|---|---|---|---|
| `workit-dev` | everyone, as Member | `dev` | `/root_env`, `/frontend_env`, `/scraper` |
| `workit-prod` | Admins only | `prod` | `/api`, `/web`, `/github`, `/desktop-fill-engine`, `/team-computer`, `/ec2-job-alerts` |
| `workit-logins` | Admins only | one | one folder per service |

Where each folder goes:

| Folder | Goes to | How |
|---|---|---|
| `workit-dev/root_env` | the root `.env` on each developer's computer | `infisical sm secrets export` (below) |
| `workit-dev/frontend_env` | `frontend/.env` on each developer's computer | `infisical sm secrets export` |
| `workit-dev/scraper` | the shell that runs a scraper script | `infisical sm run` |
| `workit-prod/api` | GitHub repo secrets named `API_*`, then the `workit-api` Worker (the Python API) | sync with key schema `API_{{secretKey}}`; `deploy.yml` sends them on |
| `workit-prod/web` | GitHub repo secrets named `WEB_*`, then the `workit-web` Worker (the website) | sync with key schema `WEB_{{secretKey}}`; `deploy.yml` sends them on |
| `workit-prod/github` | GitHub repo secrets, same names | sync, scope Repository |
| `workit-prod/desktop-fill-engine` | secrets of the GitHub environment `apply-engine` | sync, scope Repository Environment |
| `workit-prod/team-computer` | `C:\workit-bank-job\.env` on the team computer (`ASGAMINGPC`) | an Admin copies it by hand |
| `workit-prod/ec2-job-alerts` | the EC2 crontab's environment | an Admin copies it by hand |

- **`/github` and `/desktop-fill-engine` are separate because a sync
  pushes a whole folder to one place.** `/desktop-fill-engine` holds every
  build and publish secret of the desktop app (WorkIt Auto Apply, KAN-723),
  and each one is an environment secret, never a repo secret: the
  `apply-engine` environment takes jobs from `main` only, and a repo secret
  reaches every branch's workflows. In `/github`, the repo-scoped sync would
  make them repo secrets. Keep the GitHub environment's name
  `apply-engine`, which `publish-engine.yml` and `.github/CLAUDE.md` name.
  - A job that reads one must name `environment: apply-engine`. Any other
    job, and any run from a tag or another branch, gets an empty value.
  - The app itself holds no secret: anyone who installs an app can read
    what it ships, as with the extension.
- **Local development uses the production database.** `/root_env` holds the
  same `DATABASE_URL` and `SUPABASE_SERVICE_KEY` as `workit-prod/api`, so
  every member can read them. The split protects the deploy and publishing
  tokens, not the database. A separate dev Supabase project would close
  this; it is not planned yet.

## Every key, folder by folder

**Needed** is one of: **Required** (something fails without it),
**Optional** (unset, the code's default or a fallback applies), or **Not set
up** (leave it out until the feature is turned on). A value written as
`${...}` is a reference (next section).

### `workit-dev/root_env` (the root `.env`)

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `DATABASE_URL` | the local API, scripts, tests | Required | Supabase dashboard, Connect, transaction pooler (port 6543). Same value as `workit-prod/api`. |
| `DIRECT_URL` | Alembic (migrations, run by hand) | Required to run a migration | Supabase dashboard, Connect, session pooler (port 5432). Same value as `workit-prod/team-computer`. |
| `SUPABASE_URL` | the local API | Required | Supabase dashboard, Project Settings, API. |
| `SUPABASE_SERVICE_KEY` | the local API | Required | Same page, the service-role key. |
| `SCOUT_ENDPOINTS` | the local API's Scout | Optional: unset, Scout runs on a local Ollama | A JSON list of endpoints, each with its own `api_key` (`scout/CLAUDE.md`). Keys from the Groq console and Google AI Studio. |
| `SCOUT_ENDPOINTS_LARGE`, `SCOUT_ENDPOINTS_SMALL` | the local API's Scout | Optional: unset, the default chain | As above. |
| `TEST_ACCOUNT_EMAIL`, `TEST_ACCOUNT_PASSWORD` | tests and checks of pages behind sign-in | Required for those tests | The shared test account (`frontend/CLAUDE.md`). Never make a new one. |

Not in this folder: `EMBEDDING_PROVIDER` (**never**: the team computer's
`.env` is the only one that sets it, so a developer's API stays at `none`
and makes no vectors), `TURNSTILE_SECRET_KEY` (not set up),
`GEMINI_API_KEY` (unused), `LOCAL_FILES_DIR` (per computer, not a secret),
and `SCOUT_API_KEY`, `SCOUT_BASE_URL`, `SCOUT_MODEL`,
`SCOUT_REASONING_EFFORT` (a one-model Scout; unused once
`SCOUT_ENDPOINTS` is set).

### `workit-dev/frontend_env` (`frontend/.env`)

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | the local website | Required | `${dev.root_env.SUPABASE_URL}` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | the local website (browser) | Required | Supabase dashboard, Project Settings, API, the anon key. Public. |
| `API_URL` | the local website's server | Required | `http://localhost:8000`. Not a secret. |
| `NEXT_PUBLIC_BRANDFETCH_CLIENT_ID` | company logos | Optional: unset, logos fall back to what the scraper found | Brandfetch's developer portal, or the GitHub variable of the same name. Public. |

Not in this folder: `NEXT_PUBLIC_TURNSTILE_SITE_KEY` and
`TURNSTILE_SECRET_KEY` (not set up), `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET` (unset, a local clone signs in with Google through
Supabase, `frontend/docs/auth.md`).

### `workit-dev/scraper`

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `GROQ_API_KEY` | `scraper/label_headings.py` | Optional: only to run that script | Groq console, API Keys. |

### `workit-prod/api` (the `workit-api` Worker)

The names the API can read are the Worker's `FORWARDED` list
(`backend/cloudflare/src`); a name outside it never reaches the Container.

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `DATABASE_URL` | the API | Required | Same value as `workit-dev/root_env`. |
| `SUPABASE_URL` | the API, and `publish-engine.yml` | Required | Same value as `workit-dev/root_env`. |
| `SUPABASE_SERVICE_KEY` | the API, and `publish-engine.yml` | Required | Same value as `workit-dev/root_env`. |
| `SCOUT_ENDPOINTS` | the API's Scout | Required: without a chain, every Scout reply is "offline" | Production's chain, which can differ from a laptop's (`scout/CLAUDE.md`). Ask whoever set `CF_API_SECRETS_JSON` (2026-10-26) before you copy a laptop's. |
| `SCOUT_ENDPOINTS_LARGE`, `SCOUT_ENDPOINTS_SMALL` | the API's Scout | Optional: unset, the default chain | Only if production sets them today. |
| `WORKIT_ADMINS` | fix reports (`/admin` routes) | Optional: unset, nobody is an admin | The team writes it: WorkIt sign-in emails or account IDs, comma-separated. |
| `MIN_EXTENSION_VERSION`, `CONNECTOR_CHAT_CAP`, `CONNECTOR_LOOPBACK_REDIRECTS`, `AI_DAILY_POOL`, the `AI_*_CAP` and `AI_*_SHARE` keys, `FILL_EVENT_DAILY_CAP`, `FILL_REPORT_DAILY_CAP`, `JOB_SYSTEM_REQUEST_DAILY_CAP` | the API | Optional: `backend/app/config.py` has the defaults | Settings, not secrets. Only those production sets today. |
| `TURNSTILE_SECRET_KEY` | signup's CAPTCHA check | **Not set up** (2026-11-20) | See "Turnstile" below. |

Not in this folder: `DIRECT_URL` (**never**: migrations stay a local step),
`EMBEDDING_PROVIDER` (**never**: the deployed API makes no embeddings),
`CONNECTOR_API_URL` and `CONNECTOR_WEB_URL` (**never**: they are `vars` in
`wrangler.jsonc`, and a var and a secret cannot share a name),
`GEMINI_API_KEY` (only the embeddings code reads it, and only with
`EMBEDDING_PROVIDER=gemini`; Scout's Gemini key sits inside the chains),
`SCOUT_DAILY_TURNS` (ignored since KAN-210), and the one-model `SCOUT_API_KEY`,
`SCOUT_BASE_URL`, `SCOUT_MODEL`, `SCOUT_REASONING_EFFORT` (unused once
`SCOUT_ENDPOINTS` is set).

### `workit-prod/web` (the `workit-web` Worker)

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `GOOGLE_CLIENT_SECRET` | Google sign-in's own callback (`/auth/google/callback`) | Optional: unset, Google sign-in goes through Supabase's screen, which names supabase.co | Google Cloud Console, Credentials, the web client whose ID is in `frontend/wrangler.jsonc`. It was set on the Worker by hand. Wait for the `/web` deploy step before you replace it. |

### `workit-prod/github` (repo Actions secrets)

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `CLOUDFLARE_API_TOKEN` | `deploy.yml` | Required: every deploy | Cloudflare shows a token once. Make a new one from the "Edit Cloudflare Workers" template with the scopes in `.github/CLAUDE.md` (Deploy), then revoke the old one. |
| `CLOUDFLARE_ACCOUNT_ID` | `deploy.yml` | Required: every deploy | Cloudflare dashboard, the account's overview. Not a secret. |
| `FILL_ENGINE_TOKEN` | `deploy.yml`, `publish-extension.yml`, `publish-engine.yml` (they fail without it); `ci.yml`, `extension-nightly.yml`, `apply-nightly.yml`, `live-canary.yml` (they skip the engine's jobs) | Required: every deploy | A fine-grained GitHub token, Contents read-only, on `workitjobs/fill-engine` only. GitHub shows it once. Note its owner and expiry date in Infisical: it stops on that date, and every deploy with it. |
| `DATABASE_URL` | `scrape.yml`, `job-alerts.yml`, `retention-purge.yml` | Required | `${prod.api.DATABASE_URL}` |
| `SCOUT_ENDPOINTS` | `scrape.yml`'s keyword pass, as the fallback after the team computer's own Ollama | Required | `${prod.api.SCOUT_ENDPOINTS}` |
| `CHROME_CLIENT_ID` | `publish-extension.yml` | Required to publish the extension | Google Cloud Console, Credentials, the Chrome Web Store OAuth client. Not a secret. |
| `CHROME_CLIENT_SECRET` | `publish-extension.yml` | Required to publish the extension | The same client. If Google does not show it, add a new secret and disable the old one after a publish works. |
| `CHROME_REFRESH_TOKEN` | `publish-extension.yml` | Required to publish the extension | Mint a new one with that client (`.github/CLAUDE.md`, Publish extension). |
| `CHROME_EXTENSION_ID` | `publish-extension.yml` | Required to publish the extension | `cpklhdkoafegnndlafmiceehfloodjgi`. Not a secret. |
| `CHROME_PUBLISHER_ID` | `publish-extension.yml` | Required to publish the extension | Chrome Web Store Developer Dashboard, Publisher, Settings. Not a secret. |

Not in this folder: `SCOUT_ENDPOINTS_LARGE` and `SCOUT_ENDPOINTS_SMALL`
(no workflow reads them; `scrape.yml` writes its small chain itself, as the
computer's Ollama; GitHub still held both on 2026-11-20 and can delete
them), `CF_API_SECRETS_JSON` (replaced by `/api`; deleted once "Still open"
is done), `APPLY_ENGINE_SIGNING_KEY` (`/desktop-fill-engine`),
`GEMINI_API_KEY` (no workflow reads it).

### `workit-prod/desktop-fill-engine` (environment `apply-engine`)

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `APPLY_ENGINE_SIGNING_KEY` | `publish-engine.yml` | Required to publish the engine | The backup PEM file kept since 2026-11-17, pasted whole with its `BEGIN` and `END` lines. **Never a new key:** every installed Apply app refuses builds that a new key signs (`.github/CLAUDE.md`, Publish engine). |

The Mac app's signing and notarization secrets join this table when its
build needs them.

### `workit-prod/team-computer` (`C:\workit-bank-job\.env`)

Only the bank job (`app.scripts.embed_banks`) reads this file. The same
computer's GitHub runner gets its secrets from GitHub, not from here.

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `DATABASE_URL` | the bank job | Required | `${prod.api.DATABASE_URL}` |
| `DIRECT_URL` | the bank job, which listens for bank changes on it | Required | The session pooler (port 5432). Same value as `workit-dev/root_env`. |
| `EMBEDDING_PROVIDER` | the bank job | Required: it refuses to start with `none` | `ollama` |

### `workit-prod/ec2-job-alerts` (the EC2 crontab's environment)

The digest sends through AWS SES with the EC2 instance's role, so no AWS
key is stored anywhere.

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `DATABASE_URL` | the job-alert digest | Required | `${prod.api.DATABASE_URL}` |
| `AWS_REGION` | the digest's SES client | Optional: unset, `us-east-1` | Only if the crontab sets it. |
| `SES_FROM_EMAIL` | the digest | Optional: unset, `WorkIt <alerts@workitjobs.ai>` | Only if the crontab sets it. |
| `WEB_URL` | the links in each email | Optional: unset, `https://workitjobs.ai` | Only if the crontab sets it. |

### `workit-logins`

One folder per service (`/google`, `/supabase`, `/aws`, ...), each with
`EMAIL`, `PASSWORD` and `RECOVERY_CODES`. The team Gmail comes first,
because it owns Cloudflare. Infisical does not make two-factor codes: keep
the recovery codes here and the two-factor phone with two Admins.

### What stays out of Infisical

- The `NEXT_PUBLIC_*` repo variables and the `vars` in both
  `wrangler.jsonc` files. They are public: GitHub shows the variables, and
  git holds the `vars`.
- Personal values: Sandcastle's `.env` (`CLAUDE_CODE_OAUTH_TOKEN`,
  `JIRA_API_TOKEN`, `JIRA_EMAIL`), Apply's `APPLY_HOME` (with a developer's
  own `GROQ_API_KEY` or `GEMINI_API_KEY` for Apply), `LOCAL_FILES_DIR`.

### Turnstile

Cloudflare Turnstile is a CAPTCHA: a check that a person, not a script,
fills in the signup form. It usually runs without a puzzle. It has two
keys. The site key (`NEXT_PUBLIC_TURNSTILE_SITE_KEY`, a GitHub variable,
public) shows the check on the signup page, and the browser gets a one-time
token. The secret key (`TURNSTILE_SECRET_KEY`, in `/api`) lets the API ask
Cloudflare whether the token is real before it makes the account.

**Not set up (2026-11-20):** Cloudflare has no Turnstile widget and GitHub
has no site key, so signup works with no bot check. To turn it on, make a
widget for `workitjobs.ai` in the Cloudflare dashboard, put its site key in
the GitHub variable and its secret key in `/api`, and deploy. **Never the
secret key alone:** without the site key the form sends no token, and every
signup answers 400 (`backend/CLAUDE.md`, Deployment). If the `workit-api`
Worker lists `TURNSTILE_SECRET_KEY` today, delete it there.

## References

A value of `${prod.api.DATABASE_URL}` means "the value of `DATABASE_URL` in
folder `/api` of environment `prod`". Infisical fills it in when a value is
read. The CLI fills references in by default. The tables above mark each
reference.

- **References work inside one project only** on the Free plan. A value in
  both projects is typed in each and changed in both: `DATABASE_URL`,
  `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (in `workit-dev/root_env` and
  `workit-prod/api`), and `DIRECT_URL` (in `workit-dev/root_env` and
  `workit-prod/team-computer`). Each prod copy has the comment "also in
  workit-dev/root_env".
- **Use references, not secret imports, in a folder that syncs.** An import
  brings every key of the other folder, and the sync would push them all.
- **A `$` in a value can be read as a reference.** Check a new password for
  `$` before you save it.

## Access

**Join:** an Admin invites the person's email in the organization's member
settings. They make their own Infisical account (US region), and an Admin
adds them to `workit-dev` as Member. Only Admins join `workit-prod` and
`workit-logins`. Keep two or three Admins, so the organization survives
one leaving.

**Leave:** the same day, an Admin removes the person from the organization.
Then rotate what they could read: the `workit-dev` values for a Member,
everything for an Admin.

## Get your local `.env` files

Once per computer:

1. Install the CLI. On macOS, run `brew install infisical/get-cli/infisical`.
   On Windows, run `winget install infisical`.
2. Run `infisical login` and pick "Infisical Cloud (US Region)". The browser
   opens; sign in as yourself. `infisical login status` checks the login.

Then, from the repo root, whenever someone says a value changed:

```
infisical sm secrets export --projectId <workit-dev project ID> --env dev --path /root_env --format dotenv --output-file .env
infisical sm secrets export --projectId <workit-dev project ID> --env dev --path /frontend_env --format dotenv --output-file frontend/.env
```

The project ID is in the project's settings in Infisical; it is not a
secret. Older CLI versions name the command `infisical export`;
`infisical --help` shows yours.

- **The export replaces the whole file.** Copy your per-machine lines
  (`LOCAL_FILES_DIR`) first and add them back. `npm run env` will keep
  them once it exists.
- **Refresh the primary checkout first.** A worktree then gets the new
  files with `npm run worktree -- --env-only`.

## Change a value

| Change | Steps |
|---|---|
| A dev value | Change it in `workit-dev`. Tell the team to pull. |
| A GitHub secret | Change it in `workit-prod/github`. The sync pushes it, and the next run uses it. |
| An API value | Change it in `workit-prod/api`. Run "Deploy to Cloudflare" from the Actions tab: a running Container keeps its old values until a deploy restarts it. |
| A value in both projects | Change it in both (References). The references in `/github`, `/team-computer` and `/ec2-job-alerts` follow by themselves. Then copy the new value to the team computer's `.env` and the EC2 crontab by hand, and restart the bank job (`backend/CLAUDE.md`, Deployment). |
| A new key | Add it to its folder's table here, in the same PR that first reads it. A new API setting also joins the Worker's `FORWARDED` list in that PR: without it, the Container never sees the value. |
| Delete an API value | Delete it in Infisical, then in the Cloudflare dashboard (Workers, `workit-api`, Settings, Variables and Secrets). `wrangler secret bulk` never deletes. |
| Rotate a value | Issue a new value at the provider, change it as above, check that the app works, then revoke the old value. |

## First load

Upload one file per folder: open the folder, then Add New, Upload Secrets,
and drop the JSON file. A flat JSON object (`{"KEY": "value"}`) becomes
keys; a nested object would become folders. Delete each file after the
upload: it holds the values in plain text.

**A secret that works in GitHub or on a Worker can wait.** GitHub cannot
show its secrets, so a value nobody holds comes from its source in the
tables above, often as a new value. With "Disable Secret Deletion" on, a
sync leaves a secret that Infisical does not hold alone, so move each one
in when you issue it again.

**To see which names production holds,** open the Cloudflare dashboard,
Workers & Pages, the Worker (`workit-api` or `workit-web`), Settings,
Variables and Secrets. It lists every secret's name, never its value. For
GitHub, `gh secret list` does the same.

## Still open

1. **GitHub syncs.** Connect the repo through Infisical's GitHub App. Make
   four syncs: `/github` (scope Repository), `/api` (key schema
   `API_{{secretKey}}`), `/web` (key schema `WEB_{{secretKey}}`) and
   `/desktop-fill-engine` (scope Repository Environment, `apply-engine`).
   **Set the key schema before a sync first runs.** The `/api` sync first
   ran without one (2026-11-20): it wrote `/api`'s keys to GitHub under
   their plain names, over the live `DATABASE_URL` and `SCOUT_ENDPOINTS`
   that `scrape.yml` and the job workflows read, and added
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` and `WORKIT_ADMINS` repo secrets
   that nothing reads. A sync leaves names outside its schema alone, so
   such strays are deleted by hand (`gh secret delete`).
   **Turn on "Disable Secret Deletion" on every one.** The only initial
   sync behavior, Overwrite Destination Secrets, removes every GitHub secret
   that the folder does not hold. `/github` has no key schema, so it would
   delete `CF_API_SECRETS_JSON` and the `API_*` and `WEB_*` secrets. Turn a
   sync on only once each value in its folder is right, because the sync
   overwrites GitHub. Infisical's docs do not say whether a sync fills in
   references. Check it once with a test key and a workflow step that
   prints the secret's length.
2. **`deploy.yml`.** The API job's "Set runtime secrets" step builds its
   JSON from the `API_*` secrets
   (`${{ toJSON(secrets) }}` piped through
   `jq 'with_entries(select(.key | startswith("API_")) | .key |= ltrimstr("API_"))'`).
   The web job gets the same step for `WEB_*`.
3. **`publish-engine.yml`** reads `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
   out of `CF_API_SECRETS_JSON`. It must read `API_SUPABASE_URL` and
   `API_SUPABASE_SERVICE_KEY` **before** `CF_API_SECRETS_JSON` is deleted.
4. **`npm run env`.** A Node script under `frontend/scripts/`, with its
   forwarder in the root `package.json`. It runs the two exports and keeps
   any line Infisical does not have.
5. **Rotate** every value that was sent over Slack.
6. Then delete `CF_API_SECRETS_JSON` and the unused `SCOUT_ENDPOINTS_LARGE`
   and `SCOUT_ENDPOINTS_SMALL` repo secrets, and update `.github/CLAUDE.md`
   and `backend/CLAUDE.md` (Deployment) to point here.
