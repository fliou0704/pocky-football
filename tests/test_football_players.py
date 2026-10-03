import json
import unittest
from pathlib import Path
from football_players import ROOT, summary, PROFILE_FIELDS, player_transaction_type
from football_record_book import STARTERS, numeric

class FootballPlayersTests(unittest.TestCase):
    def test_missing_zero_live_and_bench(self):
        def row(week,points,status='final',slot='BE'):
            return {'season':2026,'week':week,'points':points,'status':status,'rosters':[{'slot':slot,'points':points}]}
        s=summary([row(1,None),row(2,0),row(3,12,slot='WR'),row(4,20,'live','WR')])
        self.assertEqual(s,{'weeks':2,'points':12,'average':6,'high':{'season':2026,'week':3,'points':12},'starts':1,'starterPoints':12})
        self.assertIsNone(summary([])['points'])

    def test_bundled_drop_direction_is_per_player(self):
        self.assertEqual(player_transaction_type('waiver_add',{1},set()),'drop')
        self.assertEqual(player_transaction_type('free_agent_add',{1},set()),'drop')
        self.assertEqual(player_transaction_type('waiver_add',set(),{1}),'waiver_add')
        self.assertEqual(player_transaction_type('free_agent_add',set(),{1}),'free_agent_add')
        self.assertEqual(player_transaction_type('trade',{1},{2}),'trade')

    def test_generated_contracts_against_audited_sources(self):
        folder=ROOT/'frontend/public/data/pocky-football'
        index=json.loads((folder/'players-index.json').read_text());seen=set()
        sources={}
        for year in sorted({year for entry in index['players'] for year in entry['seasons']}):
            season=folder/str(year)
            sources[year]={name:json.loads((season/f'{name}.json').read_text()) for name in ('draft','activity','teams','player-scoring')}
            sources[year]['scores']={p['playerId']:p for p in sources[year]['player-scoring']['players']}
            sources[year]['lineups']={int(p.stem):json.loads(p.read_text()) for p in (season/'lineups').glob('*.json')}
        for entry in index['players']:
            pid=entry['espnId'];self.assertNotIn(pid,seen);seen.add(pid)
            data=json.loads((ROOT/'frontend/public/data'/entry['path']).read_text())
            self.assertEqual(data['profile']['espnId'],pid);self.assertLessEqual(set(data['profile']),set(PROFILE_FIELDS))
            self.assertEqual(entry['seasons'],[s['season'] for s in data['seasons']])
            if pid<0:self.assertNotIn('birthDate',data['profile']);self.assertNotIn('headshot',data['profile'])
            for season in data['seasons']:
                self.assertEqual([w['week'] for w in season['weeks']],list(range(1,19)))
                starts=[r for w in season['weeks'] if w['fantasyStatus']=='final' for r in w['rosters'] if r['slot'] in STARTERS]
                self.assertEqual(season['seasonStats']['gp'],len(starts))
                if all(numeric(r['points']) for r in starts):
                    total=round(sum(r['points'] for r in starts),2)
                    self.assertEqual(season['seasonStats']['points'],total)
                    self.assertEqual(season['seasonStats']['fppg'],round(total/len(starts),2) if starts else None)
                for t in season['transactions']:
                    if t['type']=='drop':self.assertTrue(t['fromTeams']);self.assertFalse(t['toTeams'])
                    if t['type'] in ('waiver_add','free_agent_add'):self.assertTrue(t['toTeams']);self.assertFalse(t['fromTeams'])
                    if t['type']=='trade':self.assertTrue(t['fromTeams']);self.assertTrue(t['toTeams'])
                source=sources[season['season']]
                expected=[p for p in source['draft']['picks'] if p['playerId']==pid]
                self.assertEqual(len(season['draft']),len(expected))
                for row,pick in zip(season['draft'],expected):
                    for field in ('round','pickInRound','overallPick'):self.assertEqual(row[field],pick[field])
                    self.assertEqual(row['team']['teamId'],pick['teamId'])
                self.assertEqual(season['summary'],summary(season['weeks']))
                events=[e for e in source['activity']['events'] if e['type']!='draft' and e['status']=='executed'
                        and any(p['playerId']==pid for t in e['teams'] for field in ('playersAdded','playersDropped') for p in t[field])]
                self.assertEqual(len(season['transactions']),len(events))
                for week in season['weeks']:
                    score=source['scores'].get(pid,{}).get('pointsByWeek',{}).get(str(week['week']))
                    if numeric(score):self.assertEqual(week['points'],score)
                    for row in week['rosters']:
                        actual=next(p for p in source['lineups'][week['week']]['teams'][str(row['team']['teamId'])] if p['playerId']==pid)
                        self.assertEqual(row['points'],actual['points']);self.assertEqual(row['slot'],actual['slot'])
                for owner in season['ownership']:
                    for week in owner['weeks']:
                        self.assertTrue(any(p['playerId']==pid for p in source['lineups'][week]['teams'][str(owner['team']['teamId'])]))
        self.assertEqual(seen,{p['espnId'] for p in json.loads((folder/'players.json').read_text())['players']})

if __name__=='__main__':unittest.main()
