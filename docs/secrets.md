# Secrets: Infisical

KAN-899. Every secret the team shares lives in Infisical (Infisical Cloud,
US region, Free plan). GitHub and Cloudflare hold copies that Infisical or a
workflow writes. A copy can be lost; the value in Infisical cannot.

**Status (2026-11-21): the `/api` sync is on and checked, and `deploy.yml`
and `publish-engine.yml` read its `API_*` secrets, as do the scrape, the
purge and the job alerts. The `/github` sync is on and holds 3 of its 8
keys** (Syncs). Developers pull their `.env` files with `npm run env`. The
`/web` sync is still open, and so are the Apple keys of the
`auto-apply-desktop` environment (end of this file).
A key that no folder holds yet is still set with `gh secret set`.

## Rules

- **Infisical is the only place a person types a secret.** Once a key is in
  a folder that syncs, never set its GitHub secret or Worker secret by hand:
  the next sync or deploy overwrites it.
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
any number of projects, 3 environments per project and 10 syncs.

**Every team member is an Admin of the organization and of all three
projects** (2026-11-27, the team's choice), so anyone on the team can read
any value, the deploy, publishing and signing keys included. The projects
split where values go (what `npm run env` pulls, what each sync carries),
not who may read them. These docs call the projects by the first column's
names; Infisical's project list shows the second column's.

| Project | Name in Infisical | Environment (slug) | Folders |
|---|---|---|---|
| `workit-dev` | `dev` | `dev` | `/root_env`, `/frontend_env`, `/scraper` |
| `workit-prod` | `prod` | `prod` | `/api`, `/web`, `/github`, `/auto-apply-desktop`, `/team-computer`, `/ec2-job-alerts` |
| `workit-logins` | `Logins` | one | one folder per service |

Where each folder goes:

| Folder | Goes to | How |
|---|---|---|
| `workit-dev/root_env` | the root `.env` on each developer's computer | `npm run env` (below) |
| `workit-dev/frontend_env` | `frontend/.env` on each developer's computer | `npm run env` |
| `workit-dev/scraper` | the shell that runs a scraper script | `infisical sm run` |
| `workit-prod/api` | GitHub repo secrets named `API_*`, then the `workit-api` Worker (the Python API) | sync with key schema `API_{{secretKey}}`; `deploy.yml` sends them on |
| `workit-prod/web` | GitHub repo secrets named `WEB_*`, then the `workit-web` Worker (the website) | sync with key schema `WEB_{{secretKey}}`; `deploy.yml` sends them on |
| `workit-prod/github` | GitHub repo secrets, same names | sync, scope Repository |
| `workit-prod/auto-apply-desktop` | secrets of the GitHub environment `auto-apply-desktop` | sync, scope Repository Environment |
| `workit-prod/team-computer` | `C:\workit-bank-job\.env` on the team computer (`ASGAMINGPC`) | an Admin exports it with the CLI and copies the file there (References) |
| `workit-prod/ec2-job-alerts` | the EC2 crontab's environment | an Admin exports it with the CLI and copies the values there |

- **`/github` and `/auto-apply-desktop` are separate because a sync
  pushes a whole folder to one place.** `/auto-apply-desktop` holds every
  secret that a workflow of the desktop app (WorkIt Auto Apply, KAN-723)
  reads, its signing keys too, and each one is a secret of the GitHub
  environment of the same name, which takes jobs from `main` only. A repo
  secret reaches every branch's workflows, and the `/github` sync writes
  repo secrets.
  - A job that reads one must name `environment: auto-apply-desktop`. Any other
    job, and any run from a tag or another branch, gets an empty value.
  - **The signing keys live in Infisical and the environment only,** on no
    person's computer: every installed app runs what they sign, and
    `publish-app.yml` signs each release on a GitHub Mac (D32).
  - The app itself holds no secret: anyone who installs an app can read
    what it ships, as with the extension.
- **Local development uses the production database.** `/root_env` holds the
  same `DATABASE_URL` and `SUPABASE_SERVICE_KEY` as `workit-prod/api`, so
  every developer's `.env` holds them. A separate dev Supabase project
  would close this; it is not planned yet.

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

**A workflow that needs one of these values reads its `API_*` copy**
(`secrets.API_DATABASE_URL`), never a second copy in `/github`. Then each
value is in one folder, and one change reaches the API and every
workflow.

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `DATABASE_URL` | the API, and `scrape.yml`, `retention-purge.yml` and `job-alerts.yml` | Required | Same value as `workit-dev/root_env`. |
| `SUPABASE_URL` | the API, and `publish-engine.yml` | Required | Same value as `workit-dev/root_env`. |
| `SUPABASE_SERVICE_KEY` | the API, and `publish-engine.yml` | Required | Same value as `workit-dev/root_env`. |
| `SCOUT_ENDPOINTS` | the API's Scout, and `scrape.yml`'s keyword pass, as the fallback after the team computer's own Ollama | Required: without a chain, every Scout reply is "offline" | Production's chain, which can differ from a laptop's (`scout/CLAUDE.md`). Ask whoever set `CF_API_SECRETS_JSON` (2026-10-26) before you copy a laptop's. |
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
| `FILL_ENGINE_TOKEN` | `deploy.yml`, `publish-extension.yml`, `publish-engine.yml` (they fail without it); `ci.yml`, `extension-nightly.yml`, `apply-nightly.yml`, `live-canary.yml` (they skip the engine's jobs) | Required: every deploy | A fine-grained GitHub token, Contents read-only, on `workitjobs/fill-engine` only. GitHub shows it once. Note its owner and expiry date in Infisical: it stops on that date, and every deploy with it. The one in use (set 2026-11-03) is not on the `workitjobs` organization's list of fine-grained tokens (2026-11-21), so it is likely a classic token, whose owner and expiry the organization cannot see: replace it (Still open). |
| `CHROME_CLIENT_ID` | `publish-extension.yml` | Required to publish the extension | Google Cloud Console, Credentials, the Chrome Web Store OAuth client. Not a secret. |
| `CHROME_CLIENT_SECRET` | `publish-extension.yml` | Required to publish the extension | The same client. If Google does not show it, add a new secret and disable the old one after a publish works. |
| `CHROME_REFRESH_TOKEN` | `publish-extension.yml` | Required to publish the extension | Mint a new one with that client (`.github/CLAUDE.md`, Publish extension). |
| `CHROME_EXTENSION_ID` | `publish-extension.yml` | Required to publish the extension | `cpklhdkoafegnndlafmiceehfloodjgi`. Not a secret. |
| `CHROME_PUBLISHER_ID` | `publish-extension.yml` | Required to publish the extension | Chrome Web Store Developer Dashboard, Publisher, Settings. Not a secret. |

Not in this folder: `DATABASE_URL` and `SCOUT_ENDPOINTS` (the workflows
read `/api`'s, as `API_DATABASE_URL` and `API_SCOUT_ENDPOINTS`; both
were deleted from this folder and from GitHub on 2026-11-21),
`SCOUT_ENDPOINTS_LARGE` and `SCOUT_ENDPOINTS_SMALL`
(no workflow reads them; `scrape.yml` writes its small chain itself, as the
computer's Ollama; the repo copies were deleted on 2026-11-20),
`CF_API_SECRETS_JSON` (`/api` replaced it; deleted on 2026-11-21), `APPLY_ENGINE_SIGNING_KEY` (`/auto-apply-desktop`),
`GEMINI_API_KEY` (no workflow reads it).

### `workit-prod/auto-apply-desktop` (environment `auto-apply-desktop`)

| Key | Read by | Needed | Value or source |
|---|---|---|---|
| `APPLY_ENGINE_SIGNING_KEY` | `publish-engine.yml` | Required to publish the engine | The backup PEM file kept since 2026-11-17, pasted whole with its `BEGIN` and `END` lines. **Never a new key:** every installed Apply app refuses builds that a new key signs (`.github/CLAUDE.md`, Publish engine). |
| `SPARKLE_PRIVATE_KEY` | `publish-app.yml` (`apply-agent/scripts/publish_app.py`) | Required to publish the app | The app's update key: the one line `generate_keys -x` wrote for the key made on 2026-11-26, whose public half is `SPARKLE_PUBLIC_KEY` in `apply-agent/scripts/build_app.py`. **Never a new key:** every installed app refuses an update another key signs, so its students would stay on their build for good. |
| `R2_AUTO_APPLY_DESKTOP_ACCESS_KEY_ID` | `publish-app.yml` | Required to publish the app | Cloudflare dashboard, R2, Manage API tokens: a token with Object Read & Write on the `auto-apply-desktop` bucket only (2026-11-26). |
| `R2_AUTO_APPLY_DESKTOP_SECRET_ACCESS_KEY` | `publish-app.yml` | Required to publish the app | The same token's secret, which Cloudflare shows once. |
| `R2_AUTO_APPLY_DESKTOP_ENDPOINT` | `publish-app.yml` | Required to publish the app | `https://<account id>.r2.cloudflarestorage.com`, the S3 address on the same page. Not a secret. |
| `APPLE_DEVELOPER_ID_CERTIFICATE` | `publish-app.yml` | Required to publish the app | WorkIt's Developer ID Application certificate with its private key: exported from Keychain Access as a `.p12`, then `base64 -i <file>.p12`, one line. Then delete the certificate, its key and the file from the Mac (Load the Apple keys). |
| `APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD` | `publish-app.yml` | Required to publish the app | The password typed when that `.p12` was exported. |
| `APPLE_NOTARY_KEY` | `publish-app.yml` (`apply-agent/scripts/notarize_app.py`) | Required to publish the app | App Store Connect, Users and Access, Integrations, App Store Connect API: a key with the Developer role. The `.p8` file's whole text, its `BEGIN` and `END` lines included. Apple lets you download it once. |
| `APPLE_NOTARY_KEY_ID` | `publish-app.yml` | Required to publish the app | That key's ID, on the same page. Not a secret. |
| `APPLE_NOTARY_ISSUER_ID` | `publish-app.yml` | Required for a Team key; leave it out for an Individual key | The Issuer ID at the top of the Team Keys page. Not a secret. |

To check a PEM file against the key the apps hold, run this from `backend/`:
`uv run python -c "import sys; from pathlib import Path; from app.scripts.publish_engine import load_key, public_key; print(public_key(load_key(Path(sys.argv[1]))))" <PEM file>`.
It prints only the public half, which must be `PUBLIC_KEY` in
`apply-agent/src/apply/engine_download.py`.

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
folder `/api` of environment `prod`". The CLI fills references in by
default. The tables above mark each reference.

- **Never use a reference in a folder that syncs.** The `/github` sync
  wrote `${prod.api.DATABASE_URL}` to GitHub as that text, 24 characters,
  not as the value (2026-11-21), and Infisical's docs do not say a sync
  fills references in. Every workflow that reads the database would have
  failed. A workflow that needs an `/api` value reads its `API_*` copy
  instead (`workit-prod/api`).
- **Copy `/team-computer` and `/ec2-job-alerts` with the CLI** (`infisical
  export --projectId <workit-prod ID> --env prod --path /team-computer
  --format dotenv`), which fills in
  their references. On the first export, check that `DATABASE_URL` is the
  URL itself, not `${...}`.
- **References work inside one project only** on the Free plan. A value in
  both projects is typed in each and changed in both: `DATABASE_URL`,
  `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (in `workit-dev/root_env` and
  `workit-prod/api`), and `DIRECT_URL` (in `workit-dev/root_env` and
  `workit-prod/team-computer`). Each prod copy has the comment "also in
  workit-dev/root_env".
- **Never use a secret import in a folder that syncs** either. An import
  brings every key of the other folder, and the sync would push them all.
- **A `$` in a value can be read as a reference.** Check a new password for
  `$` before you save it.

## Access

**Join:**

1. An Admin invites the person's email in the organization's member
   settings, as Admin.
2. The person accepts the invite and makes their Infisical account (US
   region) with that same email. An account under another email is another
   person to Infisical, outside the organization.
3. The person joins each of the three projects as Admin: in Infisical, All
   Projects, then Join as Admin on each. **The organization's Admin role
   gives no project access by itself:** on 2026-11-26 every teammate was an
   organization Admin in no project, and `npm run env` failed with 403 for
   each of them.

**Leave:** the same day, an Admin removes the person from the organization.
Then rotate every value: as an Admin, they could read every project.

## Get your local `.env` files

`npm run env` writes two files only: the root `.env` from
`workit-dev/root_env` and `frontend/.env` from `/frontend_env`
(`frontend/scripts/env.mjs`, which holds the project ID). It prints the
names of the keys that are new or changed, never a value. Production
values never reach a laptop: the syncs and the deploy carry them to GitHub
and Cloudflare (Change a value).

**First time.** Steps 1 and 2 are once per person, steps 3 to 5 once per
computer:

1. Accept the email invite to the Infisical organization. Make your
   account in the US region with the email the invite went to, and turn
   on two-factor sign-in.
2. Join the three projects (Access): All Projects, then Join as Admin on
   `dev`, `prod` and `Logins`. Until you are in `dev`, `npm run env` says
   you have no access.
3. Install the CLI. On macOS, run `brew install infisical/get-cli/infisical`.
   On Windows, run `winget install infisical`.
4. Run `infisical login` and pick "Infisical Cloud (US Region)". The browser
   opens; sign in as yourself. `infisical login status` checks the login.
5. From the repo root, run:

   ```
   npm run env
   ```

**After that, whenever someone says a value changed**, run `npm run env`
again in each checkout you use.

**To change or add a value, change it in Infisical, never only in your
`.env`,** then tell the team the key's name (Change a value). A value you
change only in your own `.env` is replaced on your next pull when
Infisical has that key.

- **It keeps the lines Infisical does not have** (`LOCAL_FILES_DIR`, or
  anything only your computer needs), under a comment at the file's end. A
  key Infisical has always takes Infisical's value: a local value under the
  same name is replaced on the next pull.
- **A failed pull writes nothing.** Not signed in, no access to
  `workit-dev`, or an empty folder leaves both files as they were, and the
  message says which.
- **`frontend/.env.local` wins over `frontend/.env`** in Next. If it sets a
  key that Infisical has, `npm run env` names it: delete those lines there,
  or the app keeps the old values.
- **Each checkout pulls for itself.** Run it in a worktree too. `npm run
  worktree` still copies the primary checkout's files into a new one.
- **Without npm**, the same pull is `infisical export --projectId <ID>
  --env dev --path /root_env --format dotenv` (newer CLIs also call it
  `infisical sm secrets export`), which prints the file and keeps no local
  line.

## Change a value

**A developer only ever runs `npm run env`.** A dev value changes in
Infisical and reaches each laptop on its owner's next pull. A production
value never reaches a laptop: each row below says how it reaches GitHub,
Cloudflare, the team computer or EC2.

| Change | Steps |
|---|---|
| A dev value | Change it in `workit-dev`. Tell the team to run `npm run env` ("pull, `DATABASE_URL` changed": the name, never the value). |
| A GitHub secret | Change or add it in `workit-prod/github`. The sync pushes it, and the next run uses it. |
| An API value | Change it in `workit-prod/api`. Run "Deploy to Cloudflare" from the Actions tab: a running Container keeps its old values until a deploy restarts it. |
| A value in more than one folder | Change it in each folder whose copy has the comment "also in ..." (References): `/api`'s `DATABASE_URL` is also in `workit-dev/root_env`. The references in `/team-computer` and `/ec2-job-alerts` follow by themselves. Then export those two folders with the CLI to the team computer's `.env` and the EC2 crontab, and restart the bank job (`backend/CLAUDE.md`, Deployment). |
| A new key | Put it in its Infisical folder. In the same PR that first reads it, add it to its folder's table here and its name, with no value, to the `.env.example` beside its file. A new API setting also joins the Worker's `FORWARDED` list in that PR: without it, the Container never sees the value. Then tell the team to run `npm run env`. |
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

## Load the Apple keys (W8 step 2, KAN-950)

`publish-app.yml` signs the Mac app with WorkIt's Developer ID and has
Apple notarize it with five keys in `workit-prod/auto-apply-desktop`,
which the sync copies to the `auto-apply-desktop` environment. Only the
Account Holder of WorkIt's Apple Developer account can make them. Make
them on a Mac; at the end, nothing of them stays on it.

1. **Enroll** at https://developer.apple.com/programs/enroll as an
   individual (D20 of `desktop_application_auto_apply.md`), $99 a year.
   Apple checks the identity first, which can take a day or two.
2. **Make the certificate request.** Keychain Access, the Keychain Access
   menu, Certificate Assistant, Request a Certificate From a Certificate
   Authority: your email, Common Name "WorkIt Auto Apply", Saved to disk.
   This also puts the certificate's private key in your login keychain.
3. **Make the certificate.** developer.apple.com, Account, Certificates,
   +, Developer ID Application, G2 Sub-CA, upload the request, then
   Download. Open the `.cer`: Keychain Access puts it with its key under
   My Certificates, as "Developer ID Application: <your name> (<team
   ID>)".
4. **Export it with its key.** In My Certificates, select that
   certificate, then File, Export Items, format Personal Information
   Exchange (`.p12`), with a new strong password.
5. **Put both in Infisical.** `base64 -i <file>.p12 | pbcopy`, and paste
   it as `APPLE_DEVELOPER_ID_CERTIFICATE`. The password goes in
   `APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD`.
6. **Make the notarization key.** https://appstoreconnect.apple.com,
   Users and Access, Integrations, App Store Connect API. The first time,
   request access. Team Keys, +, the name "publish-app" and the Developer
   access, Generate, then Download API Key: Apple allows one download.
   The `.p8` file's whole text goes in `APPLE_NOTARY_KEY`, the Key ID in
   `APPLE_NOTARY_KEY_ID`, and the Issuer ID above the list in
   `APPLE_NOTARY_ISSUER_ID`. If the account offers only Individual Keys,
   make one there and leave `APPLE_NOTARY_ISSUER_ID` out.
7. **Delete them from the Mac.** In Keychain Access, delete the
   certificate and its private key. Delete the `.p12`, the `.cer`, the
   request and the `.p8` files. The signing keys live on no person's
   computer (Layout, `/auto-apply-desktop`).
8. **Check.** `gh api
   repos/workitjobs/workit/environments/auto-apply-desktop/secrets --jq
   '.secrets[].name'` lists the five new keys, ten in all. Then run
   `publish-app.yml`: each failure names the key to fix and how
   (`../.github/CLAUDE.md`, Publish WorkIt Auto Apply).

**The certificate lasts five years.** Make the next one the same way
before it expires, and replace the two certificate keys. A new
certificate from the same team keeps every installed app updating and
keeps its permissions (Screen Recording): macOS and Sparkle tie both to
the team, not to one certificate. A revoked certificate or key is made
again the same way.

**Apple asks the Account Holder to accept each new agreement** at
developer.apple.com, Account. Until then, notarizing fails with HTTP 403.

## Syncs

The repo connects through Infisical's GitHub App, installed on the
`workitjobs` organization for the `workit` repo only. Each sync is one
folder to one place:

| Sync | Scope | Key schema | State (2026-11-21) |
|---|---|---|---|
| `workit-prod/api` | Repository | `API_{{secretKey}}` | on, checked |
| `workit-prod/github` | Repository | none | on, with `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` (a deploy passed with them) and `CHROME_EXTENSION_ID`; `DATABASE_URL` and `SCOUT_ENDPOINTS` only until this change is on `main` (Still open) |
| `workit-prod/web` | Repository | `WEB_{{secretKey}}` | off: the folder is empty until `GOOGLE_CLIENT_SECRET` is issued again |
| `workit-prod/auto-apply-desktop` | Repository Environment, `auto-apply-desktop` | none | on, checked 2026-11-26: the environment lists the folder's 5 keys |

**Only GitHub holds these keys (2026-11-21):** `FILL_ENGINE_TOKEN`,
`CHROME_CLIENT_ID`, `CHROME_CLIENT_SECRET`, `CHROME_PUBLISHER_ID` and
`CHROME_REFRESH_TOKEN`. The `/github` sync leaves them alone. GitHub cannot
show a secret, so a deleted one is lost and is issued again from its
source (the `/github` table). Put each one in `/github` when it is issued
again.

- **Set the key schema before a sync first runs.** The `/api` sync first
  ran without one (2026-11-20): it wrote `/api`'s keys to GitHub under
  their plain names, over the live `DATABASE_URL` and `SCOUT_ENDPOINTS`
  that `scrape.yml` and the job workflows read, and added
  `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` and `WORKIT_ADMINS` repo secrets
  that nothing reads. A sync leaves names outside its schema alone, so
  those strays were deleted by hand (`gh secret delete`).
- **Check the scope before a sync first runs.** `/auto-apply-desktop`
  first ran with scope Repository (2026-11-26): it wrote the folder's
  keys, the update key and the engine's signing key among them, as repo
  secrets, which every branch's workflows can read, and the environment
  got none. A changed scope leaves the old copies behind, so they were
  deleted by hand; no run in that time named them.
- **Turn on "Disable Secret Deletion" on every one.** The only initial
  sync behavior, Overwrite Destination Secrets, removes every GitHub secret
  that the folder does not hold. `/github` has no key schema, so it would
  delete the `API_*` secrets and every repo secret not yet in Infisical.
  The cost: a key deleted from a folder stays in GitHub, so delete that
  copy too (`gh secret delete <name>`), or it lingers unused.
- **A sync writes real GitHub secrets,** as `gh secret set` does. A
  workflow reads GitHub's copy and never asks Infisical, so a change in
  Infisical reaches a run only through the sync.
- **Turn a sync on only once each value in its folder is right:** the sync
  overwrites the working GitHub copy. With deletion off, a secret the
  folder does not hold yet stays as it is.
- **Never add a key without its real value.** The sync writes every key
  in the folder, so an empty key or a placeholder ("TODO") replaces the
  working GitHub copy. A placeholder `CLOUDFLARE_API_TOKEN` stops every
  deploy. Leave a key out until you have its value.
- **Never put a reference in a folder that syncs** (References): the
  `/github` sync wrote `DATABASE_URL` and `SCOUT_ENDPOINTS` as their
  reference text on 2026-11-21, and the check below caught it.
- **Check a sync without seeing a value.** The run "Secrets check"
  (https://github.com/workitjobs/workit/actions/runs/44858092532, from
  commit `a5dcec4e`) prints each `API_*`, `WEB_*`, `DATABASE_URL` and
  `SCOUT_ENDPOINTS` secret's length, never its value, flags a value still
  written `${...}`, and lists the names the deploy would send. Re-run it
  from the Actions tab: a re-run uses its own commit, so it works after
  the workflow file is gone. GitHub can hold it for a person's approval.
  It does not check `CLOUDFLARE_*` or `CHROME_*`: a deploy checks the
  Cloudflare pair, and the extension's next publish checks the Chrome
  keys.

## Still open

1. **Replace `FILL_ENGINE_TOKEN`** before it expires on a date nobody
   knows. Make a fine-grained token: resource owner `workitjobs`, only the
   `fill-engine` repository, Contents read-only, with an expiry date. Put
   it in `/github` with a comment naming its owner and that date, then run
   "Deploy to Cloudflare" on `main`. Once it passes, ask the team who set
   the old one on 2026-11-03 and have them revoke it.
2. **Revoke the old Cloudflare token.** "Deploy to Cloudflare" passed with
   the new one on 2026-11-21.
3. **The `/web` sync,** when `GOOGLE_CLIENT_SECRET` is issued again.
4. **Load the five `APPLE_*` keys** (W8 step 2, KAN-950), once the Apple
   enrollment is done (Load the Apple keys). Until then, every run of
   `publish-app.yml` stops at its first signing step.
5. **Rotate** every value that was sent over Slack.
