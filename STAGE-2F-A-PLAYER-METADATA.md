# Stage 2F-A: Football player metadata foundation

Data-only implementation for normalized Pocky Football appearances from 2021–2026. No Players page, navigation, existing page changes, frontend deployment, or schedule change.

## Coverage audit

| Measure | Count | Human coverage |
| --- | ---: | ---: |
| Unique league entities | 539 | — |
| Human players | 507 | 100% |
| Team defenses | 32 | excluded |
| nflverse ESPN-ID matches | 507 | 100% |
| ESPN-only humans | 0 | 0% |
| Sleeper fallback matches | 0 | 0% |
| Unmatched humans | 0 | 0% |
| Headshot | 507 | 100% |
| Height | 507 | 100% |
| Weight | 507 | 100% |
| Birth date | 507 | 100% |
| College | 507 | 100% |
| Position | 507 | 100% |
| Latest NFL team | 507 | 100% |
| Jersey number | 459 | 90.53% |
| NFL Draft fields, any / complete | 424 / 424 | 83.63% / 83.63% |

All 507 primary headshot URLs were checked with streamed requests: HTTP 200 and image content type. No image files were saved. All selected URLs came from nflverse; ESPN fallback was unnecessary. Checks establish availability and content type, not visual correctness or permanent availability.

Sleeper was neither downloaded nor queried: the primary source matched every human and supplied all requested biographical fields except jersey and draft fields. The optional Sleeper ID fallback is implemented and tested for future gaps; it never uses fuzzy names.

## Universe and matching

The universe is the union of `teams.json` rosters, every available weekly `lineups/*.json`, `draft.json` picks, and `activity.json` player movements, across configured seasons. ESPN IDs deduplicate identities across seasons. `observedIn` and `seasons` preserve membership evidence. The scoring pool is intentionally excluded from universe membership because it contains NFL players who never appeared in this league; it can fill missing names/positions for existing universe members.

No malformed universe IDs, unresolved names, ambiguous nflverse ESPN IDs, or duplicate human GSIS IDs were found. Historical retired/out-of-league players, kickers, and short-term players remain included and all match. The only non-human entities are the 32 defenses, represented separately rather than reported as biography failures.

Matches are strictly `ESPN playerId → nflverse espn_id`, then optionally `→ Sleeper espn_id`. Conflicting duplicate source IDs remain unresolved; identical duplicate rows collapse deterministically. No name matching occurs. Each profile records its matching method and field-level sources. ESPN supplies known names/positions; nflverse supplies biographies, latest team/jersey, external player IDs, NFL Draft fields, and headshots. Fantasy draft picks remain in the original fantasy draft contracts.

## Missing fields and review concerns

The machine-readable audit lists every missing-field case with ID, name, position, and last source season.

- **48 missing jersey numbers:** includes active/recent and historical players. Examples: Zach Ertz, Adam Thielen, Brandin Cooks, Austin Ekeler, and Kenyan Drake. This is a source omission, not failed identity matching. Historical lineup contracts do not contain reliable jersey numbers, so none are inferred.
- **83 empty NFL Draft records:** 33 RB, 26 K, 15 WR, 5 TE, 4 QB. Inspection includes known undrafted players such as Austin Ekeler, Justin Tucker, Adam Thielen, Brandon Aubrey, and Jordan Mason. Blank source fields are consistent with undrafted histories but are not an authoritative undrafted flag. They remain null; the future UI should avoid labeling every null as “undrafted.”
- NFL team abbreviations are retained from their named source. nflverse may use `WAS` while ESPN weekly contracts use `WSH`; future display code should canonicalize aliases without changing historical records.
- Latest team, jersey, position, headshot, and last season describe the source snapshot, not historical fantasy seasons, guaranteed present-day employment, or retirement status. Some departed players retain a last known team.
- Birth date is stored; age is not. Source photos may change or become unavailable; future rendering needs a local UI fallback.
- No biography completeness problems justify additional API traffic at this stage. Jersey enrichment can be considered later if it becomes important to the product.

## Contract and outputs

- `football_player_metadata.py`: standalone generator over existing normalized snapshots.
- `frontend/public/data/pocky-football/players.json`: schema version 1; generation timestamp, season scope, source URL/cache timestamp/SHA-256, and sorted `players`.
- `frontend/public/data/pocky-football/player-metadata-audit.json`: totals, match rates, coverage, missing cases, input file inventory, source collisions, malformed IDs, and image-check outcomes.
- `tests/test_football_player_metadata.py`: seven focused tests.

Human profiles use numeric `espnId`, `entityType: "player"`, name/position, dimensions, DOB/college, latest team/jersey, rookie/last seasons, `ids` (GSIS/NFL/PFR), `nflDraft` (year/round/overall pick/team), headshot URL/validation, match method and field sources. Unknown values are null. All fields are explicitly selected from sources; no raw source columns, fantasy owners, credentials, member identifiers, or stale calculated ages are published.

D/ST profiles use `entityType: "team_defense"`, their negative ESPN ID, name, NFL team, position, and a derived ESPN team-logo URL. Team-logo URLs are syntax checked, not individually fetched. They have no height, weight, DOB, college, human headshot, or NFL Draft fields and are excluded from all human coverage denominators.

Headshot chain: verified nflverse URL → verified ESPN URL derived from the authoritative ESPN player ID → null. No other free image source was needed. The future frontend must handle null and later image failures.

## Updating

Run after normalized season generation:

```sh
python football_player_metadata.py --refresh --check-headshots
```

`--refresh` downloads the nflverse CSV once. As of Stage 2F-B, prior image results remain cached; `--recheck-images` explicitly refreshes URL checks. Raw source and image-check caches live under ignored `.cache/player-metadata/`, outside public data. Concurrent image checks are capped at 12; streamed responses close without saving image files. No per-player biography requests occur.

For an offline/review rebuild using cached source and cached successful image checks:

```sh
python football_player_metadata.py --check-headshots
```

Without `--check-headshots`, image URLs are syntax checked only and explicitly marked `syntax_only`; use the checked mode for publication. Non-200 responses or network uncertainty never count as verified images; the checked build tries the ESPN fallback, then leaves null. Cached failures can be retried with `--recheck-images`.

Optional `--sleeper` fetches the full free public player response once and caches it; use only when primary coverage warrants it. Sleeper fills available gaps after nflverse and records ESPN-ID matching. `--first-season` / `--last-season` can override the CLI defaults, which come from league configuration.

Stage 2F-A left the generation workflow unchanged. Stage 2F-B now refreshes metadata after ESPN snapshots and builds compact Players presentation contracts. Image results are cached across workflow runs to avoid repeat traffic; no new secret or schedule increase is needed.

Sources: [nflverse maintained player release](https://github.com/nflverse/nflverse-data/releases/tag/players), [nflreadr player dictionary](https://nflreadr.nflverse.com/articles/dictionary_players.html), and the optional [Sleeper API documentation](https://docs.sleeper.com/).

## Validation

All **76 Python tests passed**, including **7 focused metadata tests**. Checks cover universe membership, unique ESPN and GSIS identities, deterministic joins and ambiguous-ID handling, dimensions and NFL Draft bounds, D/ST exclusions, headshot fallback/URL handling, optional Sleeper ID matching, and the public field allowlist/absence of credential identifiers. Existing exporter, activity, history, H2H, season, home, and record tests also passed. No frontend tests/build were necessary because no frontend behavior changed.
