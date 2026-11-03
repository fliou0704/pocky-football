-- Apply once in the FOOTBALL project's SQL Editor. No basketball objects referenced.
begin;
create table public.football_live_snapshots (
  league_id bigint not null check (league_id = 668411840),
  season integer not null check (season between 2021 and 2200),
  week integer not null check (week between 1 and 25),
  revision text not null check (revision ~ '^[a-f0-9]{64}$'),
  generation_id text not null check (generation_id ~ '^[a-f0-9]{64}$'),
  source_at timestamptz not null,
  published_at timestamptz not null default now(),
  is_public boolean not null default false,
  snapshot jsonb not null check (jsonb_typeof(snapshot) = 'object'),
  primary key (league_id, season),
  check (snapshot ?& array['schemaVersion','leagueId','season','week','snapshotId','fetchedAt','matchups','lineups']),
  check ((snapshot->>'schemaVersion')::integer = 1),
  check ((snapshot->>'leagueId')::bigint = league_id),
  check ((snapshot->>'season')::integer = season),
  check ((snapshot->>'week')::integer = week),
  check (snapshot->>'snapshotId' = revision),
  check ((snapshot->>'fetchedAt')::timestamptz = source_at)
);
alter table public.football_live_snapshots enable row level security;
revoke all on public.football_live_snapshots from public, anon, authenticated;
grant select on public.football_live_snapshots to anon, authenticated;
grant select, insert, update on public.football_live_snapshots to service_role;
create policy football_published_read on public.football_live_snapshots
  for select to anon, authenticated using (is_public);

create function public.publish_football_snapshot(p_snapshot jsonb, p_generation text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  v_old public.football_live_snapshots%rowtype;
  v_source timestamptz;
  v_week integer;
  v_season integer;
begin
  if p_snapshot is null or not (p_snapshot ?& array['schemaVersion','leagueId','season','week','snapshotId','fetchedAt','matchups','lineups'])
     or (p_snapshot->>'schemaVersion')::integer is distinct from 1
     or (p_snapshot->>'leagueId')::bigint is distinct from 668411840
     or coalesce(p_snapshot->>'snapshotId','') !~ '^[a-f0-9]{64}$'
     or coalesce(p_generation,'') !~ '^[a-f0-9]{64}$'
     or jsonb_typeof(p_snapshot->'matchups') is distinct from 'array'
     or jsonb_array_length(p_snapshot->'matchups') = 0
     or jsonb_typeof(p_snapshot->'lineups'->'teams') is distinct from 'object' then
    raise exception 'Invalid football snapshot';
  end if;
  v_source := (p_snapshot->>'fetchedAt')::timestamptz;
  v_week := (p_snapshot->>'week')::integer;
  v_season := (p_snapshot->>'season')::integer;
  if v_source is null or v_source > now() + interval '5 minutes' then
    raise exception 'Invalid source timestamp';
  end if;
  perform pg_advisory_xact_lock(668411840, v_season);
  select * into v_old from public.football_live_snapshots
    where league_id=668411840 and season=v_season for update;
  if found then
    if v_week < v_old.week or v_source < v_old.source_at then
      return jsonb_build_object('action','stale');
    end if;
    if v_old.revision = p_snapshot->>'snapshotId' then
      if v_old.snapshot <> p_snapshot then raise exception 'Revision conflict'; end if;
      return jsonb_build_object('action','unchanged');
    end if;
    if v_source <= v_old.source_at then return jsonb_build_object('action','stale'); end if;
  end if;
  insert into public.football_live_snapshots
    (league_id,season,week,revision,generation_id,source_at,is_public,snapshot)
    values (668411840,v_season,v_week,p_snapshot->>'snapshotId',p_generation,v_source,true,p_snapshot)
    on conflict (league_id,season) do update set
      week=excluded.week, revision=excluded.revision,generation_id=excluded.generation_id,
      source_at=excluded.source_at,published_at=now(),is_public=true,snapshot=excluded.snapshot;
  return jsonb_build_object('action','published');
end;
$$;
revoke all on function public.publish_football_snapshot(jsonb,text) from public,anon,authenticated;
grant execute on function public.publish_football_snapshot(jsonb,text) to service_role;
notify pgrst, 'reload schema';
commit;
