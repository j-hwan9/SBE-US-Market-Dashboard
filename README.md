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
- `Refresh market news` runs daily at 21:00 UTC (06:00 KST the next day), or manually via Actions → Run workflow. `최신 게시본 불러오기` only reloads the published snapshot. `뉴스 수집 실행` opens the authenticated GitHub workflow page; no write token is exposed in the website.

## FDA approval-letter dating periods

When PI lacks an explicit unopened refrigerated period, query openFDA Drugs@FDA by exact BLA. Discover all indexed approved application/supplement letters, newest first, and extract PDF dating-period sections. Cache extracted evidence by document and parser identity. Monthly official refresh rechecks the letter index; manual news refresh can optionally recheck letters.

Only explicit 2–8°C finished-product dating periods in months are added. Drug substance, redacted values, stability protocols, ambiguous shared-BLA brand attribution, and unsupported temperatures remain unfilled. Evidence includes BLA, letter date, page, original quote, URL, and strengths found in the approval context. Display as **FDA letter 당시**, never as a guaranteed current expiry for all presentations. Older dated evidence can remain relevant as historical information; actual package expiry and current PI control use. Source errors are exposed separately and do not invalidate existing PI data.

Run `python3 -m unittest discover -s tests -v` and `node tests/ui.cjs` before deployment.


## Portfolio Home

Home combines the reviewed Samsung Bioepis portfolio with the **current** `data.json` Purple Book snapshot and `news.json` article archive. Regulatory historical snapshots do not change the Home summary. Product selection links to the matching molecule/reference in Regulatory and to all collected matching news in Market news. The competitor number counts unique biosimilar brands excluding the selected brand; the originator is shown separately. Denosumab/Prolia and denosumab/Xgeva are separate competitor groups. Products outside current Purple Book coverage display “not connected,” not zero approvals. Prices remain placeholders.

`dist/portfolio.json` is the small, editable portfolio catalog. It was reviewed against Samsung Bioepis’s official Products and Pipeline pages on Sep 09, 2026 (pipeline page: Aug 2026), with US names/suffixes reconciled to Purple Book and launch/access evidence linked per product. Global launch is not US launch. Ospomyv has a US supply/formulary announcement; Opuviz is FDA-approved but awaits US launch. Xbryk and Eticovo are labeled US launch unconfirmed. SB8 uses its development code rather than an overseas brand. Pipeline candidates do not inherit the reference drug’s FDA suffix. Novel ADCs carry target descriptions where no non-proprietary name is assigned.

Portfolio lifecycle/launch states are **editorially reviewed**, not automatically changed by the monthly FDA or daily news workflow. To update a product, edit its catalog entry, evidence URL and `reviewedAt`; no app code changes are required. Competitor and recent-news content automatically follows the existing data refreshes. No market-share or price values are fabricated.

## News topics and product aliases

News matches article titles plus the isolated editorial body (or title/description when no body is available). Purple Book **brand names, molecule names and molecule+suffix names** all map to molecule filters; a brand-only article does not need to say “biosimilar.” The alias list automatically follows the current Purple Book data.

Two additional, independently assigned topics require `biosimilar`/`biosimilars` and at least one keyword in the same article:

- **Market overall:** CMS, Medicare, Medicaid, PBM, health plan, payer, insurance, Veterans affairs, Federal, patient.
- **Policy:** policy, regulation, scheme, administration, executive order.

Matching is case-insensitive, uses word boundaries, and recognizes ordinary plurals and spaces/hyphens. The rules intentionally use the requested broad terms: for example, “administration” also matches an article referring to the Food and Drug Administration. These are keyword topics, not an AI judgment about the article's main subject. One article may belong to multiple molecules/topics. Multiple selected filters use **OR**, and the period filter applies to all results. Articles with no molecule but a qualifying topic are included. Body content is never stored or republished.

Schema v2 keeps `topics` separate from `molecules`, so Home's product news stays molecule-specific. A rule/alias signature triggers bounded reclassification of the existing archive, including URLs no longer in a feed, alongside discovery of new articles. First-seen dates are preserved. Unavailable articles retain their prior records and the UI displays how many are awaiting the new classification. Scheduled and manual GitHub Actions use the same rules without GPT or an API key.


## Refresh schedule and default news filter

- Regulatory: every Monday at 06:00 KST (`0 21 * * 0`, Sunday 21:00 UTC).
- Market news: daily at 06:00 KST (`0 21 * * *`).
- Both workflows retain a shared concurrency group to serialize repository writes and deployments. Monday runs can therefore queue behind each other; GitHub scheduling and collection time can delay publication.
- Market news initially selects **Market overall** only. Policy and molecules start unchecked and use the same neutral/selected styles. Clearing the selection shows all topics; direct product-news navigation replaces the selection with that product’s molecule.
