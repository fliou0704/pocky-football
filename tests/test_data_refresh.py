"""Offline release tests, with small fixtures derived from committed contracts."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch, Mock

import data_refresh as pipeline
from football_exporter import PUBLIC_DATA, write_json


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'data'
        config = pipeline.read_config(pipeline.SLUG).copy()
        config['firstSeason'] = 2026
        self.patch = patch('data_refresh.read_config', return_value=config)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        # One real season, compact profiles/scoring. No network or repository writes.
        slug = pipeline.SLUG
        def copy(name):
            write_json(self.root/name, pipeline.read(PUBLIC_DATA/name))
        source = f'{slug}/2026/'
        for name in ('league', 'teams', 'home', 'activity', 'draft', 'player-scoring', 'player-games', 'team-of-week'):
            copy(source+name+'.json')
        for week in (1, 2, 3):
            copy(source+f'lineups/{week}.json')
        site = pipeline.read(PUBLIC_DATA/'site.json')
        site['seasons'] = [2026]
        write_json(self.root/'site.json', site)
        for name in ('players', 'player-metadata-audit', 'record-book', 'draft-analysis', 'draft-scoring-audit'):
            write_json(self.root/slug/(name+'.json'), {'schemaVersion': 1})
        index = pipeline.read(PUBLIC_DATA/slug/'players-index.json')
        index['players'] = index['players'][:1]
        write_json(self.root/slug/'players-index.json', index)
        copy(index['players'][0]['path'])
        h2h = pipeline.read(PUBLIC_DATA/slug/'h2h.json')
        h2h['teams'] = [t for t in h2h['teams'] if t['teamId'] in (1, 2)]
        write_json(self.root/slug/'h2h.json', h2h)
        copy(slug+'/h2h/1-2.json')

    def generate(self, slug, output, current_only):
        self.assertTrue(current_only)
        path = output/slug/'2026/league.json'
        data = pipeline.read(path)
        data['standings'][0]['name'] = 'Updated team'
        write_json(path, data)

    def test_changed_refresh_validates_before_promotion_and_hashes_release(self):
        self.assertTrue(pipeline.refresh(self.root, self.generate))
        pipeline.validate(self.root, require_metadata=True)
        meta = pipeline.read(self.root/pipeline.SLUG/pipeline.META)
        self.assertTrue(meta['producedChanges'])
        self.assertEqual(meta['latestMatchupPeriod'], 4)
        self.assertEqual(meta['dataHashes'], pipeline.hashes(self.root))

    def test_unchanged_refresh_retains_exact_persisted_files(self):
        pipeline.refresh(self.root, self.generate)
        before = {str(p): p.read_bytes() for p in self.root.rglob('*.json')}
        self.assertFalse(pipeline.refresh(self.root, self.generate))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*.json')})

    def test_failed_fetch_never_promotes_partial_writes(self):
        before = pipeline.hashes(self.root)
        def failed(slug, output, **kwargs):
            write_json(output/slug/'2026/teams.json', {})
            raise ValueError('Upstream failure')
        with self.assertRaises(ValueError):
            pipeline.refresh(self.root, failed)
        self.assertEqual(before, pipeline.hashes(self.root))

    def test_missing_and_invalid_json(self):
        path = self.root/'site.json'
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing required'):
            pipeline.validate(self.root)
        path.write_text('{')
        with self.assertRaises(ValueError):
            pipeline.validate(self.root)

    def test_partial_scoring_does_not_replace_previous_good_data(self):
        before = pipeline.hashes(self.root)
        def partial(slug, output, **kwargs):
            path = output/slug/'2026/player-scoring.json'
            data = pipeline.read(path)
            data['players'] = []
            write_json(path, data)
        with self.assertRaisesRegex(ValueError, 'Empty current player'):
            pipeline.refresh(self.root, partial)
        self.assertEqual(before, pipeline.hashes(self.root))

    def test_regressing_week_and_missing_player_history_rejected(self):
        candidate = Path(self.tmp.name)/'candidate'
        shutil.copytree(self.root, candidate)
        path = candidate/pipeline.SLUG/'2026/home.json'
        home = pipeline.read(path)
        home['state']['currentWeek'] = 2
        write_json(path, home)
        with self.assertRaisesRegex(ValueError, 'Matchup period regressed'):
            pipeline.validate(candidate, self.root)
        shutil.copy2(self.root/pipeline.SLUG/'2026/home.json', path)
        scoring_path = candidate/pipeline.SLUG/'2026/player-scoring.json'
        scoring = pipeline.read(scoring_path)
        scoring['players'].pop()
        write_json(scoring_path, scoring)
        with self.assertRaisesRegex(ValueError, 'player scoring disappeared'):
            pipeline.validate(candidate, self.root)

    def test_generation_hash_detects_snapshot_tampering(self):
        pipeline.refresh(self.root, self.generate)
        path = self.root/pipeline.SLUG/'2026/league.json'
        data = pipeline.read(path)
        data['standings'][0]['name'] = 'Older snapshot'
        write_json(path, data)
        with self.assertRaisesRegex(ValueError, 'hashes do not match'):
            pipeline.validate(self.root)

    def test_historical_snapshot_changes_rejected(self):
        config = pipeline.read_config(pipeline.SLUG).copy()
        config['firstSeason'] = 2025
        with patch('data_refresh.read_config', return_value=config):
            source = PUBLIC_DATA/pipeline.SLUG/'2025'
            shutil.copytree(source, self.root/pipeline.SLUG/'2025')
            site = pipeline.read(self.root/'site.json')
            site['seasons'] = [2026, 2025]
            write_json(self.root/'site.json', site)
            candidate = Path(self.tmp.name)/'candidate'
            shutil.copytree(self.root, candidate)
            path = candidate/pipeline.SLUG/'2025/league.json'
            old = pipeline.read(path)
            old['standings'][0]['name'] = 'Unexpected archive mutation'
            write_json(path, old)
            with self.assertRaisesRegex(ValueError, 'Historical snapshot changed'):
                pipeline.validate(candidate, self.root)

    def test_missing_auth_fails_before_any_request(self):
        from football_exporter import generate
        with patch.dict('os.environ', {}, clear=True), patch('football_exporter.load_dotenv'), \
             patch('espn_api.football.League') as league:
            with self.assertRaisesRegex(ValueError, 'Missing environment variables'):
                generate(pipeline.SLUG, output=self.root, current_only=True)
            league.assert_not_called()

    def test_current_only_never_constructs_historical_leagues(self):
        from football_exporter import generate
        for year in range(2021, 2026):
            write_json(self.root/pipeline.SLUG/str(year)/'league.json', {'standings': [{'teamId': 1}]})
        prefix = f'{pipeline.SLUG}/2026/'
        payload = pipeline.read(self.root/(prefix+'league.json'))
        teams = pipeline.read(self.root/(prefix+'teams.json'))
        home = pipeline.read(self.root/(prefix+'home.json'))
        with ExitStack() as stack:
            stack.enter_context(patch.dict('os.environ', {'ESPN_S2': 'test', 'SWID': 'test'}))
            league = stack.enter_context(patch('espn_api.football.League'))
            stack.enter_context(patch('football_seasons.build_season', return_value=(payload, teams)))
            stack.enter_context(patch('football_home.build_home', return_value=home))
            for target in ('football_activity.generate_activity', 'football_player_scoring.generate_player_scoring',
                           'football_h2h.build_h2h', 'football_record_book.build_record_book',
                           'football_player_metadata.generate', 'football_players.build_players',
                           'football_draft_analysis.build_draft_analysis', 'football_team_of_week.build_team_of_week'):
                stack.enter_context(patch(target))
            generate(pipeline.SLUG, output=self.root, current_only=True)
            self.assertEqual(league.call_count, 1)
            self.assertEqual(league.call_args.kwargs['year'], 2026)

    def test_public_guard_rejects_older_generation(self):
        pipeline.refresh(self.root, self.generate)
        remote = pipeline.read(self.root/pipeline.SLUG/pipeline.META)
        remote['lastSuccessfulEspnFetchAt'] = '2099-01-01T00:00:00+00:00'
        with patch('requests.get', return_value=Mock(status_code=200, json=lambda: remote)):
            with self.assertRaisesRegex(ValueError, 'newer public generation'):
                pipeline.public_check(self.root)

    def test_public_verification_requires_actual_source_hashes(self):
        pipeline.refresh(self.root, self.generate)
        meta = pipeline.read(self.root/pipeline.SLUG/pipeline.META)
        with patch('requests.get', side_effect=[Mock(json=lambda: meta), Mock(json=lambda: {'wrong': True})]):
            with self.assertRaisesRegex(ValueError, 'source JSON hash mismatch'):
                pipeline.public_check(self.root, exact=True)
        def response(url, **kwargs):
            name = url.split('/data/', 1)[1]
            return Mock(json=lambda: pipeline.read(self.root/name))
        with patch('requests.get', side_effect=response):
            pipeline.public_check(self.root, exact=True)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root/'remote.git'
        self.clone = self.root/'clone'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        subprocess.run(['git', 'clone', str(self.remote), str(self.clone)], check=True, capture_output=True)
        pipeline.git('config', 'user.name', 'Test', cwd=self.clone)
        pipeline.git('config', 'user.email', 'test@example.com', cwd=self.clone)
        pipeline.git('checkout', '-b', 'main', cwd=self.clone)
        write_json(self.clone/'frontend/public/data/site.json', {'version': 1})
        pipeline.git('add', '.', cwd=self.clone)
        pipeline.git('commit', '-m', 'initial', cwd=self.clone)
        pipeline.git('push', '-u', 'origin', 'main', cwd=self.clone)

    def test_changed_persistence_and_no_change_no_commit(self):
        write_json(self.clone/'frontend/public/data/site.json', {'version': 2})
        sha = pipeline.persist(self.clone)
        self.assertEqual(sha, pipeline.git('rev-parse', 'origin/main', cwd=self.clone))
        self.assertEqual(sha, pipeline.persist(self.clone))
        self.assertEqual(pipeline.git('log', '-1', '--format=%s', cwd=self.clone),
                         'chore(data): refresh Pocky Football snapshots')

    def test_rejected_push_is_fatal(self):
        write_json(self.clone/'frontend/public/data/site.json', {'version': 2})
        hook = self.remote/'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        with self.assertRaises(subprocess.CalledProcessError):
            pipeline.persist(self.clone)
        self.assertNotEqual(pipeline.git('rev-parse', 'HEAD', cwd=self.clone),
                            pipeline.git('rev-parse', 'origin/main', cwd=self.clone))

    def test_concurrent_main_advance_rejects_stale_checkout(self):
        # A newer code/data commit advances main while an older run is working.
        other = self.root/'other'
        subprocess.run(['git', 'clone', '-b', 'main', str(self.remote), str(other)], check=True, capture_output=True)
        pipeline.git('config', 'user.name', 'Other', cwd=other)
        pipeline.git('config', 'user.email', 'other@example.com', cwd=other)
        (other/'code.txt').write_text('new code')
        pipeline.git('add', '.', cwd=other)
        pipeline.git('commit', '-m', 'newer code', cwd=other)
        pipeline.git('push', 'origin', 'main', cwd=other)
        with self.assertRaisesRegex(ValueError, 'main advanced'):
            pipeline.assert_latest(self.clone)
        with self.assertRaises(ValueError):
            pipeline.persist(self.clone)

    def test_workflow_serializes_latest_main_and_explicit_deployment(self):
        workflow = (pipeline.ROOT/'.github/workflows/pages.yml').read_text()
        self.assertIn('cancel-in-progress: false', workflow)
        self.assertIn('ref: main', workflow)
        self.assertIn('contents: write', workflow)
        self.assertLess(workflow.index('data_refresh.py persist'), workflow.index('data_refresh.py guard'))
        self.assertLess(workflow.index('data_refresh.py guard'), workflow.index('actions/deploy-pages'))
        self.assertIn('data_refresh.py verify', workflow)
        self.assertNotIn('workflow_run:', workflow)
        self.assertNotIn('--force', workflow)
        # Bot push uses GITHUB_TOKEN; no PAT or second push-triggered build is required.
        self.assertNotIn('secrets.PAT', workflow)


if __name__ == '__main__':
    unittest.main()
