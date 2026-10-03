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
  rows=[{'status':'final','gameState':state,'points':p,'nflStats':{'receptions':rec}} for state,p,rec in [('played',0,0),('played',20,2),('bye',0,None),('did_not_play',0,None)]]
  s=season_stats(rows,[('receptions','Rec')]);self.assertEqual(s['gp'],2);self.assertEqual(s['points'],20);self.assertEqual(s['fppg'],10);self.assertEqual(s['nflStats']['receptions'],2)
  rows.append({'status':'final','gameState':'unknown','points':0,'nflStats':{}})
  uncertain=season_stats(rows,[])
  self.assertIsNone(uncertain['gp']);self.assertIsNone(uncertain['fppg']);self.assertEqual(uncertain['points'],20)
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
