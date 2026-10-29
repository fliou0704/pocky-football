import itertools
import json
import unittest
from pathlib import Path
from football_team_of_week import optimize, weekly_pool, completed, SLOTS, build_team_of_week, season_team_of_week


def player(i, position, points):
    return dict(playerId=i, name=f'Player {i}', position=position, points=points)


class TeamOfWeekTests(unittest.TestCase):
    def pool(self):
        return [player(i, p, i) for i, p in enumerate(['QB','RB','RB','WR','WR','TE','RB','D/ST','K'], 1)]

    def test_complete_optimal_flex_and_bench(self):
        pool = self.pool() + [dict(player(10, 'TE', 100), slot='BE')]
        result = optimize(pool)
        self.assertEqual(len(result['lineup']), 9)
        self.assertEqual(len({p['playerId'] for p in result['lineup']}), 9)
        self.assertEqual(result['totalPoints'], sum(p['points'] for p in pool) - 2)
        self.assertIn(10, [p['playerId'] for p in result['lineup']])
        self.assertEqual([p['slot'] for p in result['lineup']], list(SLOTS))
        # Exact brute force assignment oracle for a pool small enough to enumerate.
        best = max(sum(p['points'] for p in subset) for subset in itertools.combinations(pool, 9)
                   if optimize(list(subset)) is not None)
        self.assertEqual(result['totalPoints'], best)

    def test_multi_position_and_duplicates(self):
        pool = self.pool()
        pool[0]['eligiblePositions'] = ['QB', 'WR']
        self.assertEqual(optimize(pool + [pool[0]]), optimize(pool))
        self.assertIsNone(optimize(pool + [dict(pool[0], points=400)]))

    def test_zero_negative_ties_and_missing(self):
        pool = [dict(p, points=-1) for p in self.pool()]
        pool += [player(99, 'QB', -1)]
        result = optimize(pool)
        self.assertEqual(result['totalPoints'], -9)
        self.assertEqual(result, optimize(list(reversed(pool))))
        self.assertEqual(result['lineup'][0]['playerId'], 1)
        pool[0]['points'] = 0
        self.assertEqual(optimize(pool)['totalPoints'], -8)
        self.assertIsNone(optimize([p for p in pool if p['position'] != 'K']))
        self.assertIsNone(optimize([dict(p, points=None) for p in pool]))

    def test_completion(self):
        self.assertTrue(completed([{'status':'final'}, {'status':'bye'}]))
        for statuses in [[], ['bye'], ['live'], ['final','upcoming']]:
            self.assertFalse(completed([{'status':s} for s in statuses]))

    def test_committed_historical_pool_and_attribution(self):
        root = Path('frontend/public/data/pocky-football/2021')
        detail = json.loads((root/'lineups/1.json').read_text())
        scoring = json.loads((root/'player-scoring.json').read_text())
        league = json.loads((root/'league.json').read_text())
        pool = weekly_pool(detail, scoring, league['standings'], 2021, 1)
        ids = {p['playerId']:p for p in pool}
        self.assertTrue(any(p['teamId'] is None for p in pool))
        for team, roster in detail['teams'].items():
            for p in roster:
                self.assertEqual(ids[p['playerId']]['teamId'], int(team))
                self.assertEqual(ids[p['playerId']]['position'], p['position'])
                self.assertEqual(ids[p['playerId']]['points'], p['points'])
        result = optimize(pool)
        self.assertTrue(any(p.get('slot') == 'BE' for p in pool if p['playerId'] in {r['playerId'] for r in result['lineup']}))
        self.assertIsNone(weekly_pool(detail, scoring, league['standings'], 2021, 2))
        self.assertIsNone(weekly_pool(dict(detail, teams={}), scoring, league['standings'], 2021, 1))
        broken = json.loads(json.dumps(detail)); broken['teams']['1'][0]['points'] = None
        recovered = weekly_pool(broken, scoring, league['standings'], 2021, 1)
        self.assertIsNotNone(recovered)  # Reliable actual scoring can fill a missing lineup value.
        derived=json.loads((root/'team-of-week.json').read_text())
        self.assertEqual([{k: p[k] for k in result['lineup'][i]} for i,p in enumerate(derived['weeks']['1']['lineup'])], result['lineup'])


class CurrentTeamOfWeekTests(unittest.TestCase):
    def test_real_current_completed_weeks_and_missing_bench_scores(self):
        root = Path('frontend/public/data/pocky-football/2026')
        derived = season_team_of_week(root)
        self.assertEqual(derived, season_team_of_week(root))
        self.assertEqual(derived, json.loads((root/'team-of-week.json').read_text()))
        home = json.loads((root/'home.json').read_text())
        last = str(home['state']['lastCompletedWeek'])
        self.assertEqual(derived['weeks'][last]['status'], 'available')
        self.assertGreater(derived['weeks'][last]['excludedUnscoredPlayers'], 0)
        self.assertNotIn(str(home['state']['currentWeek']), derived['weeks'])
        bench_used = False
        for week, result in derived['weeks'].items():
            self.assertEqual(result['status'], 'available')
            self.assertEqual([p['slot'] for p in result['lineup']], list(SLOTS))
            self.assertEqual(len({p['playerId'] for p in result['lineup']}), 9)
            self.assertEqual(round(sum(p['points'] for p in result['lineup']), 2), result['totalPoints'])
            detail = json.loads((root/f'lineups/{week}.json').read_text())
            scoring = json.loads((root/'player-scoring.json').read_text())
            league = json.loads((root/'league.json').read_text())
            pool = weekly_pool(detail, scoring, league['standings'], 2026, int(week))
            original_slots = {p['playerId']: p.get('slot') for p in pool}
            self.assertEqual(optimize(pool)['totalPoints'], result['totalPoints'])
            bench_used |= any(original_slots[p['playerId']] in ('BE', 'IR') for p in result['lineup'])
        self.assertTrue(bench_used)

    def test_unknown_score_is_excluded_not_changed_to_zero(self):
        pool = TeamOfWeekTests().pool()
        rosters = {'1': pool + [dict(player(100, 'RB', None), slot='BE')]}
        scoring = {'season': 2026, 'players': []}
        result = weekly_pool({'season': 2026, 'week': 1, 'teams': rosters}, scoring, [{'teamId': 1}], 2026, 1)
        self.assertNotIn(100, [p['playerId'] for p in result])
        self.assertEqual(optimize(result)['totalPoints'], optimize(pool)['totalPoints'])

    def test_new_final_week_is_in_same_staged_persisted_generation(self):
        import shutil
        from tempfile import TemporaryDirectory
        from football_exporter import PUBLIC_DATA, write_json
        from data_refresh import refresh, read, META, SLUG
        with TemporaryDirectory() as temp:
            root = Path(temp)/'data'
            shutil.copytree(PUBLIC_DATA, root)
            (root/SLUG/META).unlink()
            season = root/SLUG/'2026'
            final_teams = read(season/'teams.json')
            final_league = read(season/'league.json')
            final_home = read(season/'home.json')
            latest = final_home['state']['lastCompletedWeek']
            pending = json.loads(json.dumps(final_teams))
            for match in pending['matchups']:
                if match['week'] == latest:
                    match.update(status='upcoming', homeScore=None, awayScore=None, winnerTeamId=None)
            write_json(season/'teams.json', pending)
            pending_league = json.loads(json.dumps(final_league))
            for team in pending_league['standings']:
                played = [m for m in pending['matchups'] if m['status'] == 'final' and m['phase'] == 'regular'
                          and team['teamId'] in (m['homeTeamId'], m['awayTeamId'])]
                team.update(wins=sum(m['winnerTeamId'] == team['teamId'] for m in played),
                            ties=sum(m['winnerTeamId'] is None for m in played),
                            losses=sum(m['winnerTeamId'] not in (None, team['teamId']) for m in played))
            write_json(season/'league.json', pending_league)
            pending_home = json.loads(json.dumps(final_home))
            pending_home['state'].update(currentWeek=latest, lastCompletedWeek=latest-1)
            write_json(season/'home.json', pending_home)
            build_team_of_week(root, SLUG, [2026])
            self.assertNotIn(str(latest), read(season/'team-of-week.json')['weeks'])
            def fetched(slug, output, current_only):
                self.assertTrue(current_only)
                for name, data in [('league',final_league),('teams',final_teams),('home',final_home)]:
                    write_json(output/slug/'2026'/(name+'.json'), data)
                build_team_of_week(output, slug, [2026])
            self.assertTrue(refresh(root, fetched))
            derived = read(season/'team-of-week.json')
            self.assertEqual(derived['weeks'][str(latest)]['status'], 'available')
            metadata = read(root/SLUG/META)
            self.assertIn(f'{SLUG}/2026/team-of-week.json', metadata['dataHashes'])
            self.assertFalse(refresh(root, fetched))
