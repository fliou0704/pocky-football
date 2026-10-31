"""Season-specific fantasy logo archive. No owner IDs or cookies enter public JSON."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
from io import BytesIO
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import time
from urllib.parse import urlparse, urljoin
import xml.etree.ElementTree as ET

import requests
from PIL import Image, ImageOps
from football_exporter import ROOT, PUBLIC_DATA, write_json, read_config

CATALOG = 'team-logos.json'
AUTH_HOST = 'mystique-api.fantasy.espn.com'
MAX_BYTES = 4 * 1024 * 1024


def public_url(url):
    if not isinstance(url, str): return False
    try:
        p = urlparse(url)
        port = p.port
    except ValueError: return False
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.query or p.fragment or port not in (None, 443): return False
    if p.hostname == 'localhost' or p.hostname.endswith(('.local', '.internal')): return False
    try:
        if not ipaddress.ip_address(p.hostname).is_global: return False
    except ValueError: pass
    return True


def observation(team, season):
    owners = sorted(set(team.get('owners') or []))
    candidates = [team.get(k) for k in ('logo', 'logoUrl', 'imageUrl')]
    return {'season': season, 'teamId': team['id'], 'name': team.get('name'), 'abbreviation': team.get('abbrev'),
            'logoFields': {'logo': next((u for u in candidates if public_url(u)), None), 'logoType': team.get('logoType')},
            'ownerHash': hashlib.sha256(json.dumps(owners).encode()).hexdigest() if owners else None}


def encode_image(content, content_type):
    """Decode/validate rather than trusting an HTTP content-type alone."""
    if not content_type.lower().startswith('image/') or len(content) > MAX_BYTES: raise ValueError('Invalid image response')
    if 'svg' in content_type.lower():
        if any(s in content.lower() for s in (b'<!doctype', b'<!entity', b'<?xml-stylesheet')): raise ValueError('Active SVG')
        tree = ET.fromstring(content)
        if tree.tag.split('}')[-1] != 'svg': raise ValueError('Not SVG')
        for node in tree.iter():
            if node.tag.split('}')[-1].lower().startswith('animate') or node.tag.split('}')[-1].lower() == 'set': raise ValueError('Active SVG')
            if node.tag.split('}')[-1].lower() in ('script', 'foreignobject', 'iframe', 'object', 'image', 'use'):
                # ESPN logo packs are self-contained paths; no remote resources/execution.
                if node.tag.split('}')[-1].lower() != 'use' or not all(v.startswith('#') for k,v in node.attrib.items() if k.endswith('href')):
                    raise ValueError('External/active SVG')
            for key, value in node.attrib.items():
                if key.split('}')[-1].lower().startswith('on') or (key.endswith('href') and not value.startswith('#')): raise ValueError('Active SVG attribute')
            text = (node.text or '') + ' '.join(node.attrib.values())
            if re.search(r'(?:https?:|javascript:|@import)', text, re.I): raise ValueError('External SVG resource')
            if any(not target.strip().strip('"\'').startswith('#') for target in re.findall(r'url\(([^)]+)\)',text,re.I)):
                raise ValueError('External SVG resource')
        return content, 'svg'
    with Image.open(BytesIO(content)) as img:
        if img.width * img.height > 16_000_000: raise ValueError('Oversized image')
        img.verify()
    with Image.open(BytesIO(content)) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((256, 256), getattr(Image, 'Resampling', Image).LANCZOS)
        img = img.convert('RGBA' if 'A' in img.getbands() or 'transparency' in img.info else 'RGB')
        output = BytesIO()
        img.save(output, 'WEBP', quality=86, method=6)
        return output.getvalue(), 'webp'


def download(url, cookies=None):
    """Cookies only reach the observed ESPN image host; redirects shed credentials."""
    for redirect in range(4):
        if not public_url(url): raise ValueError('Unsafe logo URL')
        p = urlparse(url)
        addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise ValueError('Nonpublic image host')
        auth = cookies if p.hostname == AUTH_HOST and re.fullmatch(r'/apis/v1/domains/lm/images/[a-fA-F0-9-]{36}',p.path) else None
        # No Session: cookies returned by one host cannot leak to another.
        for attempt in range(2):
            try:
                with requests.get(url, cookies=auth, headers={'User-Agent': 'Mozilla/5.0 (compatible; PockyFootballLogoArchive/1.0)'},
                                  timeout=(5, 15), stream=True, allow_redirects=False) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = urljoin(url, response.headers['Location']); cookies = None
                        break
                    response.raise_for_status()
                    content = bytearray()
                    for chunk in response.iter_content(65536):
                        content.extend(chunk)
                        if len(content) > MAX_BYTES: raise ValueError('Image exceeds limit')
                    return encode_image(bytes(content), response.headers.get('content-type', ''))
            except requests.RequestException as exc:
                if attempt or (isinstance(exc,requests.HTTPError) and exc.response is not None
                               and exc.response.status_code in (401,403,404,410,429)): raise
                time.sleep(.5)
        else: continue
    raise ValueError('Too many image redirects')


def valid_asset(root, asset):
    if not isinstance(asset, str) or not re.fullmatch(r'data/[a-z0-9-]+/team-logos/[a-f0-9]{64}\.(svg|webp)', asset): return False
    path = Path(root)/asset.removeprefix('data/')
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == path.stem


def load_catalog(root, slug):
    path = Path(root)/slug/CATALOG
    return json.loads(path.read_text()) if path.exists() else {'schemaVersion': 1, 'seasons': {}, 'continuity': []}


def connected(catalog, team_id, first, last):
    edges = {(e['teamId'], e['fromSeason'], e['toSeason']) for e in catalog['continuity'] if e['verified']}
    return all((team_id, y, y+1) in edges for y in range(min(first,last), max(first,last)))


def synchronize(root, slug, observations, cookies=None, recheck=False, downloader=None, write_seasons=None):
    root = Path(root)
    downloader = downloader or download
    catalog = load_catalog(root, slug)
    rows = {(r['season'], r['teamId']): r for r in observations}
    edges = {(e['teamId'], e['fromSeason'], e['toSeason']): e for e in catalog['continuity']}
    for (year, tid), row in sorted(rows.items()):
        prior = rows.get((year-1, tid))
        if prior:
            same = bool(row.get('ownerHash')) and row['ownerHash'] == prior.get('ownerHash')
            edges[(tid,year-1,year)] = {'teamId':tid,'fromSeason':year-1,'toSeason':year,'verified':same,
                'evidence':'Same ESPN team ID and nonempty identical owner-ID sets in adjacent season mTeam responses.'}
    catalog['continuity'] = [edges[k] for k in sorted(edges)]
    # Reuse exact observed source URLs across seasons without downloading duplicates.
    cache = {}
    for season in catalog['seasons'].values():
        for record in season.values():
            if record.get('sourceUrl') and valid_asset(root, record.get('asset')):
                cache[record['sourceUrl']] = record
    now = datetime.now(timezone.utc)
    for (year, tid), row in sorted(rows.items()):
        if write_seasons is not None and year not in write_seasons: continue
        season = catalog['seasons'].setdefault(str(year), {})
        previous = season.get(str(tid), {})
        proof = hashlib.sha256(f"{year}:{tid}:{row['ownerHash']}".encode()).hexdigest() if row.get('ownerHash') else None
        identity_changed = proof and previous.get('identityProof') and proof != previous['identityProof']
        if identity_changed or not proof:
            for edge in catalog['continuity']:
                if edge['teamId'] == tid and year in (edge['fromSeason'], edge['toSeason']): edge['verified'] = False
        if identity_changed:
            previous = {}  # Same-season ownership transfer: old identity is not a fallback.
        source = row['logoFields'].get('logo')
        entry = {**previous, 'teamId':tid, 'season':year, 'name':row['name'], 'abbreviation':row.get('abbreviation'),
                 'observedSourceUrl':source if public_url(source) else None, 'logoType':row['logoFields'].get('logoType')}
        if proof: entry['identityProof'] = proof
        found = None
        failure = None
        if public_url(source):
            cached = cache.get(source)
            immutable = urlparse(source).hostname == AUTH_HOST or '/lm-static/' in source
            fresh = cached and (immutable or now - datetime.fromisoformat(cached['verifiedAt']) < timedelta(days=7))
            failed_recently = (previous.get('lastFailureUrl') == source and previous.get('lastFailureAt')
                               and now - datetime.fromisoformat(previous['lastFailureAt']) < timedelta(days=1))
            if failed_recently and not recheck:
                from football_http import cache_hit
                cache_hit('logo-negative-cache')
                failure = previous.get('observedSourceStatus','unavailable')
            elif cached and fresh and not recheck:
                from football_http import cache_hit
                cache_hit('logo-archive')
                found = cached
            else:
                try:
                    content, extension = downloader(source, cookies)
                    digest = hashlib.sha256(content).hexdigest()
                    relative = f'{slug}/team-logos/{digest}.{extension}'
                    path = root/relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not path.exists():
                        assets = list(path.parent.glob('*.*'))
                        if len(assets) >= 256 or sum(p.stat().st_size for p in assets) + len(content) > 10*1024*1024:
                            raise ValueError('Logo archive budget exceeded')
                        path.write_bytes(content)
                    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                        path.write_bytes(content)  # Repair only with newly verified source bytes.
                    found = {'asset':'data/'+relative,'sourceUrl':source,'verifiedAt':now.isoformat()}
                    cache[source] = found
                except (requests.RequestException, ValueError, OSError, ET.ParseError, Image.DecompressionBombError) as exc:
                    # A logo outage cannot erase a working archive or stop score ingestion.
                    failure = ('http_'+str(exc.response.status_code)) if isinstance(exc, requests.HTTPError) and exc.response is not None else type(exc).__name__
                    entry.update(lastFailureAt=now.isoformat(),lastFailureUrl=source)
        entry['observedSourceStatus'] = 'verified' if found else failure or 'missing'
        if found:
            entry.pop('lastFailureAt',None); entry.pop('lastFailureUrl',None)
            entry.update({k:found[k] for k in ('asset','sourceUrl','verifiedAt')})
            entry.update(provenance='exact-espn-season', sourceSeason=year,
                         logoType=row['logoFields'].get('logoType'), status='verified')
        elif previous.get('provenance') in ('exact-espn-season','archived-exact-season') and valid_asset(root, previous.get('asset')):
            entry.update(provenance='archived-exact-season', status='preserved')
        else:
            entry.update(asset=None, provenance='generated-badge', sourceSeason=None, status='unavailable')
        season[str(tid)] = entry
    # Fallback requires an explicit verified continuity path, never just a name or ID.
    for (year, tid), row in sorted(rows.items()):
        if write_seasons is not None and year not in write_seasons: continue
        entry = catalog['seasons'][str(year)][str(tid)]
        if entry.get('asset'): continue
        candidates = [(int(y), ts[str(tid)]) for y,ts in catalog['seasons'].items() if str(tid) in ts
                      and ts[str(tid)].get('provenance') in ('exact-espn-season','archived-exact-season')
                      and valid_asset(root, ts[str(tid)].get('asset')) and connected(catalog,tid,year,int(y))]
        if candidates:
            source_year, record = min(candidates, key=lambda p:(abs(p[0]-year),p[0]))
            entry.update(asset=record['asset'],sourceUrl=record['sourceUrl'],sourceSeason=source_year,
                         provenance='same-franchise-fallback',status='fallback', verifiedAt=record['verifiedAt'])
    write_json(root/slug/CATALOG, catalog)
    return catalog


def read_teams(client):
    """Bounded read of the library's real mTeam endpoint, without its unbounded timeout."""
    endpoint = client.LEAGUE_ENDPOINT
    if not public_url(endpoint) or urlparse(endpoint).hostname != 'lm-api-reads.fantasy.espn.com':
        raise ValueError('Unexpected ESPN metadata endpoint')
    with requests.get(endpoint, params={'view':'mTeam'}, cookies=client.cookies,
                      timeout=(5,15), allow_redirects=False) as response:
        response.raise_for_status()
        raw = response.json()
    if not isinstance(raw,dict) or not isinstance(raw.get('teams'),list) or not raw['teams']:
        raise ValueError('Incomplete team metadata')
    return raw['teams']


def refresh_catalog(client, root, slug, season, cookies):
    """Read logo metadata only; do not refresh historical sports snapshots."""
    try:
        rows = [observation(t, season) for t in read_teams(client)]
    except Exception:
        return load_catalog(root, slug)
    config = read_config(slug)
    if season == config['season']:
        from espn_api.requests.espn_requests import EspnFantasyRequests
        for year in range(config.get('firstSeason',season), season):
            try:
                historical = EspnFantasyRequests('nfl',year,config['leagueId'],cookies=cookies)
                rows += [observation(t,year) for t in read_teams(historical)]
            except Exception: pass  # Preserve archives on optional metadata failures.
    # Six small mTeam reads discover restored historical images; no historical scores/rosters are fetched.
    catalog = synchronize(root,slug,rows,cookies)
    counts = {}
    for records in catalog['seasons'].values():
        for record in records.values(): counts[record['provenance']] = counts.get(record['provenance'],0)+1
    print('Team logo archive:', json.dumps(counts,sort_keys=True))
    return catalog


def validate_catalog(root, slug):
    catalog = load_catalog(root,slug)
    for path in (Path(root)/slug/'team-logos').glob('*'):
        if path.is_file() and re.fullmatch(r'[a-f0-9]{64}\.(svg|webp)',path.name) and hashlib.sha256(path.read_bytes()).hexdigest() != path.stem:
            raise ValueError('Invalid archived team logo asset')
    for year, records in catalog['seasons'].items():
        for tid, row in records.items():
            if row['teamId'] != int(tid) or row['season'] != int(year): raise ValueError('Logo identity mismatch')
            if row.get('asset') and not row['asset'].startswith('data/'+slug+'/team-logos/'): raise ValueError('Foreign league logo asset')
            if row.get('provenance') in ('exact-espn-season','archived-exact-season') and row.get('sourceSeason') != int(year):
                raise ValueError('Incorrect exact-season provenance')
            if row.get('asset') and not valid_asset(root,row['asset']): raise ValueError('Invalid archived team logo asset')
            if row.get('sourceUrl') and not public_url(row['sourceUrl']): raise ValueError('Unsafe public logo provenance URL')
            if row.get('provenance') == 'same-franchise-fallback' and not connected(catalog,int(tid),int(year),row['sourceSeason']):
                raise ValueError('Unverified franchise logo fallback')
            if row.get('provenance') == 'same-franchise-fallback':
                source = catalog['seasons'].get(str(row['sourceSeason']),{}).get(str(tid),{})
                if source.get('asset') != row.get('asset') or source.get('provenance') not in ('exact-espn-season','archived-exact-season'):
                    raise ValueError('Alternate logo source does not match verified franchise')
    return catalog


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--league', default='pocky-football')
    parser.add_argument('--recheck', action='store_true')
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=False)
    config=read_config(args.league)
    cookies={'espn_s2':os.environ.get('ESPN_S2'),'SWID':os.environ.get('SWID')}
    if not all(cookies.values()): raise SystemExit('ESPN_S2 / SWID missing')
    from espn_api.requests.espn_requests import EspnFantasyRequests
    rows=[]
    try:
        for year in range(config['firstSeason'],config['season']+1):
            client=EspnFantasyRequests('nfl',year,config['leagueId'],cookies=cookies)
            rows += [observation(t,year) for t in read_teams(client)]
        catalog=synchronize(PUBLIC_DATA,args.league,rows,cookies,args.recheck)
        validate_catalog(PUBLIC_DATA,args.league)
        from data_refresh import update_derived_metadata
        update_derived_metadata(PUBLIC_DATA, builder='team-logos-v1')
        counts={}
        for records in catalog['seasons'].values():
            for record in records.values(): counts[record['provenance']]=counts.get(record['provenance'],0)+1
        print('Logo recovery:',json.dumps(counts))
    except Exception as exc:
        raise SystemExit('Logo recovery failed ('+type(exc).__name__+'); no credential details logged.') from None


if __name__ == '__main__': main()
