"""Small offline live fixtures plus the actual committed full release contracts."""
import copy
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout

import requests
import data_refresh as pipeline
import football_live as live
from football_http import instrument, get_json


def source(league_id, season=2026, week=2):
    def side(tid, points):
        return {'teamId':tid, 'totalPointsLive':points, 'adjustment':0,
                'rosterForCurrentScoringPeriod':{'entries':[
                    {'playerId':100+tid, 'lineupSlotId':0, 'playerPoolEntry':{'appliedStatTotal':points,
                      'player':{'id':100+tid, 'fullName':'Player '+str(tid), 'defaultPositionId':1, 'proTeamId':1,
                                'injuryStatus':'ACTIVE'}}},
                    {'playerId':200+tid, 'lineupSlotId':20, 'playerPoolEntry':{'appliedStatTotal':None,
                      'player':{'id':200+tid, 'fullName':'Bench '+str(tid), 'defaultPositionId':2, 'proTeamId':1}}}]}}
    return {'id':league_id, 'seasonId':season, 'scoringPeriodId':week,
            'status':{'currentMatchupPeriod':week},
            'schedule':[{'matchupPeriodId':week, 'home':side(1,7.25), 'away':side(2,-1.2), 'winner':'UNDECIDED'}]}


class LiveTests(unittest.TestCase):
    def setUp(self):
        import test_data_refresh as fixtures
        self.fixture = fixtures.ReleaseTests('test_unchanged_refresh_retains_exact_persisted_files')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        pipeline.refresh(self.root, self.fixture.generate)
        self.raw = source(pipeline.read_config(pipeline.SLUG)['leagueId'])
        self.fetch = Mock(return_value=self.raw)
        self.env = patch.dict(os.environ, {'ESPN_S2':'private-test-cookie','SWID':'private-test-owner'})
        self.env.start(); self.addCleanup(self.env.stop)

    def run_live(self):
        original = live.collect
        with patch('football_live.collect', side_effect=lambda root, slug, metrics: original(root, slug, metrics, self.fetch)):
            return pipeline.refresh(self.root, mode='live')

    def test_one_current_request_and_only_overlay_metadata_change(self):
        before = pipeline.hashes(self.root)
        base = pipeline.read(self.root/pipeline.SLUG/'refresh.json')['generationId']
        self.assertTrue(self.run_live())
        self.fetch.assert_called_once()
        args = self.fetch.call_args
        self.assertIn('/seasons/2026/', args.args[0])
        self.assertEqual(args.kwargs['params']['scoringPeriodId'], 2)
        after = pipeline.hashes(self.root)
        self.assertEqual(before, {k:v for k,v in after.items() if k != pipeline.SLUG+'/live.json'})
        meta = pipeline.read(self.root/pipeline.SLUG/'refresh.json')
        self.assertEqual(meta['baseGenerationId'], base)
        pipeline.validate(self.root, require_metadata=True)

    def test_unchanged_no_publish_and_full_reconciliation(self):
        self.run_live()
        before = {str(p):p.read_bytes() for p in self.root.rglob('*.json')}
        self.assertFalse(self.run_live())
        self.assertEqual(before, {str(p):p.read_bytes() for p in self.root.rglob('*.json')})
        self.assertTrue(pipeline.refresh(self.root, self.fixture.generate))
        self.assertFalse((self.root/pipeline.SLUG/'live.json').exists())
        pipeline.validate(self.root, require_metadata=True)

    def test_partial_response_wrong_total_duplicate_and_missing_starter_preserve_release(self):
        before = pipeline.hashes(self.root)
        variations = []
        raw = copy.deepcopy(self.raw); raw['schedule']=[]; variations.append(raw)
        raw = copy.deepcopy(self.raw); raw['schedule'][0]['home']['totalPointsLive']=10; variations.append(raw)
        raw = copy.deepcopy(self.raw); raw['schedule']*=2; variations.append(raw)
        raw = copy.deepcopy(self.raw); raw['schedule'][0]['home']['rosterForCurrentScoringPeriod']['entries'][0]['playerPoolEntry']['appliedStatTotal']=None; variations.append(raw)
        for raw in variations:
            self.fetch.return_value=raw
            with self.subTest(raw=variations.index(raw)), self.assertRaises(ValueError): self.run_live()
            self.assertEqual(before, pipeline.hashes(self.root))

    def test_failed_request_and_changed_period_preserve(self):
        before = pipeline.hashes(self.root)
        self.fetch.side_effect = requests.Timeout()
        with self.assertRaises(requests.Timeout): self.run_live()
        self.fetch.side_effect = None
        self.raw['status']['currentMatchupPeriod']=3
        with self.assertRaises(live.ReconciliationRequired): self.run_live()
        self.assertEqual(before, pipeline.hashes(self.root))

    def test_base_source_corruption_and_digest_rejected(self):
        self.run_live()
        path = self.root/pipeline.SLUG/'live.json'
        data=pipeline.read(path); data['baseGenerationId']='wrong'; pipeline.write_json(path,data)
        with self.assertRaisesRegex(ValueError,'digest'): pipeline.validate(self.root)

    def test_local_concurrent_refresh_rejected(self):
        with pipeline.refresh_lock(self.root):
            with self.assertRaisesRegex(ValueError,'Another refresh'): self.run_live()

    def test_duplicate_player_between_teams_rejected_and_metadata_preserved(self):
        self.run_live()
        previous=pipeline.read(self.root/pipeline.SLUG/'live.json')
        previous['lineups']['teams']['1'][1]['points']=3.5
        # Missing bench score and injury metadata retain prior evidence; active scores remain strict.
        p=self.root/pipeline.SLUG/'2026'
        result=live.normalize(self.raw,*[pipeline.read(p/(n+'.json')) for n in ('league','home','teams')],previous)
        self.assertEqual(result['lineups']['teams']['1'][1]['points'],3.5)
        entry=self.raw['schedule'][0]['away']['rosterForCurrentScoringPeriod']['entries'][0]
        entry['playerId']=101;entry['playerPoolEntry']['player']['id']=101
        with self.assertRaises(ValueError):live.normalize(self.raw,*[pipeline.read(p/(n+'.json')) for n in ('league','home','teams')])

    def test_committed_team_identity_and_historical_layout(self):
        p=pipeline.PUBLIC_DATA/pipeline.SLUG/'2026'
        league,home,teams=[pipeline.read(p/(n+'.json')) for n in ('league','home','teams')]
        from espn_api.football.constant import POSITION_MAP
        slots={v:k for k,v in POSITION_MAP.items()}
        raw={'id':league['league']['id'],'seasonId':2026,'scoringPeriodId':home['state']['currentWeek'],
             'status':{'currentMatchupPeriod':home['state']['currentWeek']},'schedule':[]}
        positions={'QB':1,'RB':2,'WR':3,'TE':4,'K':5,'D/ST':16}
        for match in teams['matchups']:
            if match['week']!=home['state']['currentWeek']:continue
            item={'matchupPeriodId':match['week'],'winner':'UNDECIDED'}
            for side in ('home','away'):
                tid=match[side+'TeamId'];roster=teams['teams'][str(tid)]['roster']
                item[side]={'teamId':tid,'totalPointsLive':0,'rosterForCurrentScoringPeriod':{'entries':[
                    {'playerId':p['playerId'],'lineupSlotId':slots[p['slot']], 'playerPoolEntry':{'appliedStatTotal':0,
                     'player':{'id':p['playerId'],'fullName':p['name'],'defaultPositionId':positions[p['position']]}}} for p in roster]}}
            raw['schedule'].append(item)
        result=live.normalize(raw,league,home,teams)
        self.assertEqual(set(result['lineups']['teams']),set(teams['teams']))
        self.assertEqual(len(result['matchups']),5)


class HttpTests(unittest.TestCase):
    def test_instrumentation_is_redacted_and_counts_response_bytes(self):
        response=requests.Response(); response.status_code=200; response._content=b'{}'; response._content_consumed=True
        response.headers={'Content-Length':'2','X-Cache':'HIT'}
        output=io.StringIO()
        with patch.object(requests.Session,'send',return_value=response), redirect_stdout(output):
            with instrument('test') as metrics:
                requests.get('https://lm-api-reads.fantasy.espn.com/a?view=mScoreboard&token=PRIVATE',cookies={'espn_s2':'SECRET'})
            result=metrics.summary()
        self.assertEqual(result['totalRequests'],1)
        row=result['categories']['fantasy:mScoreboard']
        self.assertEqual((row['decodedBytes'],row['cacheHits']),(2,1))
        self.assertNotIn('SECRET',output.getvalue()); self.assertNotIn('PRIVATE',output.getvalue())

    def test_bounded_retries_no_auth_or_rate_limit_retries(self):
        with patch('requests.get',side_effect=requests.Timeout()), patch('football_http.time.sleep'):
            with self.assertRaises(ValueError): get_json('https://site.api.espn.com/a')
        for status in (401,403,429):
            with patch('requests.get',return_value=Mock(status_code=status)) as get:
                with self.assertRaises(ValueError): get_json('https://site.api.espn.com/a')
                self.assertEqual(get.call_count,1)

    def test_transient_retry_conditional_and_failure_count(self):
        responses=[]
        for status in (503,200,304):
            response=requests.Response(); response.status_code=status; response._content=b'{}'; response._content_consumed=True
            responses.append(response)
        with patch.object(requests.Session,'send',side_effect=responses), patch('football_http.time.sleep'), redirect_stdout(io.StringIO()):
            with instrument('test') as metrics:
                get_json('https://site.api.espn.com/scoreboard',metrics=metrics)
                requests.get('https://site.api.espn.com/scoreboard')
        row=metrics.summary()['categories']['nfl:scoreboard']
        self.assertEqual((row['requests'],row['failed'],row['retries'],row['conditional']),(3,1,1,1))


if __name__ == '__main__': unittest.main()
