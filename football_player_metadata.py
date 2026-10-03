"""Data-only identity layer. No ESPN credentials or per-player biography requests."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlsplit
import requests
from football_exporter import write_json

NFLVERSE = 'https://github.com/nflverse/nflverse-data/releases/download/players/players.csv'
SLEEPER = 'https://api.sleeper.app/v1/players/nfl'
ROOT = Path(__file__).resolve().parent


def url(value):
    if not isinstance(value, str): return None
    p = urlsplit(value)
    return value if p.scheme == 'https' and p.hostname and not p.username and not p.password else None


def integer(value):
    try:
        n = float(value)
        return int(n) if n.is_integer() else None
    except (ValueError, TypeError): return None


def clean(value):
    return value if value not in (None, '', '—', 'NA', 'N/A') else None


def walk(value):
    if isinstance(value, dict):
        if 'playerId' in value: yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value, list):
        for child in value: yield from walk(child)


def universe(folder, first=2021, last=None):
    if last is None: last = json.loads((ROOT/'leagues.json').read_text())['pocky-football']['season']
    result = {}; files = []; malformed = []
    for year in range(first, last + 1):
        season = folder / str(year)
        required = [season / f for f in ('teams.json', 'draft.json', 'activity.json')]
        if any(not p.exists() for p in required): raise ValueError(f'Missing normalized season {year}')
        paths = required + sorted((season / 'lineups').glob('*.json'), key=lambda p: int(p.stem))
        for path in paths:
            files.append(str(path.relative_to(folder)))
            for row in walk(json.loads(path.read_text())):
                pid = row['playerId']
                if type(pid) is not int or pid == 0:
                    malformed.append({'file': str(path.relative_to(folder)), 'value': str(pid)}); continue
                p = result.setdefault(pid, {'espnId': pid, 'seasons': set(), 'observedIn': set()})
                p['seasons'].add(year); p['observedIn'].add(str(path.relative_to(folder)))
                for field in ('name', 'position', 'nflTeam'):
                    value = clean(row.get(field) or (row.get('playerName') if field == 'name' else None))
                    if value: p[field] = value
        scoring = season / 'player-scoring.json'
        if scoring.exists():
            for row in walk(json.loads(scoring.read_text())):
                if row['playerId'] not in result: continue
                for field in ('name', 'position'):
                    if clean(row.get(field)): result[row['playerId']].setdefault(field, row[field])
    return result, files, malformed


def index(rows, key):
    groups = defaultdict(list)
    for row in rows:
        pid = integer(row.get(key))
        if pid and pid > 0: groups[pid].append(row)
    # Exact duplicate rows collapse; ambiguous ID collisions never choose arbitrarily.
    unique = {}; collisions = []
    for pid, group in sorted(groups.items()):
        distinct = {json.dumps(r, sort_keys=True): r for r in group}
        if len(distinct) == 1: unique[pid] = next(iter(distinct.values()))
        else: collisions.append(pid)
    return unique, collisions


def build(known, nflrows, sleeperrows=(), image_check=None):
    nfl, collisions = index(nflrows, 'espn_id'); sleeper, scollisions = index(sleeperrows, 'espn_id')
    players = []; misses = []; image_results = {}
    for pid, observed in sorted(known.items()):
        defense = pid < 0 or observed.get('position') == 'D/ST'
        p = {'espnId': pid, 'entityType': 'team_defense' if defense else 'player',
             'name': observed.get('name'), 'seasons': sorted(observed['seasons']),
             'observedIn': sorted(observed['observedIn'])}
        if defense:
            team = observed.get('nflTeam')
            p.update(position='D/ST', nflTeam=team, logo=url(f'https://a.espncdn.com/i/teamlogos/nfl/500/{team.lower()}.png') if team else None,
                     match={'method': 'espn_team_defense_id'})
            players.append(p); continue
        n = nfl.get(pid, {}); s = sleeper.get(pid, {}); sources = {}
        p['match'] = {'method': 'nflverse_espn_id' if n else 'sleeper_espn_id' if s else 'espn_only',
                      'sleeperEspnIdMatch': bool(s), 'nflverseIdCollision': pid in collisions}
        def choose(field, choices, converter=clean):
            p[field] = None
            for source, value in choices:
                value = converter(value)
                if value is not None:
                    p[field] = value; sources[field] = source; break
        choose('name', [('espn', observed.get('name')), ('nflverse', n.get('display_name')), ('sleeper', s.get('full_name'))])
        choose('position', [('espn', observed.get('position')), ('nflverse', n.get('position')), ('sleeper', s.get('position'))])
        for field, nk, sk in [('positionGroup','position_group',None), ('heightInches','height','height'), ('weightPounds','weight','weight'),
                              ('birthDate','birth_date','birth_date'), ('college','college_name','college'), ('jerseyNumber','jersey_number','number'),
                              ('nflTeam','latest_team','team'), ('rookieSeason','rookie_season',None), ('lastSeason','last_season',None)]:
            def convert(v):
                if field == 'heightInches' and isinstance(v,str) and '-' in v:
                    a,b=v.split('-',1);return integer(a)*12+integer(b) if integer(a) is not None and integer(b) is not None else None
                return integer(v) if field in ('heightInches','weightPounds','rookieSeason','lastSeason') else str(v) if clean(v) is not None else None
            choices=[('nflverse',n.get(nk)),('sleeper',s.get(sk))]
            choose(field,choices,convert)
        p['ids'] = {k: clean(n.get(v)) for k,v in [('gsis','gsis_id'),('nfl','nfl_id'),('pfr','pfr_id')]}
        p['nflDraft'] = {k: integer(n.get(v)) for k,v in [('year','draft_year'),('round','draft_round'),('overallPick','draft_pick')]}
        # Zero denotes undrafted, not an actual round/pick.
        for k in ('round','overallPick'):
            if p['nflDraft'][k] == 0: p['nflDraft'][k] = None
        p['nflDraft']['team'] = clean(n.get('draft_team'))
        p['headshot'] = None; p['headshotValidation'] = None
        candidates=[('nflverse',url(n.get('headshot'))),('espn',f'https://a.espncdn.com/i/headshots/nfl/players/full/{pid}.png')]
        for source, candidate in candidates:
            if not candidate: continue
            if image_check:
                if candidate not in image_results: image_results[candidate]=image_check(candidate)
                status=image_results[candidate]
                if status != 'valid': continue
            else: status='syntax_only'
            p['headshot']=candidate; sources['headshot']=source; p['headshotValidation']=status; break
        p['fieldSources']=sources
        if not n:
            misses.append({'espnId':pid,'name':p['name'],'position':p['position'],'seasons':p['seasons'],
                           'reason':'ambiguous_nflverse_id' if pid in collisions else 'no_nflverse_espn_id',
                           'sleeperMatch':bool(s)})
        players.append(p)
    validate(players)
    humans=[p for p in players if p['entityType']=='player']; count=len(humans)
    coverage={}
    for field in ('headshot','heightInches','weightPounds','birthDate','college','position','nflTeam','jerseyNumber'):
        present=sum(p.get(field) is not None for p in humans)
        coverage[field]={'count':present,'percent':round(100*present/count,2) if count else 0}
    for label, predicate in [('nflDraftAny',lambda p:any(p['nflDraft'].values())),('nflDraftComplete',lambda p:all(p['nflDraft'].values()))]:
        present=sum(bool(predicate(p)) for p in humans);coverage[label]={'count':present,'percent':round(100*present/count,2) if count else 0}
    audit={'totalEntities':len(players),'humanPlayers':count,'teamDefenses':len(players)-count,
           'nflverseMatches':sum(p['match']['method']=='nflverse_espn_id' for p in humans),
           'sleeperFallbackMatches':sum(p['match']['method']=='sleeper_espn_id' for p in humans),
           'espnOnlyPlayers':sum(p['match']['method']=='espn_only' for p in humans),
           'unresolvedIdentityPlayers':[p['espnId'] for p in humans if not p['name']],
           'nflverseMatchPercent':round(100*sum(p['match']['method']=='nflverse_espn_id' for p in humans)/count,2) if count else 0,
           'missingFields':{field:[{'espnId':p['espnId'],'name':p['name'],'position':p['position'],'lastSeason':p['lastSeason']}
                                  for p in humans if p.get(field) is None] for field in coverage if not field.startswith('nflDraft')},
           'missingNflDraft':[{'espnId':p['espnId'],'name':p['name'],'position':p['position'],
                              'reason':'no_draft_fields_in_source; may be undrafted, not inferred'}
                             for p in humans if not any(p['nflDraft'].values())],
           'nflverseMissing':misses,'nflverseIdCollisions':collisions,'sleeperIdCollisions':scollisions,
           'coverage':coverage,'imageChecks':dict(sorted(image_results.items()))}
    return players,audit


def validate(players):
    ids=[p['espnId'] for p in players]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate ESPN identity')
    gsis=[p['ids']['gsis'] for p in players if p['entityType']=='player' and p['ids']['gsis']]
    if len(gsis)!=len(set(gsis)): raise ValueError('Human GSIS identity duplicated')
    for p in players:
        if p['entityType']=='team_defense':
            if any(k in p for k in ('heightInches','weightPounds','birthDate','college','headshot','nflDraft')): raise ValueError('Defense biography')
            continue
        for k,lo,hi in [('heightInches',55,90),('weightPounds',100,450)]:
            if p[k] is not None and (type(p[k]) is not int or not lo<=p[k]<=hi): raise ValueError(f'Invalid {k}')
        if p['birthDate']: date.fromisoformat(p['birthDate'])
        if p['headshot'] is not None and not url(p['headshot']): raise ValueError('Invalid headshot')
        for k,lo,hi in [('year',1936,datetime.now(timezone.utc).year+1),('round',1,32),('overallPick',1,600)]:
            v=p['nflDraft'][k]
            if v is not None and (type(v) is not int or not lo<=v<=hi): raise ValueError('Invalid NFL draft')


def cached_source(cache, name, source, refresh):
    path=cache/name
    if refresh or not path.exists():
        response=requests.get(source,timeout=60);response.raise_for_status()
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(response.content)
    return path


def generate(folder, cache, refresh=False, use_sleeper=False, check_images=False, first=2021,last=2026,recheck_images=False):
    known,files,malformed=universe(folder,first,last)
    nf=cached_source(cache,'nflverse.csv',NFLVERSE,refresh)
    rows=list(csv.DictReader(nf.open())); sleeper=[]; source_paths={'nflverse':nf}
    if use_sleeper:
        sf=cached_source(cache,'sleeper.json',SLEEPER,refresh);sleeper=list(json.loads(sf.read_text()).values());source_paths['sleeper']=sf
    checks=json.loads((cache/'headshots.json').read_text()) if (cache/'headshots.json').exists() and not recheck_images else {}
    def image_check(candidate):
        if candidate in checks:return checks[candidate]
        try:
            with requests.get(candidate,stream=True,timeout=8) as r:
                status='valid' if r.status_code==200 and r.headers.get('content-type','').lower().startswith('image/') and url(r.url) else 'invalid' if r.status_code in (404,410) else 'unverified'
        except requests.RequestException:status='unverified'
        checks[candidate]=status;return status
    if check_images:
        primary, _ = index(rows, 'espn_id')
        candidates = {url(primary.get(pid, {}).get('headshot')) for pid in known if pid > 0}
        candidates.discard(None)
        with ThreadPoolExecutor(max_workers=12) as pool:
            list(pool.map(image_check, sorted(candidates)))
        fallback = [f'https://a.espncdn.com/i/headshots/nfl/players/full/{pid}.png'
                    for pid in known if pid > 0 and checks.get(url(primary.get(pid, {}).get('headshot'))) != 'valid']
        with ThreadPoolExecutor(max_workers=12) as pool:
            list(pool.map(image_check, sorted(fallback)))
    players,audit=build(known,rows,sleeper,image_check if check_images else None)
    if check_images:write_json(cache/'headshots.json',checks)
    stamp=datetime.now(timezone.utc).isoformat()
    sources={name:{'url':NFLVERSE if name=='nflverse' else SLEEPER,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   'cachedAt':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()} for name,path in source_paths.items()}
    payload={'schemaVersion':1,'generatedAt':stamp,'seasons':list(range(first,last+1)),
             'profileSemantics':'Latest source snapshot; team, jersey, position and headshot are not historical season facts.',
             'sources':sources,'players':players}
    audit.update(schemaVersion=1,generatedAt=stamp,sources=sources,universeFiles=files,malformedIds=malformed)
    write_json(folder/'players.json',payload);write_json(folder/'player-metadata-audit.json',audit)
    return audit


if __name__=='__main__':
    config=json.loads((ROOT/'leagues.json').read_text())['pocky-football']
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true');parser.add_argument('--recheck-images',action='store_true');parser.add_argument('--sleeper',action='store_true');parser.add_argument('--check-headshots',action='store_true')
    parser.add_argument('--first-season',type=int,default=config.get('firstSeason',2021));parser.add_argument('--last-season',type=int,default=config['season'])
    args=parser.parse_args()
    audit=generate(ROOT/'frontend/public/data/pocky-football',ROOT/'.cache/player-metadata',args.refresh,args.sleeper,args.check_headshots,args.first_season,args.last_season,args.recheck_images)
    print(json.dumps({k:v for k,v in audit.items() if k in ('totalEntities','humanPlayers','teamDefenses','nflverseMatches','sleeperFallbackMatches','espnOnlyPlayers','coverage')},indent=2))
