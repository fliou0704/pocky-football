import copy
import json
import tempfile
import unittest
from pathlib import Path
from football_player_metadata import build, index, universe, validate, ROOT


class PlayerMetadataTests(unittest.TestCase):
    def setUp(self):
        self.known={7:{'name':'Example','position':'WR','seasons':{2021,2026},'observedIn':{'2021/draft.json'}},
                    -16001:{'name':'Falcons D/ST','position':'D/ST','nflTeam':'ATL','seasons':{2021},'observedIn':set()}}
        self.row={'espn_id':'7','gsis_id':'00-0000007','height':'72','weight':'201','birth_date':'2000-03-01',
                  'draft_year':'2021','draft_round':'1','draft_pick':'5','draft_team':'ATL','headshot':'https://example.com/photo.png'}

    def test_deterministic_join_and_defense(self):
        a,_=build(self.known,[self.row,self.row]);b,_=build(dict(reversed(list(self.known.items()))),[self.row])
        self.assertEqual(a,b)
        self.assertEqual(a[1]['match']['method'],'nflverse_espn_id')
        self.assertNotIn('headshot',a[0]);self.assertNotIn('nflDraft',a[0])

    def test_collision_unresolved_no_name_match(self):
        other=dict(self.row,gsis_id='00-0000008')
        p,a=build(self.known,[self.row,other])
        self.assertEqual(p[1]['match']['method'],'espn_only')
        self.assertIsNone(p[1]['heightInches']);self.assertEqual(a['nflverseIdCollisions'],[7])
        self.assertEqual(index([self.row,other],'espn_id'),index([other,self.row],'espn_id'))

    def test_headshot_chain(self):
        p,_=build(self.known,[self.row],image_check=lambda u:'invalid' if 'example' in u else 'valid')
        self.assertEqual(p[1]['fieldSources']['headshot'],'espn')
        p,_=build(self.known,[self.row],image_check=lambda u:'unverified')
        self.assertIsNone(p[1]['headshot'])

    def test_sleeper_id_fallback_and_height(self):
        p,a=build(self.known,[],[{'espn_id':'7','height':'6-0','weight':'201'}])
        self.assertEqual(p[1]['heightInches'],72);self.assertEqual(a['sleeperFallbackMatches'],1)

    def test_validation_rejects_bad_values_and_duplicates(self):
        players,_=build(self.known,[self.row])
        for field,value in [('heightInches',300),('weightPounds',-1),('headshot','javascript:bad')]:
            bad=copy.deepcopy(players);bad[1][field]=value
            with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(players);bad[1]['nflDraft']['round']=99
        with self.assertRaises(ValueError):validate(bad)
        with self.assertRaises(ValueError):validate(players+players)
        bad=copy.deepcopy(players);bad[0]['birthDate']='2000-01-01'
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(players);bad.append(dict(bad[1],espnId=8))
        with self.assertRaises(ValueError):validate(bad)

    def test_universe_includes_only_league_appearances(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);season=folder/'2021';season.mkdir()
            for f in ('teams','draft','activity'):
                (season/f'{f}.json').write_text(json.dumps({'players':[{'playerId':7,'name':'Example'}]}))
            (season/'player-scoring.json').write_text(json.dumps({'players':[{'playerId':999,'name':'Unrostered'}]}))
            known,_,_=universe(folder,2021,2021)
            self.assertEqual(set(known),{7})

    def test_generated_contract_coverage_and_public_allowlist(self):
        folder=ROOT/'frontend/public/data/pocky-football'
        data=json.loads((folder/'players.json').read_text());known,_,malformed=universe(folder)
        self.assertEqual(set(known),{p['espnId'] for p in data['players']});self.assertFalse(malformed)
        validate(data['players'])
        allowed={'espnId','entityType','name','seasons','observedIn','position','nflTeam','logo','match','positionGroup',
                 'heightInches','weightPounds','birthDate','college','jerseyNumber','rookieSeason','lastSeason','ids',
                 'nflDraft','headshot','headshotValidation','fieldSources'}
        for p in data['players']:self.assertLessEqual(set(p),allowed)
        text=json.dumps(data).lower()
        for forbidden in ('espn_s2','swid','memberid','ownerid','cookie','authorization','"age":'):
            self.assertNotIn(forbidden,text)


if __name__=='__main__':unittest.main()
