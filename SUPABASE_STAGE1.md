# Football Supabase backend — Stage 1

Project: `gkrqrlvimigznlbqcxie` (football only). Basketball Brawl is unchanged.

## Required setup

1. In the **football** Supabase project's SQL Editor, run the complete file
   [`supabase/migrations/202611030001_football_live.sql`](supabase/migrations/202611030001_football_live.sql)
   once. It runs transactionally and deliberately fails rather than replacing
   existing unknown objects. API publishable/secret keys cannot safely apply DDL;
   no database password or management token is requested.
2. Confirm repository secrets `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
   `SUPABASE_SECRET_KEY`. The URL must match the specified football project.
   This checkout's local `.env` had none of these entries at implementation time;
   populate them locally only if running the publisher locally. Never commit keys.
3. After a successful existing live refresh, run `python football_supabase.py`
   for one controlled publication. This reuses existing JSON and makes no ESPN
   requests. Do not run a full/historical export just to test the publisher.

## Schema and security

One `football_live_snapshots` table stores a complete JSONB live overlay per
league/season, week, semantic revision, release generation, source/publication
timestamps and explicit public visibility. The league column/compound key permits
future expansion with a deliberate migration; this stage accepts Pocky only.

RLS allows public SELECT only for explicitly published rows. Anonymous and
authenticated roles have no mutation grants or publisher RPC execution. Only the
backend service role writes. The RPC locks league/season publication atomically,
rejects regressing weeks/timestamps and conflicting revisions, skips identical
snapshots, and replaces the complete snapshot in one transaction. Keys stay in
backend environment variables and are sent using `apikey`, without redirects.

## Pipeline

The live workflow validates and persists its snapshot to Git, checks latest-main
and public rollback safety, then publishes to Supabase without building/deploying
Pages. Unchanged live checks retry/read back the persisted snapshot without
another ESPN request. Supabase failure fails the live job and leaves that candidate
available for retry; scheduler completion requires verified publication. Full
refreshes and code deployments retain the existing Pages pipeline. See
`ops/cloudflare-live-scheduler/README.md` for dispatch setup and reversible cutover.

Full reconciliations have no live overlay and are not published to this table.
The next successful live collection replaces the prior week; `source_at`/`week`
must be used to recognize an older snapshot. No frontend integration, Realtime,
new scheduler, historical migration, or basketball changes are included.

## Verification status

Focused offline tests cover publication/readback, unchanged suppression,
stale/invalid input, failure handling, release validation and SQL security
definitions. Workflow YAML is parsed separately. SQL definitions were reviewed,
but the migration was **not applied or executed against PostgreSQL** here.
Local Supabase credentials were absent, so no real write/readback was attempted.
Automatic publication code is wired but database readiness and real publication
remain unverified until the migration and configured credentials are confirmed.
