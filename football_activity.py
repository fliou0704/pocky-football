"""Minimal executed fantasy roster movements from ESPN's period and playercard views.

Coverage distinguishes complete source retrieval from independent counter agreement.
Pending/rejected activity and account metadata never enter the public contract.
"""
from collections import defaultdict, Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


def normalize_transaction(raw, season, names, team_ids, uses_faab=False):
    # ESPN archived executed trades retain isPending=True; status is authoritative.
    if raw.get('status') != 'EXECUTED' or raw.get('id') is None:
        return None
    movements = defaultdict(lambda: {'playersAdded': [], 'playersDropped': []})
    kinds = set()
    for item in raw.get('items', []):
        kind, player_id = item.get('type'), item.get('playerId')
        if kind not in ('ADD', 'DROP', 'TRADE', 'DRAFT') or not isinstance(player_id, int) or isinstance(player_id,bool) or player_id == 0:
            continue
        kinds.add(kind)
        player = {'playerId': player_id, 'name': names.get(player_id)}
        origin, destination = item.get('fromTeamId'), item.get('toTeamId')
        if kind in ('DROP', 'TRADE') and type(origin) is int and origin in team_ids:
            movements[origin]['playersDropped'].append(player)
        if kind in ('ADD', 'TRADE', 'DRAFT') and type(destination) is int and destination in team_ids:
            movements[destination]['playersAdded'].append(player)
    if not movements:
        return None
    source_type = raw.get('type')
    kind = ('trade' if 'TRADE' in kinds else 'draft' if 'DRAFT' in kinds else
            'waiver_add' if source_type == 'WAIVER' and 'ADD' in kinds else
            'free_agent_add' if source_type == 'FREEAGENT' and 'ADD' in kinds else
            'drop' if kinds == {'DROP'} else None)
    if kind is None:
        return None
    timestamp = raw.get('processDate') or raw.get('proposedDate')
    if isinstance(timestamp,bool) or not isinstance(timestamp, (float, int)) or not math.isfinite(timestamp):
        return None
    bid = raw.get('bidAmount')
    faab = bid if uses_faab and kind == 'waiver_add' and isinstance(bid, (int, float)) and math.isfinite(bid) else None
    event = {'id': 'event-' + hashlib.sha256(str(raw['id']).encode()).hexdigest()[:20],
            'season': season, 'timestamp': datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat(),
            'timestampKind': 'processed' if raw.get('processDate') else 'proposed',
            'type': kind, 'week': raw.get('scoringPeriodId'), 'status': 'executed',
            'teams': [{'teamId': team, **{key: sorted({p['playerId']:p for p in rows}.values(), key=lambda p:p['playerId'])
                                        for key,rows in changes.items()}}
                      for team,changes in sorted(movements.items())],
            'faab': faab, 'waiverType': raw.get('executionType') if kind == 'waiver_add' else None}
    if kind == 'trade':
        event['transfers'] = [{'playerId':i['playerId'],'name':names.get(i['playerId']),
                               'fromTeamId':i.get('fromTeamId'),'toTeamId':i.get('toTeamId')}
                              for i in raw.get('items',[]) if i.get('type') == 'TRADE' and isinstance(i.get('playerId'),int) and i['playerId'] != 0]
        event['assetCoverage'] = {'draftPickTransfersObserved':sum(bool(i.get('overallPickNumber') or i.get('draftPickId')) for i in raw.get('items',[])),
                                  'budgetTransfersObserved':sum(bool(i.get('acquisitionBudget')) for i in raw.get('items',[]))}
    return event


def movements_for_team(activity, team_id):
    """Reusable chronological acquisition/drop/trade evidence, not inferred membership."""
    return [{key: event[key] for key in ('id', 'season', 'timestamp', 'type', 'week')}
            | changes for event in activity['events'] for changes in event['teams']
            if changes['teamId'] == team_id]


def reconcile_activity(season, names, team_ids, periods, cards, metadata, failed_periods=(), universe_succeeded=True):
    """Merge same source IDs, retaining rich executed transfers from player histories."""
    from football_activity_audit import validate_events, ownership_audit, compare_counters
    transactions={}; origins=defaultdict(set); appearances=Counter(); conflicts=set()
    by_source=defaultdict(set)
    for source, rows in [('period', [t for ts in periods.values() for t in ts]),
                         ('playercard', [t for p in cards for t in p.get('transactions',[])])]:
        for t in rows:
            if 'id' not in t:continue
            key=t['id'];appearances[key]+=1;origins[key].add(source);by_source[source].add(key)
            previous=transactions.get(key)
            if previous and previous.get('status')=='EXECUTED' and t.get('status')=='EXECUTED':
                fields=('type','playerId','fromTeamId','toTeamId')
                shape=lambda raw: sorted(json.dumps({f:i.get(f) for f in fields},sort_keys=True) for i in raw.get('items',[]) if i.get('type') in ('ADD','DROP','TRADE','DRAFT'))
                if shape(previous)!=shape(t):conflicts.add(key)
            if previous is None or (t.get('status')=='EXECUTED' and t.get('items')):
                transactions[key]=t
    returned={p['playerId'] for p in cards}
    known=set(names)|{i['playerId'] for t in transactions.values() for i in t.get('items',[]) if isinstance(i.get('playerId'),int) and not isinstance(i.get('playerId'),bool) and i['playerId']!=0}
    for p in cards:names[p['playerId']]=p.get('name') or names.get(p['playerId'])
    uses_faab=metadata.get('usesFaab',False)
    events=[e for t in transactions.values() if (e:=normalize_transaction(t,season,names,team_ids,uses_faab)) is not None]
    events.sort(key=lambda e:(e['timestamp'],e['id']))
    audit=validate_events(events,team_ids);ownership=ownership_audit(events)
    counters=compare_counters(events,metadata.get('teamCounters',{}))
    counters['teamCoverageCompleted']=set(map(int,metadata.get('teamCounters',{})))==set(team_ids)
    if not counters['teamCoverageCompleted']:
        counters['allTotalsMatch']=False
        counters['dropsAndTradesMatch']=False
    missing=known-returned
    clean=set(map(int,periods))==set(range(metadata['through']+2)) and not failed_periods and universe_succeeded and not missing and not audit['issues'] and not audit['duplicateEventIds'] and not audit['semanticDuplicateGroups'] and not ownership['anomalies'] and not conflicts and all(p['name'] is not None for e in events for t in e['teams'] for k in ('playersAdded','playersDropped') for p in t[k])
    classification=('independently_verified_counts' if clean and counters['allTotalsMatch'] else 'likely_complete' if clean else 'partial')
    through=metadata['through']; excluded=Counter(); card_only=Counter(); executed_period=set()
    for key,t in transactions.items():
        event=normalize_transaction(t,season,names,team_ids,uses_faab)
        if event is None:excluded[f"{t.get('type','unknown')}:{t.get('status','unspecified')}"]+=1
        elif origins[key]=={'playercard'}:card_only[event['type']]+=1
        if event and 'period' in origins[key]:executed_period.add(key)
    coverage={'complete':classification=='independently_verified_counts','status':classification,
              'scope':'Executed player roster movements through the observed transaction period; excludes failed/pending claims and lineup-only changes.',
              'sources':['mTransactions2','kona_playercard','mTeam.transactionCounter'],
              'cardOnlyTradeExplanation':'Period feed acceptance placeholders have no executed status/items and distinct source IDs; executed playercard transfers supply the movement.',
              'queriedThroughPeriod':through,'requestedPeriods':list(range(through+2)),
              'successfulPeriods':sorted(int(p) for p in periods),'failedPeriods':list(failed_periods),
              'sourceSweepCompleted':not failed_periods and set(map(int,periods))==set(range(through+2)),
              'playerUniverseSweepCompleted':universe_succeeded,'playerUniverseReturnedCount':len(returned),'knownPlayerCoverageCompleted':not missing,
              'requestedPlayerCount':len(known),'returnedPlayerCount':len(returned),'missingPlayerCount':len(missing),
              'failedCardPlayerCount':len(missing),'unknownPlayerNames':sum(p['name'] is None for e in events for t in e['teams'] for k in ('playersAdded','playersDropped') for p in t[k]),
              'sourceEventCount':len(transactions),'sourceUniqueCounts':{k:len(v) for k,v in by_source.items()},
              'sourceAppearances':sum(appearances.values()),'repeatedSourceIdAppearancesMerged':sum(appearances.values())-len(transactions),
              'overlappingSourceIds':len(by_source['period']&by_source['playercard']),
              'playercardOnlyExecutedCounts':dict(card_only),'executedPayloadConflictCount':len(conflicts),
              'excludedSourceCounts':dict(sorted(excluded.items())), 'executedMovementCount':len(events),
              'firstTimestamp':events[0]['timestamp'] if events else None,'lastTimestamp':events[-1]['timestamp'] if events else None,
              'usesFaab':bool(uses_faab),'independentCounters':counters,
              'independentCountAgreement':{'drops':counters['dropsAndTradesMatch'],'trades':counters['dropsAndTradesMatch'],'acquisitions':counters['allTotalsMatch']},
              'limitation':'Counts verify quantities, not every historical detail. Historical acquisition counters differ for some boundary-period moves; discrepancies remain explicit. No failed claims, private member IDs, or inferred historical waiver priority are published.'}
    return {'schemaVersion':2,'season':season,'generatedAt':datetime.now(timezone.utc).isoformat(),
            'coverage':coverage,'validation':{**audit,'ownership':ownership},'events':events}


def collect_activity(client, season, names, team_ids):
    """Sweep every period plus a boundary probe and the full unfiltered player universe."""
    raw=client.league_get(params={'view':['mStatus','mSettings','mTeam']})
    status=raw['status'];through=max(int(status.get('latestScoringPeriod',0)),int(status.get('transactionScoringPeriod',0)))
    metadata={'through':through,'usesFaab':raw['settings']['acquisitionSettings'].get('isUsingAcquisitionBudget',False),
              'teamCounters':{str(t['id']):t.get('transactionCounter',{}) for t in raw.get('teams',[])}}
    periods={};failed=[]
    for period in range(through+2):
        try:
            data=client.league_get(params={'view':'mTransactions2','scoringPeriodId':period})
            if not isinstance(data,dict) or 'status' not in data:raise ValueError('Missing activity response')
            periods[period]=data.get('transactions',[])
        except Exception:failed.append(period)
    cards=[];universe_succeeded=False
    filters={'players':{'filterStatsForTopScoringPeriodIds':{'value':int(status.get('finalScoringPeriod',17)),
                        'additionalValue':[f'00{season}',f'10{season}']}}}
    try:
        data=client.league_get(params={'view':'kona_playercard'},headers={'x-fantasy-filter':json.dumps(filters)})
        players=data.get('players',[])
        if not players:raise ValueError('Empty player universe')
        cards=[{'playerId':p['id'],'name':p.get('player',{}).get('fullName'),'transactions':p.get('transactions',[])} for p in players]
        universe_succeeded=True
    except Exception:pass
    known=set(names)|{i['playerId'] for ts in periods.values() for t in ts for i in t.get('items',[]) if isinstance(i.get('playerId'),int)}
    missing=sorted(known-{p['playerId'] for p in cards})
    for offset in range(0,len(missing),100):
        try:
            data=client.get_player_card(missing[offset:offset+100],int(status.get('finalScoringPeriod',17)))
            cards.extend({'playerId':p['id'],'name':p.get('player',{}).get('fullName'),'transactions':p.get('transactions',[])} for p in data.get('players',[]))
        except Exception:pass
    # Also check players referenced only in card trade counterparts.
    referenced={i['playerId'] for p in cards for t in p['transactions'] for i in t.get('items',[]) if isinstance(i.get('playerId'),int)}
    absent=sorted(referenced-{p['playerId'] for p in cards})
    for offset in range(0,len(absent),100):
        try:
            data=client.get_player_card(absent[offset:offset+100],int(status.get('finalScoringPeriod',17)))
            cards.extend({'playerId':p['id'],'name':p.get('player',{}).get('fullName'),'transactions':p.get('transactions',[])} for p in data.get('players',[]))
        except Exception:pass
    result=reconcile_activity(season,names,team_ids,periods,cards,metadata,failed,universe_succeeded)
    # Communication is corroborative only; historical endpoints can be unavailable.
    try:
        topic_count=0;offset=0
        while True:
            topic_filter={'topics':{'filterType':{'value':['ACTIVITY_TRANSACTIONS']},'limit':100,'offset':offset,'limitPerMessageSet':{'value':100},'sortMessageDate':{'sortPriority':1,'sortAsc':False},'filterIncludeMessageTypeIds':{'value':[178,180,179,239,181,244]}}}
            communication=client.league_get(params={'view':'kona_league_communication'},extend='/communication/',headers={'x-fantasy-filter':json.dumps(topic_filter)})
            batch=communication.get('topics',[]);topic_count+=len(batch)
            if len(batch)<100:break
            offset+=100
            if offset>=10000:raise ValueError('Communication page bound exceeded')
        result['coverage']['communicationFeed']={'status':'returned','topicCount':topic_count,'usedForExecutedMovements':False}
    except Exception:
        result['coverage']['communicationFeed']={'status':'unavailable','usedForExecutedMovements':False}
    return result


def generate_activity(client, folder, season, teams, preserve_existing=True):
    from football_exporter import write_json
    names = {}
    for path in (Path(folder)/'lineups').glob('*.json'):
        for roster in json.loads(path.read_text())['teams'].values():
            names.update({p['playerId']:p['name'] for p in roster})
    try:
        data = collect_activity(client, season, names, set(teams))
    except Exception:
        data = {'schemaVersion':1, 'season':season, 'generatedAt':datetime.now(timezone.utc).isoformat(),
                'coverage':{'complete':False, 'status':'unavailable', 'limitation':'ESPN activity retrieval failed; no complete history asserted.'}, 'events':[]}
    path = Path(folder)/'activity.json'
    if preserve_existing and path.exists() and data['coverage']['status'] in ('unavailable','partial'):
        previous = json.loads(path.read_text())
        # Refresh failures never erase previously verified fantasy movements.
        events = {event['id']:event for event in previous['events']}
        events.update({event['id']:event for event in data['events']})
        data['events'] = sorted(events.values(), key=lambda e:(e['timestamp'],e['id']))
        if previous['events'] and data['coverage']['status'] == 'unavailable':
            data['coverage'] = {**previous['coverage'], **data['coverage'], 'status':'stale',
                                'lastSuccessfulSnapshotAt':previous.get('generatedAt')}
        data['coverage']['complete'] = False
        data['coverage']['status'] = 'stale'
        data['coverage']['executedMovementCount'] = len(data['events'])
        data['coverage']['firstTimestamp'] = data['events'][0]['timestamp'] if data['events'] else None
        data['coverage']['lastTimestamp'] = data['events'][-1]['timestamp'] if data['events'] else None
    if client is not None:
        from football_draft import generate_draft
        try:
            draft=generate_draft(client,folder,season,names,set(teams))
            data['coverage']['draft']={**draft['coverage'],'path':'draft.json'}
            from football_activity_audit import draft_activity_audit
            data.setdefault('validation',{})['draftAssignments']=draft_activity_audit(draft,data['events'])
        except Exception:
            data['coverage']['draft']={'complete':False,'status':'refresh_failed'}
    from football_activity_audit import lineup_window_audit
    data.setdefault('validation',{})['lineupWindows']=lineup_window_audit(data['events'],folder)
    if data['coverage']['status']=='stale':
        from football_activity_audit import validate_events,ownership_audit
        data['validation'].update({**validate_events(data['events'],set(teams)),'ownership':ownership_audit(data['events'])})
    if data['validation']['lineupWindows']['anomalies'] or data['validation'].get('draftAssignments',{}).get('matchesAuthoritativeBoard') is False:
        data['coverage'].update({'complete':False,'status':'partial'})
    write_json(path, data)
    return data
