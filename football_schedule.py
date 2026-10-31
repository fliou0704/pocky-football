"""Clock-injected game-window decisions; private state, no fantasy requests."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from football_http import get_json

UTC = timezone.utc
INTERVAL = timedelta(minutes=15)


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Schedule timestamps must include timezone')
    return result.astimezone(UTC)


def normalize(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('events'), list) or not raw.get('leagues'):
        raise ValueError('Incomplete NFL calendar')
    events, seen = [], set()
    for event in raw['events']:
        eid = str(event['id'])
        if eid in seen:
            raise ValueError('Duplicate NFL event')
        seen.add(eid)
        status = event['status']['type']
        events.append({'id':eid, 'kickoff':instant(event['date']).isoformat(),
                       'state':status['state'], 'name':status['name'], 'completed':status['completed'] is True})
    return events


def decide(events, state=None, now=None):
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError('Clock must be timezone aware')
    state = json.loads(json.dumps(state or {}))
    finals = state.setdefault('finalSeenAt', {})
    postgame = state.setdefault('postgameEligible', {})
    active, phases, completed, attention = [], [], [], []
    for event in events:
        kickoff = instant(event['kickoff'])
        name = event['name']
        eid = event['id']
        if kickoff < now-timedelta(days=2):
            continue
        if event['completed'] or name == 'STATUS_CANCELED':
            if eid not in finals:
                finals[eid] = now.isoformat()
                postgame[eid] = kickoff >= now-timedelta(hours=12) or any(e['id'] == eid and not e['completed'] for e in state.get('events', []))
            completed.append(eid)
            if postgame.get(eid, False) and now <= instant(finals[eid])+timedelta(hours=1):
                active.append(event); phases.append('postgame')
        elif name == 'STATUS_POSTPONED':
            # Retain discovery of its new date; don't poll fantasy all night for a postponement.
            finals.pop(eid, None)
        elif event['state'] == 'in' or name in ('STATUS_DELAYED', 'STATUS_SUSPENDED'):
            finals.pop(eid, None)
            if now-kickoff > timedelta(hours=24):
                attention.append(eid)
            else:
                active.append(event); phases.append('live-or-delayed')
        elif kickoff-timedelta(hours=1) <= now <= kickoff+timedelta(hours=24):
            # A late status feed is not evidence the game ended. Keep checking, with a cap/alert.
            finals.pop(eid, None)
            active.append(event); phases.append('pregame' if now < kickoff else 'awaiting-status')
        elif now-kickoff > timedelta(hours=24):
            attention.append(eid)
    last = instant(state['lastSuccessfulAt']) if state.get('lastSuccessfulAt') else None
    due = last is None or int(now.timestamp())//900 > int(last.timestamp())//900
    new_finals = set(completed)-set(state.get('reconciledIds', []))
    mode = 'live' if active else 'full' if new_finals and not attention else 'skip'
    if mode == 'full' and state.get('lastFullAt'):
        # A regular baseline full refresh after the observed finals already reconciled them.
        if all(instant(finals[eid]) <= instant(state['lastFullAt']) for eid in new_finals):
            mode = 'skip'
    days = {}
    for event in events:
        day = instant(event['kickoff']).date().isoformat()
        days.setdefault(day, []).append(event['kickoff'])
    decision = {'due':bool(due and mode != 'skip'), 'mode':mode if due else 'skip',
                'reason':','.join(sorted(set(phases))) if active else 'reconciliation' if new_finals else 'no-game-window',
                'checkedAt':now.isoformat(), 'completedIds':sorted(completed), 'needsAttention':attention,
                'days':{day:{'firstKickoff':min(times),'lastKickoff':max(times)} for day,times in days.items()}}
    state['events'] = events
    state['lastScheduleCheckAt'] = now.isoformat()
    return decision, state


def plan(path, enabled=False, dry_run=False, now=None, fetch=get_json, metrics=None):
    now = now or datetime.now(UTC)
    path = Path(path)
    if not enabled and not dry_run:
        return {'due':False, 'mode':'skip', 'reason':'pilot-disabled'}
    state = json.loads(path.read_text()) if path.exists() else {}
    try:
        by_id = {}
        # The NFL endpoint rejects multi-day ranges. Three supported single-date reads
        # cover UTC midnight, long games, and the next pregame window without guessing dates.
        for offset in (-1, 0, 1):
            raw = fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard',
                        params={'dates':(now+timedelta(days=offset)).strftime('%Y%m%d')}, metrics=metrics)
            for event in normalize(raw):
                if event['id'] in by_id and event != by_id[event['id']]:
                    raise ValueError('Inconsistent schedule responses')
                by_id[event['id']] = event
        # Retain previously observed live/delayed games even if they disappear from a date
        # bucket; their absence is not proof of completion. Surface a bounded attention state.
        for event in state.get('events', []):
            if event['id'] not in by_id and not event['completed'] and (event['state'] == 'in' or event['name'] in ('STATUS_DELAYED','STATUS_SUSPENDED')):
                by_id[event['id']] = event
        events = list(by_id.values())
    except Exception:
        # A stale calendar can cause needless fantasy traffic; don't activate new work from it.
        return {'due':False,'mode':'skip','reason':'schedule-unavailable; last-good retained','needsAttention':['calendar']}
    decision, updated = decide(events, state, now)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(updated, sort_keys=True))
        temp.replace(path)
    return decision


def complete(path, mode, now=None):
    path = Path(path)
    state = json.loads(path.read_text()) if path.exists() else {}
    now = now or datetime.now(UTC)
    state['lastSuccessfulAt'] = now.isoformat()
    if mode == 'full':
        state['lastFullAt'] = now.isoformat()
        state['reconciledIds'] = sorted(state.get('finalSeenAt', {}))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, sort_keys=True))
