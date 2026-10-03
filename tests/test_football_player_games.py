import unittest
from datetime import datetime,timezone
from football_player_games import normalize_games,game_state,season_stats,COLUMNS

class PlayerGameTests(unittest.TestCase):
 def test_sparse_actual_stats_and_gp(self):
  def stat(w,stats):return {'seasonId':2021,'statSourceId':0,'statSplitTypeId':1,'scoringPeriodId':w,'stats':stats,'proTeamId':4,'externalId':str(w)}
  raw={'players':[{'id':7,'player':{'stats':[stat(1,{'210':1,'42':20,'53':2}),stat(2,{})]}}]}
  rows=normalize_games(raw,2021,{1,2})['players']['7']
  self.assertTrue(rows['1']['played']);self.assertEqual(rows['1']['stats']['recTD'],0);self.assertIsNone(rows['2']['played']);self.assertIsNone(rows['2']['stats']['recTD'])
 def test_states_and_gp_zero_participation(self):
  now=datetime(2026,10,3,tzinfo=timezone.utc);past=now.timestamp()*1000-1000
  schedule=[{'week':w,'kickoff':past,'home':'CIN','away':'BUF'} for w in range(1,12)]
  schedule.append({'week':13,'kickoff':past+10000000,'home':'CIN','away':'NYJ'})
  self.assertEqual(game_state(12,None,'CIN',schedule,True,now),'bye')
  self.assertEqual(game_state(1,{'played':False,'stats':{}},'CIN',schedule,True,now),'did_not_play')
  self.assertEqual(game_state(13,None,'CIN',schedule,False,now),'upcoming')
  self.assertEqual(game_state(1,{'played':True,'stats':{}},'CIN',schedule,True,now),'played')
  rows=[{'status':'final','fantasyStatus':'final','gameState':state,'points':p,'nflStats':{'receptions':rec},'rosters':[{'slot':slot,'points':p}]} for state,p,rec,slot in [('played',0,0,'WR'),('played',20,2,'WR'),('played',30,3,'BE'),('did_not_play',0,None,'IR')]]
  s=season_stats(rows,[('receptions','Rec')]);self.assertEqual(s['gp'],2);self.assertEqual(s['points'],20);self.assertEqual(s['fppg'],10);self.assertEqual(s['nflStats']['receptions'],5)
  rows.append({'status':'final','fantasyStatus':'upcoming','gameState':'played','points':10,'nflStats':{'receptions':1},'rosters':[]})
  self.assertEqual(season_stats(rows,[])['gp'],2);self.assertEqual(season_stats(rows,[])['points'],20)
  rows.append({'status':'final','gameState':'unknown','points':0,'nflStats':{},'rosters':[]})
  uncertain=season_stats(rows,[('receptions','Rec')]);self.assertEqual(uncertain['gp'],2);self.assertEqual(uncertain['fppg'],10);self.assertIsNone(uncertain['nflStats']['receptions'])
 def test_position_specific_columns(self):
  self.assertNotIn('passYards',dict(COLUMNS['RB']));self.assertIn('fgMade',dict(COLUMNS['K']));self.assertIn('sacks',dict(COLUMNS['D/ST']))

 def test_eventlog_fallback_and_cache(self):
  from unittest.mock import patch,Mock
  from tempfile import TemporaryDirectory
  from football_player_games import enrich_participation
  data={'season':2021,'players':{'7':{'1':{'played':None,'eventId':'a','hasActualStats':True,'stats':{'receptions':None}},'2':{'played':None,'eventId':'b','hasActualStats':False,'stats':{'receptions':None}},'3':{'played':None,'eventId':'missing','hasActualStats':False,'stats':{'receptions':None}}}}}
  response=Mock();response.json.return_value={'events':{'items':[{'event':{'$ref':'https://sports.core.api.espn.com/v2/events/a'},'played':True},{'event':{'$ref':'https://sports.core.api.espn.com/v2/events/b'},'played':False}]}}
  with TemporaryDirectory() as cache,patch('requests.get',return_value=response) as get:
   enrich_participation(data,{7},cache)
   self.assertTrue(data['players']['7']['1']['played']);self.assertEqual(data['players']['7']['1']['stats']['receptions'],0)
   self.assertFalse(data['players']['7']['2']['played']);self.assertIsNone(data['players']['7']['2']['stats']['receptions'])
   self.assertIsNone(data['players']['7']['3']['played'])
   enrich_participation(data,{7},cache);self.assertEqual(get.call_count,1)

 def test_empty_actual_record_and_covered_absence(self):
  now=datetime(2026,10,3,tzinfo=timezone.utc)
  schedule=[{'id':'123','week':1,'kickoff':now.timestamp()*1000-86400000,'home':'BUF','away':'NE'}]
  empty={'played':None,'stats':{},'eventId':'123','actualRecord':True,'hasActualStats':False}
  self.assertEqual(game_state(1,empty,'NE',schedule,True,now),'did_not_play')
  self.assertEqual(game_state(1,None,'NE',schedule,True,now,source_covered=True),'did_not_play')
  self.assertEqual(game_state(1,None,'NE',schedule,True,now),'unknown')
  schedule[0]['canceled']=True
  self.assertEqual(game_state(1,None,'BUF',schedule,True,now,defense=True),'did_not_play')

 def test_full_nfl_schedule_independent_of_fantasy_weeks(self):
  from football_player_games import normalize_nfl_schedule
  raw={'settings':{'proTeams':[{'proGamesByScoringPeriod':{'18':[{'id':123,'date':1,'homeProTeamId':2,'awayProTeamId':4,'statsOfficial':True}]}}]}}
  data={'weeks':list(range(1,19)),'players':{}}
  games=normalize_nfl_schedule(raw,data)
  self.assertEqual(games[0]['week'],18);self.assertTrue(games[0]['completionUnknown'])
