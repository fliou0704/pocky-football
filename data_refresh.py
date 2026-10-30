"""Validated snapshot staging, Git persistence and Pages release verification.

No network access occurs during validation or ordinary unit tests.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from football_exporter import ROOT, PUBLIC_DATA, read_config, write_json

SLUG = 'pocky-football'
META = 'refresh.json'


class ReleaseError(ValueError):
    """Controlled diagnostic with no upstream request or credential details."""


def read(path):
    def invalid(value):
        raise ValueError('Nonfinite JSON constant')
    return json.loads(Path(path).read_text(), parse_constant=invalid)


def snapshots(root):
    root = Path(root)
    return {str(p.relative_to(root)): read(p) for p in sorted(root.rglob('*.json'))
            if p.name != META}


def hashes(root):
    return {name: hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            for name, data in snapshots(root).items()}


def asset_hashes(root):
    folder = Path(root)/SLUG/'team-logos'
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.glob('*')) if p.is_file() and re.fullmatch(r'[a-f0-9]{64}\.(svg|webp)', p.name)}


def semantic(value):
    # Attempt times are not sports changes. Preserve previous files on a no-change fetch.
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items()
                if k not in ('generatedAt', 'cachedAt', 'lastSuccessfulSnapshotAt', 'metadataGeneratedAt')}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def validate(root, baseline=None, require_metadata=False):
    from football_seasons import validate_season
    from football_home import validate_home
    root = Path(root)
    config = read_config(SLUG)
    year = config['season']
    years = set(range(config.get('firstSeason', year), year + 1))
    data = snapshots(root)  # Parse every JSON, including derived profiles and pair files.
    from football_team_logos import validate_catalog
    validate_catalog(root, SLUG)
    def get(name):
        require(name in data, 'Missing required JSON: ' + name)
        return data[name]
    site = get('site.json')
    require(set(site['seasons']) == years, 'Expected seasons missing')
    require(site['leaguePath'] == f'{SLUG}/{year}/league.json', 'Incorrect active season')
    for y in sorted(years):
        prefix = f'{SLUG}/{y}/'
        league, teams = get(prefix+'league.json'), get(prefix+'teams.json')
        require(league['league']['id'] == config['leagueId'] and league['league']['season'] == y,
                'League identity mismatch')
        validate_season(league, teams)
        require(bool(league['standings']) and bool(teams['matchups']), 'Empty season')
        for name in ('activity', 'draft', 'player-scoring', 'player-games', 'team-of-week'):
            require(get(prefix+name+'.json')['season'] == y, 'Source season mismatch')
    for name in ('h2h', 'record-book', 'players', 'players-index', 'player-metadata-audit',
                 'draft-analysis', 'draft-scoring-audit'):
        get(f'{SLUG}/{name}.json')
    require(bool(get(f'{SLUG}/players-index.json')['players']), 'Empty player index')
    for player in get(f'{SLUG}/players-index.json')['players']:
        # Require every profile linked by the frontend index.
        require(f"{SLUG}/players/{player['espnId']}.json" in data, 'Missing player profile')
    from football_weekly import weekly_contracts
    for y, expected in weekly_contracts(root, SLUG, sorted(years)).items():
        require(get(f'{SLUG}/{y}/weekly.json') == expected,
                'Weekly stories do not match source snapshots')
    home = get(f'{SLUG}/{year}/home.json')
    league = get(f'{SLUG}/{year}/league.json')
    teams = get(f'{SLUG}/{year}/teams.json')
    validate_home(home, league)
    ids = {str(t['teamId']) for t in league['standings']}
    require(len(ids) == len(league['standings']), 'Duplicate standings team')
    for t in league['standings']:
        require(all(isinstance(t[k], (int, float)) and not isinstance(t[k], bool)
                    and math.isfinite(t[k]) for k in ('pointsFor', 'pointsAgainst')), 'Invalid standings points')
    finals = [m for m in teams['matchups'] if m['status'] == 'final']
    for match in teams['matchups']:
        if match['status'] in ('final', 'live'):
            require(all(isinstance(match[k], (int, float)) and math.isfinite(match[k])
                        for k in ('homeScore', 'awayScore')), 'Missing matchup scores')
    for week in sorted({m['week'] for m in finals}):
        detail = get(f'{SLUG}/{year}/lineups/{week}.json')
        participants = {str(m[side+'TeamId']) for m in finals if m['week'] == week for side in ('home', 'away')}
        require(participants <= set(detail['teams']) <= ids and
                all(detail['teams'][tid] for tid in participants), 'Incomplete final-week lineups')
    for team in league['standings']:
        played = sum(m['phase'] == 'regular' and team['teamId'] in (m['homeTeamId'], m['awayTeamId'])
                     for m in finals)
        require(team['wins'] + team['losses'] + team['ties'] == played,
                'Standings disagree with completed matchups')
    scoring = get(f'{SLUG}/{year}/player-scoring.json')
    games = get(f'{SLUG}/{year}/player-games.json')
    require(bool(scoring['players']) and bool(games['players']), 'Empty current player data')
    require(not scoring['coverage'].get('conflicts') and
            not scoring['coverage'].get('lineupComparison', {}).get('scoreConflicts'), 'Player score conflicts')
    require(get(f'{SLUG}/{year}/draft.json')['coverage']['complete'], 'Incomplete draft')
    activity = get(f'{SLUG}/{year}/activity.json')
    require(activity['coverage']['status'] in ('independently_verified_counts', 'likely_complete'),
            'Activity fetch incomplete or stale')
    from football_team_of_week import season_team_of_week
    require(get(f'{SLUG}/{year}/team-of-week.json') == season_team_of_week(root / SLUG / str(year)),
            'Team of the Week does not match current source snapshots')
    # All pair contracts referenced by the H2H selector must exist.
    h2h = get(f'{SLUG}/h2h.json')
    from itertools import combinations
    for a, b in combinations(sorted(int(t['teamId']) for t in h2h['teams']), 2):
        get(f'{SLUG}/h2h/{a}-{b}.json')
    if baseline is not None:
        previous = snapshots(baseline)
        require(set(previous) <= set(data), 'Previously published JSON disappeared')
        require({p['espnId'] for p in previous[f'{SLUG}/players-index.json']['players']} <=
                {p['espnId'] for p in get(f'{SLUG}/players-index.json')['players']}, 'Player index entries disappeared')
        for name, old in previous.items():
            if any(name.startswith(f'{SLUG}/{y}/') for y in years if y != year):
                require(old == data[name], 'Historical snapshot changed: '+name)
        old_teams = previous[f'{SLUG}/{year}/teams.json']
        require(set(old_teams['teams']) == set(teams['teams']), 'Current team population changed')
        old_matches = {(m['week'], m['homeTeamId'], m['awayTeamId']): m for m in old_teams['matchups']}
        new_matches = {(m['week'], m['homeTeamId'], m['awayTeamId']): m for m in teams['matchups']}
        require(len(new_matches) == len(teams['matchups']), 'Duplicate matchup')
        for key, match in old_matches.items():
            require(key in new_matches, 'Schedule rows disappeared')
            if match['status'] == 'final':
                require(new_matches[key]['status'] == 'final', 'Final matchup regressed')
        old_home = previous[f'{SLUG}/{year}/home.json']['state']
        if home['state']['currentWeek'] is not None and old_home['currentWeek'] is not None:
            require(home['state']['currentWeek'] >= old_home['currentWeek'], 'Matchup period regressed')
        require((home['state']['lastCompletedWeek'] or 0) >= (old_home['lastCompletedWeek'] or 0),
                'Completed week regressed')
        old_scoring = previous[f'{SLUG}/{year}/player-scoring.json']['players']
        new_scores = {p['playerId']: p['pointsByWeek'] for p in scoring['players']}
        for p in old_scoring:
            require(p['playerId'] in new_scores and set(p['pointsByWeek']) <= set(new_scores[p['playerId']]),
                    'Previously observed player scoring disappeared')
        old_games = previous[f'{SLUG}/{year}/player-games.json']['players']
        require(all(pid in games['players'] and set(rows) <= set(games['players'][pid])
                    for pid, rows in old_games.items()), 'Previously observed player games disappeared')
        require({e['id'] for e in previous[f'{SLUG}/{year}/activity.json']['events']} <=
                {e['id'] for e in activity['events']}, 'Activity events disappeared')
    meta_path = root / SLUG / META
    if meta_path.exists():
        meta = read(meta_path)
        require(meta['dataHashes'] == hashes(root), 'Persisted generation hashes do not match data')
        require(meta.get('assetHashes', {}) == asset_hashes(root), 'Persisted logo asset hashes do not match files')
    elif require_metadata:
        raise ValueError('Missing persisted refresh metadata')
    return home


def update_derived_metadata(root, builder='team-of-week-v2'):
    """Record an offline derived repair without claiming a new ESPN fetch."""
    path = Path(root) / SLUG / META
    if path.exists():
        meta = read(path)
        meta['dataHashes'] = hashes(root)
        meta['assetHashes'] = asset_hashes(root)
        meta['generationId'] = hashlib.sha256(json.dumps(meta['dataHashes'], sort_keys=True).encode()).hexdigest()
        meta['derivedBuilder'] = builder
        write_json(path, meta)


def refresh(output=PUBLIC_DATA, generator=None):
    from football_exporter import generate
    output = Path(output)
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp) / 'data'
        shutil.copytree(output, candidate)
        (candidate / SLUG / META).unlink(missing_ok=True)
        (generator or generate)(SLUG, output=candidate, current_only=True)
        home = validate(candidate, baseline=output)
        changed = semantic(snapshots(candidate)) != semantic(snapshots(output))
        print(f'ESPN fetched=true; validation=passed; sportsChanged={str(changed).lower()}')
        if not changed and (output / SLUG / META).exists():
            print('No semantic changes; retaining persisted generation (no metadata-only commit). '
                  f'lastSuccessfulCheckAt={datetime.now(timezone.utc).isoformat()}')
            return False
        digest = hashlib.sha256(json.dumps(hashes(candidate), sort_keys=True).encode()).hexdigest()
        write_json(candidate / SLUG / META, {
            'schemaVersion': 1, 'lastSuccessfulEspnFetchAt': datetime.now(timezone.utc).isoformat(),
            'season': home['season'], 'latestMatchupPeriod': home['state']['currentWeek'],
            'lastCompletedWeek': home['state']['lastCompletedWeek'], 'generationId': digest,
            'producedChanges': changed, 'sourceRevision': git('rev-parse', 'HEAD'),
            'runId': os.environ.get('GITHUB_RUN_ID'), 'dataHashes': hashes(candidate),
            'assetHashes': asset_hashes(candidate),
        })
        validate(candidate, baseline=output, require_metadata=True)
        # No candidate file reaches the working tree before the whole release validates.
        shutil.copytree(candidate, output, dirs_exist_ok=True)
        return True


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def assert_latest(cwd=ROOT):
    git('fetch', 'origin', 'main', cwd=cwd)
    require(git('rev-parse', 'HEAD', cwd=cwd) == git('rev-parse', 'origin/main', cwd=cwd),
            'main advanced; refusing stale persistence/deployment. Run the workflow again on latest main.')


def persist(cwd=ROOT):
    assert_latest(cwd)
    git('add', '--', 'frontend/public/data', cwd=cwd)
    changed = bool(git('diff', '--cached', '--name-only', cwd=cwd))
    if changed:
        paths = git('diff', '--cached', '--name-only', cwd=cwd).splitlines()
        require(all((p.startswith('frontend/public/data/') and p.endswith('.json')) or
                    re.fullmatch(r'frontend/public/data/'+SLUG+r'/team-logos/[a-f0-9]{64}\.(svg|webp)', p) for p in paths),
                'Refusing to commit unrelated staged files')
        print(f'Changed generated data files={len(paths)}')
        git('-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'commit', '-m', 'chore(data): refresh Pocky Football snapshots', cwd=cwd)
        # A non-fast-forward or protected-branch rejection is fatal; never force or deploy anyway.
        git('push', 'origin', 'HEAD:main', cwd=cwd)
    revision = git('rev-parse', 'HEAD', cwd=cwd)
    print(f'JSON committed={str(changed).lower()}; persistedRevision={revision}')
    return revision


def public_check(root=PUBLIC_DATA, exact=False, attempts=1):
    import requests
    local_path = Path(root) / SLUG / META
    local = read(local_path) if local_path.exists() else None
    base = 'https://fliou0704.github.io/pocky-football/data/'
    for attempt in range(attempts):
        try:
            response = requests.get(base+SLUG+'/'+META, params={'run': os.environ.get('GITHUB_RUN_ID', ''),
                                    'attempt': attempt}, headers={'Cache-Control': 'no-cache'}, timeout=30)
            if response.status_code == 404 and not exact:
                return  # Initial migration only; no public metadata exists yet.
            response.raise_for_status()
            remote = response.json()
            require(local is not None, 'Public generation exists but checkout lacks refresh metadata')
            if exact:
                require(remote['generationId'] == local['generationId'], 'Public generation mismatch')
                # Prove source data reached Pages too, rather than trusting metadata alone.
                for name in ('site.json', f"{SLUG}/{local['season']}/home.json", f"{SLUG}/{local['season']}/teams.json",
                             f"{SLUG}/{local['season']}/team-of-week.json"):
                    r = requests.get(base+name, params={'generation': local['generationId'], 'attempt': attempt},
                                     headers={'Cache-Control': 'no-cache'}, timeout=30)
                    r.raise_for_status()
                    actual = hashlib.sha256(json.dumps(r.json(), sort_keys=True, ensure_ascii=False,
                         separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                    require(actual == local['dataHashes'][name], 'Public source JSON hash mismatch: '+name)
                for extension in ('.webp', '.svg'):
                    name = next((p for p in local.get('assetHashes', {}) if p.endswith(extension)), None)
                    if name:
                        r = requests.get(base+name, params={'generation':local['generationId'],'attempt':attempt}, timeout=30)
                        r.raise_for_status()
                        require(hashlib.sha256(r.content).hexdigest() == local['assetHashes'][name], 'Public logo asset hash mismatch')
            else:
                require(local['lastSuccessfulEspnFetchAt'] >= remote['lastSuccessfulEspnFetchAt'],
                        'Refusing to replace a newer public generation')
            print(f"Public {'verification' if exact else 'rollback guard'} passed; generation={local['generationId']}")
            return
        except (requests.RequestException, ValueError, KeyError):
            if attempt + 1 == attempts:
                raise
            time.sleep(15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('refresh', 'validate', 'persist', 'guard', 'verify'))
    args = parser.parse_args()
    try:
        if args.command == 'refresh':
            refresh()
        elif args.command == 'validate':
            validate(PUBLIC_DATA)
            print('JSON validation=passed')
        elif args.command == 'persist':
            persist()
        elif args.command == 'guard':
            assert_latest()
            public_check()
        else:
            public_check(exact=True, attempts=12)
    except Exception as exc:
        # Do not echo network exception strings: they can contain request/credential details.
        print(f'Pipeline failed ({type(exc).__name__}); phase={args.command}. No success asserted.', flush=True)
        if isinstance(exc, ReleaseError):
            print(str(exc), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
