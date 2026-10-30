# Fantasy team logo recovery — 2021–2026

Audit and implementation: October 29, 2026 (America/New_York). Repository base
`238a105`, including the persistence fixes and Team of the Week repair. Basketball
Brawl was not accessed or modified during this task. No fantasy scoring or team
identity analytics were changed.

## Before and after

66 team-season entries were examined. The original exported metadata contained
55 nonempty logos; all 55 could be verified as public images with the exporter's
normal browser-compatible image header. Eleven entries had been exported as null.
These were not missing from ESPN's raw metadata: nine referenced protected custom
uploads and two referenced an external image that now works.

| Season | Teams | Exported logos before | Exact-season logos after | Verified franchise fallbacks | Generated badges needed |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 10 | 10 | 10 | 0 | 0 |
| 2022 | 14 | 14 | 14 | 0 | 0 |
| 2023 | 12 | 12 | 12 | 0 | 0 |
| 2024 | 10 | 9 | 10 | 0 | 0 |
| 2025 | 10 | 5 | 7 | 3 | 0 |
| 2026 | 10 | 5 | 10 | 0 | 0 |
| **Total** | **66** | **55** | **63** | **3** | **0** |

**Eight previously missing entries now have exact-season authentic logos.** Three
additional entries use explicitly labeled, verified same-franchise alternatives.
All 66 entries have an authentic image available; this does **not** mean all 66
have their exact historical image. The fallback badge remains available for any
future unrecoverable or broken image.

### Remaining exact-image limitations

| Season / ESPN team ID | Team | Exact source result | Chosen alternative |
| --- | --- | --- | --- |
| 2025 / 3 | Bowers' Castle | Authenticated custom-upload image returns 404 | Exact 2024 logo, same verified franchise |
| 2025 / 6 | if u got me get rid of me | Authenticated custom-upload image returns 404 | Exact 2024 logo, same verified franchise |
| 2025 / 16 | CMC | Authenticated custom-upload image returns 404 | Exact 2024 logo, same verified franchise |

Those image IDs still appear in ESPN's 2025 team metadata, but their stored image
objects are unavailable. Their bytes were not found in Git history or preexisting
local logo assets. No guessed image IDs, alternate private paths, account scraping,
access-control bypasses or rate-limit workarounds were used. The actual failed
source URLs, controlled response status and alternate source season are recorded
in `frontend/public/data/pocky-football/team-logos.json`.

## Sources and investigation

1. Queried the raw `mTeam`/`mSettings` metadata for league 668411840 separately for
   each season. The observed fields are `logo` and `logoType`, with `VECTOR`,
   `CUSTOM_VALID` and `CUSTOM_UPLOAD` values. No additional team image/backup URL
   fields were present. The resolver also supports explicit `logoUrl`/`imageUrl`
   aliases if ESPN supplies them later; it does not invent URLs.
2. Inspected the installed `espn-api==0.41.0` Team constructor. It exposes the raw
   `logo` as `logo_url` but omits `logoType`. The existing project verifier fetched
   image URLs anonymously, so protected custom uploads returned 401 and were
   normalized to null. See the [library source](https://github.com/cwendt94/espn-api)
   and its [authentication documentation](https://github.com/cwendt94/espn-api/wiki).
3. Inspected the accessible [ESPN league website](https://fantasy.espn.com/football/league?leagueId=668411840&seasonId=2026)
   and its actual script references. The bootstrap HTML is an application shell;
   the public league/main bundles use `mTeam`, the Mystique image service and
   `CUSTOM_UPLOAD`. No different historical backup-image source was observed.
4. Tested every distinct observed image URL. Mystique image endpoints return 401
   anonymously but valid images with normal existing ESPN cookie authentication,
   except the three 404 cases above. External images were tested without ESPN
   credentials. The Redbubble image needs the same browser-compatible User-Agent
   convention already used by this project's existing image verifier.
5. Inspected every Git revision affecting season `league.json` files, with 2–4
   relevant revisions per year, including pre-refresh snapshots. Historical URLs
   are preserved, but no additional valid custom-upload bytes or hidden backup
   URL was found. Existing caches contained no earlier fantasy-logo archive.

ESPN's selected default logo-pack artwork is retained as an authentic selected
season logo; 11 entries use that selected artwork, and none is counted as our generated badge. Shared source URLs or
identical image bytes are deduplicated, not interpreted as evidence of franchise
identity. No incorrect logo duplication was identified in the inspected sources.

## Identity and provenance

The catalog is keyed by **season and ESPN team ID**. Exact-year sources always win
before alternate-year images. Every alternate requires a contiguous chain of
adjacent seasons with the same ESPN team ID **and identical nonempty owner-ID
sets** from raw metadata. All 52 observed adjacent-season identity edges passed
that comparison. Similar names, matching logos, and team IDs alone are insufficient.
Changed-owner, unknown-owner, missing-season and reused-ID cases are tested and
cannot acquire an alternate-season image from an unverified identity.

Raw owner IDs are never exported. A one-way, season/team-scoped identity proof
allows detection of same-season ownership changes without publishing account IDs;
continuity records expose only the verification outcome. Names can change without
discarding a verified exact-season image. A known ownership transfer cannot reuse
the previous owner's image as an automatic fallback. These checks are logo-only:
existing franchise/team-ID analytics, Draft manager mappings and scoring semantics
are unchanged.

Each record identifies its observed exact source, selected source, logo type,
source season, verification time and provenance: `exact-espn-season`,
`archived-exact-season`, `same-franchise-fallback` or `generated-badge`. Protected
source identifiers are provenance only; browser rendering uses local static assets,
with no ESPN credentials or signed/authentication query strings in public output.

## Asset reliability and safety

`football_team_logos.py` validates HTTP success, MIME and decoded file contents.
Rasters are bounded to 4 MB incoming and 16 million decoded pixels, stripped of
metadata, reduced to at most 256×256, and saved as WebP. ESPN SVGs must be valid,
self-contained static XML; scripts, active content, entities and external resource
references are rejected. HTML/JSON error pages cannot masquerade as images.

The archive contains 20 SVGs and 14 WebPs (314,849 bytes total; largest file 55,109 bytes). It uses SHA-256 filenames under `data/pocky-football/team-logos/` and
reuses identical sources/bytes. It is roughly a third of a megabyte, with a hard
budget of 256 files / 10 MB; it does not archive full-size photos. Source URLs are
recorded for attribution; image/mark ownership remains with the original sources.

Requests have connection/read timeouts, bounded redirects and retry limits. Cookies
are sent only to the exact observed Mystique host/path and removed on redirects;
external hosts never receive ESPN credentials. Private/local addresses, credential-
containing URLs and signed/query URLs are rejected. Authentication/permission/404
and rate-limit failures are not repeatedly retried within a download. Failures have
24-hour negative caching; mutable external URLs are rechecked after seven days,
while immutable CDN and uploaded-image IDs reuse verified local files. `--recheck`
explicitly bypasses cache freshness checks for an authorized repair.

Existing verified images survive temporary omissions, HTTP failures and decode
errors. Missing exact images may use a verified continuity fallback; otherwise the
shared green initial badge is used. Logo retrieval failures are optional and do not
abort sports ingestion; a corrupt local archive/hash is an integrity failure and
blocks publication.

## Central frontend resolution

All fantasy logos render through `Team` in `Match.jsx` and `resolveTeamBranding`.
Precedence is intentional manual branding override → verified season archive →
archived exact/verified franchise alternative → usable legacy source URL → green
initial/abbreviation badge. The archive's provenance distinguishes exact imagery
from alternate-season imagery internally.

Home, Scoreboard, Standings and Teams use their selected season. H2H rows/details,
Record Book holders/timeline, Draft and player career/transaction rows carry their
actual logo season. Existing intentional current/All-Time manual colors and logo
overrides remain independent of historical automatic-logo selection. A matching
historical source URL can identify its archive entry even when older contracts do
not carry a season on the team object.

The shared badge has a fixed 36px footprint, green border/soft background and
high-contrast abbreviation; existing smaller/larger component sizes still apply.
Images have fixed dimensions and `onError` fallback, so a failed resource does not
leave a broken-image icon or move surrounding layout. It is a reusable CSS badge,
not a fabricated historical image.

## Automatic refresh, persistence and deployment

The exporter reads logo metadata before normalizing the active season. It performs
small bounded metadata-only reads for the configured historical seasons to discover
restored sources and verify identity; it does **not** refresh historical scores,
lineups, draft or activity data. Successful current-season images feed normalized
team logos, while the centralized catalog also fixes historical pages without
rewriting their source snapshots. Existing archived exact logos are preserved on
optional source failures.

The catalog and content-addressed assets live inside the same staging data tree as
sports JSON. JSON provenance and binary `assetHashes` enter release metadata;
validation checks referenced local files and hashes. Bot persistence now permits
only generated JSON plus narrowly matched archive SVG/WebP filenames. Caches,
credentials, arbitrary binaries and unrelated source files cannot enter that commit.
The same tested generation is built and deployed with the existing concurrency,
latest-main and rollback guards. Public verification checks representative SVG and
WebP bytes against release hashes as well as sports JSON. The schedule is unchanged.

`python football_team_logos.py` is the explicit metadata-only repair command; normal
ESPN refreshes call the same recovery mechanism automatically. The one-time repair
updates derived release hashes while keeping the real previous ESPN sports-fetch
timestamp unchanged. No separate manual operation is required for future discovery.

## Validation

Offline tests cover exact-season recovery, renamed teams, changed/missing owners,
franchise fallbacks, changed logos, archive preservation, duplicate sources, bad
MIME/HTML/SVG, safe URLs, cookie isolation on redirects, asset corruption, automatic
refresh integration and all 66 real committed entries. Existing release, sports,
identity and frontend regressions continue to run. Browser QA covers multiple
seasons, matchup cards, standings, team profiles, Draft, H2H, Record Book, player
history and fallback badges at desktop and mobile widths. Deployment verification
must inspect actual public images and persisted-generation hashes, not only a green
workflow status.
