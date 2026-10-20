# Build verification

Verified locally on **20 October 2026**, Windows, Python **3.14**, using the project's `.venv`. No fabricated jobs were inserted into the production database.

## Live integrations

The final configured refresh completed with **10 successful feeds and zero feed errors**:

| Feed | Relevant German student/intern listings returned |
|---|---:|
| Arbeitnow, first 5 pages | 9 |
| Greenhouse — agilerobotsse | 2 |
| Greenhouse — planetlabs | 1 |
| Greenhouse — axon | 2 |
| Greenhouse — celonis | 0 |
| Greenhouse — hellofresh | 0 |
| Greenhouse — contentful | 0 |
| Lever global — quantco- | 0 |
| Lever global — novaspace | 0 |
| Lever EU — quantinuum | 1 |

Counts are from the verification run, not promises about future vacancies. Zero is a valid successfully parsed result. The local database contains **16 unique real listings** accumulated across verification runs, including preserved previously observed records. **7** match the default language/availability filters at verification time.

Cross-source deduplication was exercised by an Agile Robots listing appearing in Arbeitnow and Greenhouse. Source aliases remain available in details/exports.

Earlier candidate board names (`personio`, `deliveryhero`, `quantco`, `helsing`, `enpal`) returned HTTP 404 and were removed from the defaults. `quantco-` was verified as the current Lever identifier. Ashby's robots policy endpoint returned HTTP 401, so its adapter is disabled by default. No restriction was bypassed.

## Automated and runtime verification

- The complete suite, including the PDF fixture and three live API tests, passed **48 tests**.
- Local tests exercise all six Streamlit pages with `streamlit.testing.v1.AppTest`, saving a job, adding/editing an application and saving a changed profile.
- SQLAlchemy tests cover SQLite persistence across reopening, source/URL/cross-platform deduplication, preserving separate requisitions, expiry rules, refresh locks, save/unsave and append-only application edit history.
- Matching tests verify the weighted arithmetic, profile changes, conservative language evidence, missing/future dates, technical keyword boundaries, city qualification and pay evidence.
- Adapter tests cover pagination, robots denial, rate-limit retry, source failures, private/unlisted Ashby rows, Lever requirements lists and Greenhouse update/publication distinction.
- Export tests round-trip CSV and Excel, include original URLs, and verify formula-injection protection.
- CV tests cover local DOCX parsing, invalid/oversized files, and a generated text PDF fixture.
- Optional AI requests are tested for mandatory consent. No paid LLM call was made.
- Streamlit started on **127.0.0.1:8501** and `/_stcore/health` returned **HTTP 200**.
- A separate read-only `AppTest` render of the actual local database returned zero exceptions and the expected 16-job summary.

## Not verified in this environment

- No browser connection was available for visual desktop/mobile inspection. Automated Streamlit rendering/interactions passed, but pixel layout and dark-theme appearance were not visually inspected.
- No PostgreSQL service credentials were supplied. The SQLAlchemy PostgreSQL driver/URL path is implemented, but a live hosted-database connection and migration of existing local data were not tested.
- Python 3.11 and Linux CI are configured, not locally executed; local execution used Python 3.14.
- Streamlit Community Cloud deployment and GitHub Actions scheduling were not run. Source code was not pushed to GitHub.
- Optional OpenAI advice was not called with a real API key.
- No user CV was provided. CV fixtures test text extraction; scanned PDF OCR is intentionally unsupported.

See the README for installation, private cloud deployment and opt-in scheduler instructions.
