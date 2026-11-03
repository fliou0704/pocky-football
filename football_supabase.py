"""Optional backend output of an already validated live release; never calls ESPN."""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from football_exporter import ROOT, PUBLIC_DATA
from data_refresh import validate, read, SLUG, META

PROJECT = 'https://gkrqrlvimigznlbqcxie.supabase.co'
FIELDS = set('schemaVersion leagueId season week matchups lineups adjustments semantics baseGenerationId sourceFileHashes snapshotId fetchedAt'.split())


class PublicationError(ValueError):
    pass


def scan(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if re.sub('[^a-z]','',key.lower()) in ('cookies','cookie','credentials','authorization','headers','owners','password','token','espns','swid','secretkey'):
                raise PublicationError('Forbidden snapshot field')
            scan(child)
    elif isinstance(value, list):
        for child in value: scan(child)
    elif isinstance(value, str):
        for name in ('ESPN_S2','SWID','SUPABASE_SECRET_KEY','SUPABASE_PUBLISHABLE_KEY'):
            secret = os.environ.get(name,'')
            if len(secret) >= 12 and secret in value:
                raise PublicationError('Credential in snapshot')
        if 'sb_secret_' in value or 'sb_publishable_' in value:
            raise PublicationError('Credential marker in snapshot')


def instant(value):
    value = re.sub(r'\.(\d{1,6})(?=Z$|[+-]\d{2}:\d{2}$)',lambda m:'.'+m[1].ljust(6,'0'),value)
    result = datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None: raise PublicationError('Missing timestamp timezone')
    return result


def publish(snapshot, meta, url, secret, public, request=requests.request):
    """Caller validates release; shape/digest/provenance are checked again at this boundary."""
    from football_live import digest
    if set(snapshot) != FIELDS or snapshot['leagueId'] != 668411840 or meta.get('mode') != 'live':
        raise PublicationError('Invalid live envelope')
    scan(snapshot)
    content = {k:v for k,v in snapshot.items() if k not in ('fetchedAt','snapshotId')}
    if digest(content) != snapshot['snapshotId'] or not re.fullmatch('[a-f0-9]{64}',meta['generationId']):
        raise PublicationError('Invalid snapshot revision')
    if instant(snapshot['fetchedAt']) > datetime.now(timezone.utc)+timedelta(minutes=5):
        raise PublicationError('Future snapshot')
    if url.rstrip('/') != PROJECT or not secret or not public:
        raise PublicationError('Missing credentials or unexpected project')
    def call(method, path, key, **kwargs):
        response = request(method,PROJECT+'/rest/v1/'+path,headers={'apikey':key,'Content-Type':'application/json'},
                           timeout=(5,20),allow_redirects=False,**kwargs)
        try:
            if response.status_code != 200: raise PublicationError('Supabase request failed; check migration/access')
            return response.json()
        finally: response.close()
    params={'league_id':'eq.668411840','season':'eq.'+str(snapshot['season']),
            'select':'snapshot,revision,generation_id,source_at,is_public'}
    rows = call('GET','football_live_snapshots',secret,params=params)
    action = 'unchanged'
    if rows and (rows[0]['snapshot']['week'] > snapshot['week'] or instant(rows[0]['source_at']) > instant(snapshot['fetchedAt'])):
        raise PublicationError('Stale publication refused')
    if not rows or rows[0]['revision'] != snapshot['snapshotId']:
        result=call('POST','rpc/publish_football_snapshot',secret,json={'p_snapshot':snapshot,'p_generation':meta['generationId']})
        action=result.get('action')
        if action not in ('published','unchanged'): raise PublicationError('Stale/conflicting publication refused')
    # Independent authenticated and public readback; no mutation probes or test rows.
    for key in (secret, public):
        actual=call('GET','football_live_snapshots',key,params=params)
        if len(actual)!=1 or actual[0]['snapshot']!=snapshot or actual[0]['revision']!=snapshot['snapshotId'] or not actual[0]['is_public']:
            raise PublicationError('Publication readback mismatch')
        if action == 'published' and actual[0]['generation_id'] != meta['generationId']:
            raise PublicationError('Generation readback mismatch')
    return action


def main():
    load_dotenv(ROOT/'.env',override=False)
    try:
        meta=read(PUBLIC_DATA/SLUG/META)
        if meta.get('mode') != 'live':
            print('Supabase skipped: no current validated live overlay; full JSON remains on Pages')
            return 0
        validate(PUBLIC_DATA,require_metadata=True)
        snapshot=read(PUBLIC_DATA/SLUG/'live.json')
        action=publish(snapshot,meta,os.environ.get('SUPABASE_URL',''),os.environ.get('SUPABASE_SECRET_KEY',''),os.environ.get('SUPABASE_PUBLISHABLE_KEY',''))
        print('Supabase football publication='+action+'; authenticated/public readback=verified')
        return 0
    except Exception:
        print('Supabase football publication FAILED; Pages pipeline remains independent. Check migration, credentials and backend availability.')
        return 1


if __name__ == '__main__': raise SystemExit(main())
