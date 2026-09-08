# Samsung Bioepis US Market Dashboard

Private, static product comparison app in Korean, with English official label evidence.

## Scope

FDA Purple Book August 2026 full monthly snapshot, restricted to licensed 351(k) products and their named reference products. Records are grouped by BLA + proprietary name; formulation/presentation rows remain distinct within each product. Historical voluntarily revoked Rituxan BLA 103737 is excluded. Discontinued marketing does not imply revoked licensure and is retained where licensed.

130 product records, 124 proprietary names, 21 core molecules, 315 Purple Book rows. All 130 have a DailyMed or FDA PI source. These counts describe regulatory records, not unique marketed brands or purchasable packages.

## Interface

- Vertical bar chart of distinct licensed biosimilar brands per molecule; reference products excluded.
- Originator is always the first comparison column; unlimited biosimilar selection and select-all.
- Reference-brand selector for molecules with multiple originators; shared originator BLAs are combined with separate PI source links.
- Date metadata formatted as MMM DD, YYYY, without timezone-driven date shifts.
- Snapshot selector and field-level change history.
- Official-source refresh opens the authenticated GitHub workflow page; no client-side write credentials.

## Sources and refresh

- `data/purplebook.csv`: retained official full CSV.
- `data/purplebook.json`: selected Purple Book rows before exclusion of historical revoked records.
- `dist/data.json`: fixed reviewed publication snapshot, retrieved September 8, 2026.
- `scripts/collect.py`: DailyMed SPL collection, BLA validation, sections and package/ingredient extraction.
- `scripts/fda_fallback.py`: Drugs@FDA label fallback; combined Immgolis/Immgolis Intri PDF sections separated.
- `scripts/finalize.py`: current licensure scope, per-SPL-product BLA checks, manufacturer statements, verification summary.

The three original scripts document the first snapshot. Use `scripts/refresh.py` for ongoing maintenance; do not run the legacy scripts for monthly updates. The public application reads a published snapshot. `scripts/refresh.py` discovers fresh official sources and publishes only after validation. `.github/workflows/refresh.yml` supports manual and monthly execution after GitHub is connected. See SETUP_GITHUB.md.

## Interpretation limits

Dates and interchangeability remain presentation-specific. Do not infer biosimilar-to-biosimilar interchangeability. A combined PI can describe multiple presentations/routes: apply the clause that matches the Purple Book presentation. Package NDCs are from the selected official label, not an exhaustive inventory of repackagers or current commercial availability. FDA labels with pending or placeholder NDC values are shown as such.

PI wording is retained in English to preserve age, indication, route, temperature, time and handling qualifiers. PDF tables are extracted as text and may require the linked original for cell relationships. Manufacturer fields distinguish applicant, labeler and explicit manufactured/distributed-by statements. Refrigerated shelf life in months is not inferred when the PI only specifies the expiration date. Sorbitol-free and latex-free are never inferred from silence.

## Verification

JavaScript syntax and all field renderers checked over all products. Comparison rendering exercised with more than five selected biosimilars, permanent originator, separate reference scopes, date formatting and exact chart counts. Refresh tests cover full-table selection, future-month exclusion, metadata-only changes, missing reference products, mass data loss and preservation of published bytes on failure. Source spot checks cover presentation-dependent Humira latex statements, Amjevita RT conditions, Neupogen/Zarxio RT conditions in dosage sections, Ziextenzo 20–35°C / 120-hour handling, and distinct Immgolis vs Immgolis Intri labels. No browser visual QA was requested or performed.

Plain static site: `dist/index.html`, `dist/styles.css`, `dist/app.js`, `dist/data.json`. The Sites manifest identifies the private deployment.


## Market news

The Market news tab lists publisher titles, publication dates, molecule tags, and original links. Article bodies are used only in memory for matching and are never stored or republished. Dates use UTC and display as MMM DD, YYYY. Multiple selected molecules use OR matching; a date range includes both endpoints. The initial default is the last 90 days. Archives accumulate from available RSS/sitemap entries, not complete historical publisher archives.

- BR&R and Drug Channels: RSS discovery. Drug Channels tracking links must resolve through the feed's original link field.
- Fierce Pharma, BioSpace, Pharmaceutical Executive: sitemap discovery and public article metadata.
- Match Purple Book brands, proper names and molecules with word boundaries. Ignore navigation and related-article blocks. If an editorial body cannot be isolated, use title/description only and record `matchBasis`; full-text coverage is not claimed.
- Prefer NewsArticle.datePublished over generic HTML meta timestamps (some publisher meta values reflect request time). Never use sitemap lastmod as publication date.
- Respect robots.txt and publisher pacing. No CAPTCHA, login, paywall or access-control bypass. Retain older news when a source fails and show partial/unavailable source states.
- `Refresh market news` runs daily at 22:17 UTC (07:17 KST the next day), or manually via Actions → Run workflow. `최신 게시본 불러오기` only reloads the published snapshot. `뉴스 수집 실행` opens the authenticated GitHub workflow page; no write token is exposed in the website.

## FDA approval-letter dating periods

When PI lacks an explicit unopened refrigerated period, query openFDA Drugs@FDA by exact BLA. Discover all indexed approved application/supplement letters, newest first, and extract PDF dating-period sections. Cache extracted evidence by document and parser identity. Monthly official refresh rechecks the letter index; manual news refresh can optionally recheck letters.

Only explicit 2–8°C finished-product dating periods in months are added. Drug substance, redacted values, stability protocols, ambiguous shared-BLA brand attribution, and unsupported temperatures remain unfilled. Evidence includes BLA, letter date, page, original quote, URL, and strengths found in the approval context. Display as **FDA letter 당시**, never as a guaranteed current expiry for all presentations. Older dated evidence can remain relevant as historical information; actual package expiry and current PI control use. Source errors are exposed separately and do not invalidate existing PI data.

Run `python3 -m unittest discover -s tests -v` and `node tests/ui.cjs` before deployment.
