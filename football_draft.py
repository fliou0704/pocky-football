"""Authoritative ESPN draft boards, independent of activity timestamps."""
from collections import Counter
from datetime import datetime, timezone


def valid_id(value):
    # ESPN uses negative player IDs for NFL defenses; fantasy team IDs are positive.
    return isinstance(value, int) and not isinstance(value, bool) and value != 0


def iso_date(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat() if value else None


def draft_issues(data, team_ids):
    picks = data['picks']; n = len(team_ids); issues = []
    overall = [p['overallPick'] for p in picks]
    players = [p['playerId'] for p in picks]
    if len(overall) != len(set(overall)): issues.append('duplicate_overall_pick')
    if len(players) != len(set(players)): issues.append('duplicate_drafted_player')
    if any(not valid_id(p['playerId']) or p['teamId'] not in team_ids for p in picks): issues.append('invalid_team_or_player')
    if any(not isinstance(p['round'], int) or not isinstance(p['pickInRound'], int)
           or p['round'] < 1 or not 1 <= p['pickInRound'] <= n
           or p['overallPick'] != (p['round'] - 1) * n + p['pickInRound'] for p in picks):
        issues.append('invalid_round_pick_relationship')
    expected = data['coverage']['expectedSelections']
    if len(picks) != expected: issues.append('selection_count_mismatch')
    if any(not valid_id(v) for v in overall) or sorted(overall) != list(range(1, expected + 1)): issues.append('noncontiguous_overall_picks')
    counts = Counter(p['teamId'] for p in picks)
    if any(counts[t] != data['coverage']['expectedRounds'] for t in team_ids): issues.append('team_selection_count_mismatch')
    order = data['draftOrder']
    if len(order) != n or {t['teamId'] for t in order} != set(team_ids): issues.append('invalid_draft_order')
    if data['type'] == 'snake' and order:
        team_order = [t['teamId'] for t in order]
        if any(p['teamId'] != (team_order if p['round'] % 2 else list(reversed(team_order)))[p['pickInRound']-1]
               for p in picks if isinstance(p['round'],int) and isinstance(p['pickInRound'],int) and 1 <= p['pickInRound'] <= n and len(team_order)==n):
            issues.append('snake_order_mismatch')
    return issues


def normalize_draft(raw, season, names, team_ids):
    from espn_api.football.constant import POSITION_MAP
    detail = raw.get('draftDetail', {}); settings = raw['settings']['draftSettings']
    slots = raw['settings']['rosterSettings']['lineupSlotCounts']
    rounds = sum(int(count) for slot,count in slots.items() if int(slot) not in (21,24))
    order = settings.get('pickOrder', [])
    draft_type = str(settings['type']).lower()
    selections = []
    for pick in detail.get('picks', []):
        team_id = pick.get('teamId')
        selections.append({'overallPick':pick.get('overallPickNumber'), 'round':pick.get('roundId'),
                           'pickInRound':pick.get('roundPickNumber'), 'teamId':team_id,
                           'draftSlot':order.index(team_id)+1 if team_id in order else None,
                           'playerId':pick.get('playerId'), 'playerName':names.get(pick.get('playerId')),
                           'keeper':pick.get('keeper'), 'reservedForKeeper':pick.get('reservedForKeeper'),
                           'auctionPrice':pick.get('bidAmount') if draft_type == 'auction' else None,
                           'nominatingTeamId':pick.get('nominatingTeamId') if draft_type == 'auction' else None,
                           'initialSlot':POSITION_MAP.get(pick.get('lineupSlotId')),
                           'autoDraftTypeId':pick.get('autoDraftTypeId')})
    selections.sort(key=lambda p:p['overallPick'] if isinstance(p['overallPick'],int) else 0)
    data = {'schemaVersion':1, 'season':season, 'source':'mDraftDetail', 'type':draft_type,
            'startedAt':iso_date(settings.get('date')), 'completedAt':iso_date(detail.get('completeDate')),
            'keeperCount':settings.get('keeperCount'), 'draftPickTradingEnabled':settings.get('isTradingEnabled'),
            'draftOrder':[{'teamId':team,'draftSlot':i+1} for i,team in enumerate(order)],
            'coverage':{'sourceDrafted':bool(detail.get('drafted')), 'sourceInProgress':bool(detail.get('inProgress')),
                        'teamCount':len(team_ids), 'expectedRounds':rounds, 'expectedSelections':len(team_ids)*rounds,
                        'observedSelections':len(selections), 'authoritativeOrder':True,
                        'roundsSource':'rosterSettings.lineupSlotCounts excluding IR/ER',
                        'draftSlotSource':'settings.draftSettings.pickOrder'}, 'picks':selections}
    issues = draft_issues(data, team_ids)
    data['coverage'].update({'issues':issues, 'missingPlayerNames':sum(p['playerName'] is None for p in selections),
                             'complete':bool(detail.get('drafted')) and not detail.get('inProgress') and not issues})
    return data


def generate_draft(client, folder, season, names, team_ids):
    from football_exporter import write_json
    from pathlib import Path
    raw = client.league_get(params={'view':['mDraftDetail','mSettings']})
    data = normalize_draft(raw, season, names, team_ids)
    import json
    scoring=Path(folder)/'player-scoring.json'
    if scoring.exists():
        source=json.loads(scoring.read_text())
        positions={int(k):v for k,v in source.get('playerPositions',{}).items()} or {p['playerId']:p['position'] for p in source['players']}
        for pick in data['picks']:pick['position']=positions.get(pick['playerId'])
    write_json(Path(folder)/'draft.json',data)
    return data
