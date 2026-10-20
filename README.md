# CareerScout Germany

A personal Streamlit workspace for finding real Werkstudent, internship and research-assistant opportunities in Germany, understanding language requirements, and tracking applications. Built around an international AI master's student profile.

The app queries public job APIs when you click **Find Jobs** or **Refresh Jobs**. There is no demo-job fallback, no paid service required, and no external AI needed for matching.

## What you can do

- Discover jobs from Arbeitnow and configured Greenhouse/Lever employer boards; edit board names in Settings without changing code.
- Filter by category, job type, city, work arrangement, language evidence, posting age, skills, employer, source, score, published salary text, pay certainty and work-authorization wording.
- See six weighted score components, matching/missing skills, evidence, obstacles and application advice.
- Switch among the supplied default profile, a reviewed CV profile and a manually edited profile.
- Parse text PDFs and DOCX CVs locally on the app server; preview/correct the text and explicitly review profile fields.
- Save jobs in named collections, maintain application stages, notes and dates, and export the full change history.
- Explore six interactive Plotly charts; download CSV and Excel results.
- Persist locally in SQLite or use hosted PostgreSQL; refresh without a browser through the included CLI and optional GitHub Actions scheduler.
- Optionally ask for per-job AI advice using your API key, after previewing the payload and authorizing that request.

**Important scope:** this is a single-user workspace, not a multi-tenant service. Everyone with access shares its jobs, saved profile and application notes. Use private hosting access controls. Do not expose a personal workspace publicly.

## Install on Windows with VS Code

### 1. Install the tools

1. Install a supported **64-bit Python 3.11 or newer** from [python.org](https://www.python.org/downloads/windows/). Enable the Python launcher and “Add Python to PATH” when available. Python 3.11 is the baseline used in the commands below.
2. Install [Git for Windows](https://git-scm.com/download/win).
3. Install [Visual Studio Code](https://code.visualstudio.com/) and its Microsoft Python extension.
4. Restart VS Code after installing Python/Git so its terminal picks up PATH changes.

### 2. Clone and open the project

Open VS Code → **Terminal → New Terminal** and select **PowerShell**. Run:

```powershell
git clone https://github.com/Zobia02/AI-scrapper-Made-for-jobs-search-in-bielelfeld-.git careerscout-germany
cd careerscout-germany
code .
```

The final argument gives the local folder the friendly name `careerscout-germany`. If the repository is not yet pushed, use the existing local checkout instead:

```powershell
cd "C:\Users\HP\AI-scrapper-Made-for-jobs-search-in-bielelfeld-"
code .
```

All remaining commands must run **inside the folder containing `app.py` and `requirements.txt`**. Do not create another nested project folder.

### 3. Create and activate a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If you installed a different Python version, replace `-3.11`, for example `py -3.14 -m venv .venv`. Use `py -0p` to list installed runtimes. If your installation has no launcher, use `python -m venv .venv`.

In VS Code, press **Ctrl+Shift+P → Python: Select Interpreter**, then choose `.venv\Scripts\python.exe`.

### If PowerShell blocks activation

Activation is optional. This solution requires **no execution-policy changes**:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Alternatively, allow scripts only for the current PowerShell process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

No administrator privileges or system-wide policy changes are needed.

### 4. Open the app

Visit **http://localhost:8501**. Keep the terminal open while using the app. Stop it with **Ctrl+C**.
The default theme is light. Streamlit's top-right settings menu can switch to its built-in dark theme.

For a fresh checkout, install dependencies first. The completed local development checkout already contains an isolated `.venv`.

## Your first search

1. Open **Discover Jobs** and click **Find Jobs**. A progress bar shows each public API.
2. Wait for the source summary. Check **Source health & coverage** for individual successes/errors.
3. The default language filters include confirmed English compatibility and no explicit German requirement found. The latter is **uncertain**, not evidence that German is unnecessary.
4. Choose a city, category and other filters in the sidebar. Results are ranked by score. Search pagination is separate from API pagination.
5. **View details & match evidence** explains the score and shows the original listing text.
6. **Apply ↗** opens the real URL supplied by the source. Review the advert and apply on that site yourself.
7. **Save job** adds it to **Saved Jobs**. You can organize jobs into collections.
8. **Track application** creates an Interested entry. In **Application Tracker**, set Applied, Assessment, Interview, Offer or Rejected; add your notes, application/follow-up dates and confirmation link.
9. Download CSV/Excel from results or saved jobs. Application history exports include all recorded edits and original source/application links.
10. Use **Refresh Jobs** when you want fresh data. Saving/filtering does not trigger collection.

The default is to include internships with **unknown pay**, clearly labelled. Select **Confirmed paid opportunities only** to exclude them. Missing salary or a working-student title alone never proves payment. No currency or hourly/monthly salary conversion is guessed; the salary filter matches published salary text.

Posting-age filters use actual publication timestamps only. Greenhouse's update time is not a publication time. Listings without a posting date display the discovery date and are excluded by “Last 7 days” and similar filters.

## CV and profile matching

In **Settings / My Profile**, choose:

- **My default profile**: the education, technical skills, projects, languages and preferred cities supplied for this project.
- **My uploaded CV**: upload a PDF or DOCX, click Extract CV text, review/correct the preview, then Build editable CV profile. The keyword parser proposes recognized skills. Enter/review education, experience, student status and languages yourself before saving.
- **My manually edited profile**: edit the default or saved profile fields directly.

Click **Save and use this profile** to persist reviewed fields and recalculate scores. Raw uploaded files and the full extracted CV text are held in session memory, not written to the database. Reviewed fields you save are persisted. Scanned PDFs need OCR first; you can paste corrected text into the preview. Limits: 8 MB, PDF at most 30 pages, DOCX expanded size at most 30 MB.

“Local extraction” means extraction on the **Streamlit server**. On your computer that is local; on Community Cloud the upload goes to the hosting server. It is not sent to an external AI service automatically.

### Transparent scoring

| Component | Default weight | Rule |
|---|---:|---|
| Skills | 35% | Recognized advertised skills present in the profile / all recognized advertised skills |
| Role/title | 20% | Best preferred-role token overlap with the job title |
| Language | 20% | Confirmed English 100; no explicit German wording 45 (uncertainty prior); optional German 65; unknown 0; required German 0 for A1 |
| Experience/education | 10% | Explicit student/degree evidence for an enrolled student 85; possible advanced/multi-year obstacle 20; unknown 0 |
| Location | 10% | Preferred recognized city 100; another verified German location 60 |
| Posting recency | 5% | Linear from 100 today to 0 after 30 days; unknown/future date 0 |

Final score = sum(component × weight / 100). All six components and their contributions are visible. Weights must total 100. For profiles with German B2 or higher, a German-required role receives only a tentative 55 language score; exact level compatibility still needs manual review.

The score is an explainable heuristic, **not** a probability of acceptance. The engine does not infer years of experience, immigration eligibility or degree equivalence. Skills in an advert can be optional or company boilerplate; missing skills are labelled “absent from your profile,” not mandatory deficits. Language rules are conservative but cannot reliably interpret every wording or conditional requirement. Inspect the evidence.

### Optional AI advice

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` and optionally `OPENAI_MODEL`. Or use Streamlit Secrets. No key is required for discovery, ranking, CV parsing, exports or tracking.

In a job's details, enable **Preview the data for AI advice**, inspect the exact payload, authorize sending those fields to OpenAI, then click Generate AI advice. The raw CV file is never sent; saved education/experience text may contain personal data, so review it. The request uses the [Responses API](https://developers.openai.com/api/docs/guides/text), `store=false`, no tools and a bounded output. Provider data policies still apply; `store=false` is not a promise of zero provider retention. Advice does not overwrite deterministic scores. API failures leave all local features usable.

## Sources and adding employers

Default source families are Arbeitnow, Greenhouse and Lever (global/EU). Ashby code is included but disabled after its policy endpoint was inaccessible during verification. See [docs/SOURCES.md](docs/SOURCES.md) for primary access documentation and unsupported platforms.

In Settings → Job sources & coverage, enter a board name per line:

- Greenhouse: the name after the hostname in an employer's official `job-boards.greenhouse.io/<board>` career URL.
- Lever global/EU: the exact name from `jobs.lever.co/<board>` or `jobs.eu.lever.co/<board>`, including any trailing hyphen.
- Ashby: the name from `jobs.ashbyhq.com/<board>`; collection proceeds only if the runtime policy check allows it.

Do not enter a full URL, an API key or guessed credentials. Up to 40 employer boards can be configured. Source availability and employer hiring change; 404 usually means the board moved. The app stops on access restrictions and does not bypass them.

## Storage and backups

Without `DATABASE_URL`, the app creates `data/careerscout.db`. SQLAlchemy stores jobs, source aliases, discovery/verification times, saved collections, reviewed profiles/preferences, application state, append-only application snapshots and refresh health.

Deduplication uses source identity, canonical application URL (tracking parameters removed, identity parameters preserved), then normalized company/title/location across different sources. Separate same-board requisitions are preserved. Conservative cross-board deduplication can still merge genuinely distinct but identically named positions; inspect the listed source URLs.

No collection routine deletes jobs or application history. Unsave only removes the saved flag. The app marks a position **potentially expired** after two complete board snapshots miss it, or 30 days without verification. Rolling feed pagination and source errors do not prove expiration.

For a SQLite backup, stop the app and any scheduled refresh first, then copy the whole `data` directory to a private backup location. Export application history regularly. Keep backups and database credentials outside Git.

### Configure persistent PostgreSQL

**Streamlit Community Cloud local disk is temporary and must not be treated as durable storage.** GitHub Actions runners also start with fresh local disks.

1. Create a hosted PostgreSQL database with a provider of your choice. Obtain its connection string and SSL requirements. Free-tier availability and limits vary.
2. Use a dedicated database/user for this personal app. The user must be allowed to create the initial tables.
3. Put this in local `.env`, or in Community Cloud Secrets as shown below:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

4. URL-encode special characters in the username/password. Use the provider's recommended connection/pooler address.
5. Restart the app. Tables are created automatically on first connection.
6. Configure **the identical database** for scheduled refreshes.

Switching database URLs does not migrate your existing SQLite records. Keep the old database and exports. This first release creates schema version 1; future schema changes require an explicit migration, not dropping tables. Set up provider backups before long-term use.

## Deploy through GitHub and Streamlit Community Cloud

The local build does not automatically push your repository or create a cloud account.

1. From the project terminal, review `git status`. Ensure `.env`, `.streamlit/secrets.toml`, `.venv`, `data` and `logs` are ignored.
2. Push your source code:

```powershell
git add .
git commit -m "Build CareerScout Germany"
git branch -M main
git push -u origin main
```

3. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with GitHub.
4. Choose **Create app**, select your repository and branch, and set the entrypoint to **app.py**.
5. In Advanced settings, select a supported Python version (3.11+; match the version you test) and paste secrets in TOML form:

```toml
DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
APP_PASSWORD = "a-long-random-private-password"
# Optional:
# OPENAI_API_KEY = "..."
# OPENAI_MODEL = "gpt-4.1-mini"
```

6. Deploy, restrict the app to your authorized viewers, and open the assigned `https://…streamlit.app` URL. Use the workspace password if configured.
7. Click Find Jobs. Refresh the browser after an external scheduled run to see its newly stored results.

The password gate is a convenience for one private workspace, not a replacement for platform authentication, rate limiting or multi-user isolation. Use private sharing controls for internet deployment. Do not grant strangers access to your CV/profile or notes.

See Streamlit's [deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management). Never commit real secrets.

## Daily/weekly automation

The workflow `.github/workflows/refresh.yml` is included but **scheduled runs stay disabled until configured**.

1. On GitHub, open repository **Settings → Secrets and variables → Actions**.
2. Add the repository secret `DATABASE_URL` for the same persistent PostgreSQL database used by Streamlit.
3. Add repository variable `REFRESH_FREQUENCY` with value `daily` or `weekly`. Any other value leaves schedules off.
4. Optionally add variable `CAREERSCOUT_USER_AGENT` with your application name and a public contact address.
5. Daily runs are scheduled at 05:17 UTC; weekly runs Monday at 05:37 UTC. GitHub scheduling can be delayed and depends on repository/workflow availability.
6. Use **Actions → Refresh real jobs → Run workflow** for an immediate manual run.

The CLI rejects SQLite when `--require-persistent-db` is supplied, preventing a scheduler from writing to a disposable runner database. Database locking prevents overlapping refreshes. Source failures are isolated and recorded; the command fails if all configured sources fail. No email/Telegram integration is implemented or enabled, so no duplicate alerts are sent.

For Windows Task Scheduler, choose your project's absolute `.venv\Scripts\python.exe` as Program, `-m services.refresh` as Arguments, and the project folder as **Start in**. Choose a daily/weekly trigger. That local task can use the same local SQLite database because it runs on the same computer. For an external server, use PostgreSQL and:

```powershell
python -m services.refresh --require-persistent-db
```

## Testing and architecture

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The default tests use clearly marked synthetic fixtures only inside `tests/`. They cover matching/languages, filtering, deduplication, application history, persistence, locks, source adapters, retries/robots denial, CV parsing, exports/formula safety and all six Streamlit pages.

Optional tests contact real APIs:

```powershell
$env:RUN_LIVE_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -m live
Remove-Item Env:\RUN_LIVE_TESTS
```

They test access/schema, not a guarantee that a specific company has open jobs. See [docs/VERIFICATION.md](docs/VERIFICATION.md) for checks actually run during this build. CI is configured for Python 3.11 and 3.14, but a workflow file is not proof that hosted CI has executed.

```text
app.py                     Streamlit entrypoint, navigation and score cache
config/                    Environment/secrets and reviewed source defaults
ui/                        Reusable cards, filters and six page implementations
sources/                   HTTP safeguards, Pydantic job data, four API adapters
matching/                  Profile, evidence extraction and weighted local scorer
database/                  SQLAlchemy schema and SQLite/PostgreSQL storage
services/                  Refresh CLI, filters, exports, CV parsing and optional AI
tests/                     Synthetic fixtures, regression and opt-in live tests
docs/                      Source-access evidence and verification report
.github/workflows/         CI and opt-in scheduled discovery
```

New sources should implement `name` and `fetch(client) -> FetchResult`, use `build_job`/Pydantic normalization, and register through `sources/registry.py`. Document verified permission, add the API hostname to the reviewed allowlist, and add fixture tests. Set `complete=False` if pagination is capped or the feed is a rolling subset.

## Troubleshooting

| Problem | What to do |
|---|---|
| `py` or `python` not recognized | Reopen VS Code after installing Python. Check `py -0p`; use the installed Python executable's full path if necessary. |
| Activation script blocked | Use `.venv\Scripts\python.exe` directly; no policy change is necessary. |
| `No module named streamlit` | Install requirements using the same `.venv\Scripts\python.exe` that launches the app. |
| Zero results | Check source health; use All available age, all language categories, score 0, disable confirmed-pay-only; add valid employer board names in Settings. Never assume zero jobs means no market opportunities. |
| 404 from an employer | Verify the board name on the employer's current official careers page, including global/EU region and trailing hyphens; remove stale boards. |
| 401/403/robots denied/challenge | Keep that source disabled. Do not add browser cookies, proxies or guessed keys. |
| 429/timeouts | Wait and retry later; lower page counts or number of boards. Retry/backoff is already bounded. |
| PostgreSQL connection error | Check host, SSL, provider network restrictions and password URL encoding. Do not paste secrets into public logs/issues. |
| Cloud saves disappear | Configure PostgreSQL. Temporary cloud SQLite does not survive all restarts/redeploys. |
| Empty CV extraction | Use a text-based PDF/DOCX or OCR externally, then paste corrected text. Encrypted/scanned PDFs are not supported. |
| Another refresh is running | Wait. The lock survives process crashes for at most two hours; do not manually remove an active lock. |
| Port 8501 is busy | Stop an earlier app, or run `python -m streamlit run app.py --server.port 8502` and open localhost:8502. |
| Optional AI request fails | Confirm API key/model access and provider quota. All local features remain usable. |
| Languages/pay look wrong | Review the quoted original wording; heuristics are fallible. The original advert is authoritative. Report a sanitized excerpt for a regression test. |

Refresh logs are structured JSON in ignored `logs/refresh.jsonl` with rotation, and health records are also in the database. They exclude CVs, credentials and raw exception/response bodies.
