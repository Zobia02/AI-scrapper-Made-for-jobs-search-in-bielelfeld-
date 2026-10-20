# Data source access and coverage

Reviewed on 20 October 2026. The application reads documented public APIs, never logged-in pages, search-engine caches, CAPTCHA-protected pages or hidden ATS endpoints. Access policies can change; recheck the linked primary documents before expanding or republishing the service.

| Source | Implementation | Access basis and current limits |
|---|---|---|
| Arbeitnow | Enabled, paginated public API | The operator publishes a [free job-board API](https://www.arbeitnow.com/blog/job-board-api), without an API key, including ATS listings. Source attribution appears in the dashboard and exports. Default limit: 5 pages; selectable 1–10. This is a rolling feed, not an exhaustive national inventory. |
| Greenhouse | Enabled, configured employer boards | [Job Board API documentation](https://docs.greenhouse.io/job-board) describes publicly available GET endpoints without authentication. Requests use `content=true`. `updated_at` is never substituted for publication time. Employer board identifiers are shown when the feed does not supply a display name. |
| Lever global / EU | Enabled, configured employer boards | [Official Postings API](https://github.com/lever/postings-api) explicitly describes public published postings and third-party scraping. Uses GET only, `skip`/`limit` pagination, at most 20 pages of 100. Does not submit applications. |
| Ashby | Adapter implemented; disabled by default | [Public job-posting API](https://developers.ashbyhq.com/docs/public-job-posting-api) documents public board data. Only `isListed=true` entries qualify. Live policy check returned HTTP 401 from `robots.txt`; collection stopped. The adapter can be configured if policy verification becomes accessible. |
| Bundesagentur für Arbeit | Disabled | An unofficial description of an endpoint is not an authorization to reuse it. No sufficiently verified open access/redistribution agreement was established for this application. [BA portal terms](https://jobboerse.arbeitsagentur.de/vamJB/hilfe/de/AS/unbetreut/1128.html). No copied or guessed API keys are used. |
| StepStone | Disabled | [JobFeed documentation](https://api.stepstone.com/wp-content/uploads/2025/03/Stepstone_JobFeed_DE.pdf) concerns contract-authorized data exchange; [partner network](https://www.stepstone.de/e-recruiting/en/cooperation-partner/). No public search feed permission established. |
| Indeed | Disabled | [Terms](https://www.indeed.com/legal?co=US&hl=en) and [API conditions](https://docs.indeed.com/legal-terms/additional-api-terms-and-guidelines) apply. No authorized search/publisher API credentials configured. |
| LinkedIn | Disabled | [User Agreement](https://www.linkedin.com/legal/user-agreement) prohibits scraping and circumventing limits. No approved job-search API integration configured. |
| Glassdoor | Disabled | [Terms](https://www.glassdoor.com/about/terms/) reviewed; no open aggregation API or RSS permission established. |
| JOIN | Direct collection disabled | [Terms](https://join.com/en/terms) do not establish a general open aggregator API. JOIN-origin listings may appear via Arbeitnow, which documents that feed source. No direct JOIN scraping. |
| Universities | Disabled | No specific institution's permitted RSS/API identified and implemented. Research assistant roles can still arrive through enabled feeds. |

## Runtime safeguards

- HTTPS API host allowlist; ATS board names restricted to letters, digits, underscore and hyphen. Arbitrary URLs and redirects are not followed.
- Robots policy fetched and cached for each host per refresh. A disallow rule, authentication error, server error, redirect or HTML challenge stops access. Missing robots files (404/410) are accepted only for the already reviewed documented API hosts.
- At least 1.1 seconds between requests per host, or the published crawl delay/request rate if longer. Requests stop when published delay exceeds the interactive budget.
- Connection timeout 10 seconds; read timeout 25 seconds. At most three attempts on transient failures/429/5xx, exponential backoff, respect numeric Retry-After up to 30 seconds. Longer/date-form Retry-After stops the current run, so it is not retried prematurely.
- Configurable identifying user agent. The app does not impersonate a browser, rotate proxies, use harvested tokens or evade access controls.
- Bounded page limits and 20 MB response acceptance limit. The HTTP client buffers responses before checking that size; the allowlist is therefore essential.
- Invalid normalized rows are counted; incomplete feeds never cause absence-based expiration.

## Coverage and accuracy

The collector retains recognizable student/intern/research-assistant roles with technical-category evidence and an explicit German country/location or recognized German city. Generic “Remote”, “Europe” and worldwide roles without Germany evidence are excluded. The city alias list is deliberately finite; an unfamiliar town without a country may be missed.

An API success with zero matching jobs is a valid outcome. Boards move, employers stop hiring, and API-visible adverts can remain after their deadline. “Last verified” means last observed in the source API, not independent verification by the employer.

Two complete board snapshots without a listing, or 30 days without observation, mark it potentially expired. API failures and truncated/rolling feeds do not count as complete absence. Records, saved jobs and application history are retained.

No test fixtures are imported by production code. Direct Apply opens the original supplied URL; it never creates an application or fills a form.
