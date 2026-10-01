"""Minimal executed fantasy roster movements from ESPN's period and playercard views.

Coverage is explicitly bounded: no source offers a verified league-wide total count.
Pending/rejected activity and account metadata never enter the public contract.
"""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


def normalize_transaction(raw, season, names, team_ids, uses_faab=False):
    # ESPN archived executed trades retain isPending=True; status is authoritative.
    if raw.get('status') != 'EXECUTED':
        return None
    movements = defaultdict(lambda: {'playersAdded': [], 'playersDropped': []})
    kinds = set()
    for item in raw.get('items', []):
        kind, player_id = item.get('type'), item.get('playerId')
        if kind not in ('ADD', 'DROP', 'TRADE', 'DRAFT') or not isinstance(player_id, int):
            continue
        kinds.add(kind)
        player = {'playerId': player_id, 'name': names.get(player_id)}
        origin, destination = item.get('fromTeamId'), item.get('toTeamId')
        if kind in ('DROP', 'TRADE') and origin in team_ids:
            movements[origin]['playersDropped'].append(player)
        if kind in ('ADD', 'TRADE', 'DRAFT') and destination in team_ids:
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
    if not isinstance(timestamp, (float, int)) or not math.isfinite(timestamp):
        return None
    bid = raw.get('bidAmount')
    faab = bid if uses_faab and kind == 'waiver_add' and isinstance(bid, (int, float)) and math.isfinite(bid) else None
    return {'id': 'event-' + hashlib.sha256(str(raw['id']).encode()).hexdigest()[:20],
            'season': season, 'timestamp': datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat(),
            'timestampKind': 'processed' if raw.get('processDate') else 'proposed',
            'type': kind, 'week': raw.get('scoringPeriodId'), 'status': 'executed',
            'teams': [{'teamId': team, **{key: sorted({p['playerId']:p for p in rows}.values(), key=lambda p:p['playerId'])
                                        for key,rows in changes.items()}}
                      for team,changes in sorted(movements.items())],
            'faab': faab, 'waiverType': raw.get('executionType') if kind == 'waiver_add' else None}


def movements_for_team(activity, team_id):
    """Reusable chronological acquisition/drop/trade evidence, not inferred membership."""
    return [{key: event[key] for key in ('id', 'season', 'timestamp', 'type', 'week')}
            | changes for event in activity['events'] for changes in event['teams']
            if changes['teamId'] == team_id]


def collect_activity(client, season, names, team_ids):
    """Explicit period queries fix empty completed-season mTransactions2 responses."""
    metadata = client.league_get(params={'view': ['mStatus', 'mSettings']})
    status = metadata['status']
    through = max(int(status.get('latestScoringPeriod', 0)), int(status.get('transactionScoringPeriod', 0)))
    uses_faab = metadata['settings']['acquisitionSettings'].get('isUsingAcquisitionBudget', False)
    transactions = {}; failed = []; succeeded = []; missing_cards = 0; returned_ids = set()
    for period in range(through + 1):
        try:
            data = client.league_get(params={'view':'mTransactions2', 'scoringPeriodId':period})
            if not isinstance(data, dict) or 'status' not in data:
                raise ValueError('Missing activity response')
            succeeded.append(period)
            for t in data.get('transactions', []):
                transactions[t['id']] = t
        except Exception:
            failed.append(period)
    # Draft/add/drop items seed player IDs beyond the weekly roster snapshots.
    requested_ids = set(names) | {item['playerId'] for t in transactions.values() for item in t.get('items', [])
                                  if isinstance(item.get('playerId'), int)}
    ids = sorted(requested_ids)
    for offset in range(0, len(ids), 100):
        batch = ids[offset:offset+100]
        try:
            data = client.get_player_card(batch, int(status.get('finalScoringPeriod', 17)))
            for player in data.get('players', []):
                returned_ids.add(player['id']); names[player['id']] = player.get('player', {}).get('fullName') or names.get(player['id'])
                for t in player.get('transactions', []):
                    # Playercards include executed trade transfers absent from the period feed.
                    previous = transactions.get(t['id'])
                    if previous is None or t.get('status') == 'EXECUTED' and t.get('items'):
                        transactions[t['id']] = t
        except Exception:
            missing_cards += len(batch)
    events = [event for t in transactions.values()
              if (event := normalize_transaction(t, season, names, team_ids, uses_faab)) is not None]
    events.sort(key=lambda event:(event['timestamp'],event['id']))
    return {'schemaVersion':1, 'season':season, 'generatedAt':datetime.now(timezone.utc).isoformat(),
            'coverage': {'complete':False, 'status':'partial' if events else 'unavailable',
                         'sources':['mTransactions2', 'kona_playercard'], 'queriedThroughPeriod':through,
                         'successfulPeriods':succeeded, 'failedPeriods':failed,
                         'requestedPlayerCount':len(requested_ids), 'returnedPlayerCount':len(returned_ids),
                         'missingPlayerCount':len(requested_ids-returned_ids), 'failedCardPlayerCount':missing_cards,
                         'unknownPlayerNames':sum(p['name'] is None for e in events for t in e['teams'] for key in ('playersAdded', 'playersDropped') for p in t[key]),
                         'sourceEventCount':len(transactions), 'executedMovementCount':len(events),
                         'firstTimestamp':events[0]['timestamp'] if events else None,
                         'lastTimestamp':events[-1]['timestamp'] if events else None,
                         'usesFaab':bool(uses_faab),
                         'limitation':'Explicit scoring-period sweep plus known-player card histories; ESPN supplies no verified total count. Unobserved player-only events, missing trade details and archived omissions remain possible. Transaction records are deferred.'},
            'events':events}


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
    if preserve_existing and path.exists():
        previous = json.loads(path.read_text())
        # Refresh failures never erase previously verified fantasy movements.
        events = {event['id']:event for event in previous['events']}
        events.update({event['id']:event for event in data['events']})
        data['events'] = sorted(events.values(), key=lambda e:(e['timestamp'],e['id']))
        if previous['events'] and data['coverage']['status'] == 'unavailable':
            data['coverage'] = {**previous['coverage'], **data['coverage'], 'status':'stale',
                                'lastSuccessfulSnapshotAt':previous.get('generatedAt')}
        data['coverage']['executedMovementCount'] = len(data['events'])
        data['coverage']['firstTimestamp'] = data['events'][0]['timestamp'] if data['events'] else None
        data['coverage']['lastTimestamp'] = data['events'][-1]['timestamp'] if data['events'] else None
    write_json(path, data)
    return data
