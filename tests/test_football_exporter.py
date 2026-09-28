import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from football_exporter import normalize, read_config, verified_logo, write_json


def team(team_id, rank, wins, losses, ties=0):
    return SimpleNamespace(team_id=team_id, team_name=f"Team {team_id}", standing=rank,
                           wins=wins, losses=losses, ties=ties, points_for=110.25,
                           points_against=95.5, logo_url="https://example.com/logo.png")


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.config = {"sport": "football", "leagueId": 123, "season": 2026}
        self.league = SimpleNamespace(league_id=123, year=2026,
                                      settings=SimpleNamespace(name="Example League"),
                                      teams=[team(2, 2, 9, 4, 1), team(1, 1, 10, 4)])

    def test_normalized_standings_are_sorted_and_keep_ties(self):
        result = normalize(self.league, self.config, "example-league")
        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(result["league"]["name"], "Example League")
        self.assertEqual([row["teamId"] for row in result["standings"]], [1, 2])
        self.assertEqual(result["standings"][1]["ties"], 1)
        self.assertEqual(set(result["standings"][0]),
                         {"teamId", "name", "rank", "wins", "losses", "ties", "pointsFor", "pointsAgainst", "logo"})

    def test_duplicate_ids_are_rejected(self):
        self.league.teams[1].team_id = 2
        with self.assertRaisesRegex(ValueError, "Team IDs"):
            normalize(self.league, self.config, "example-league")

    def test_invalid_ranks_are_rejected(self):
        self.league.teams[1].standing = 3
        with self.assertRaisesRegex(ValueError, "ranks"):
            normalize(self.league, self.config, "example-league")

    def test_invalid_record_and_identity_are_rejected(self):
        self.league.teams[0].ties = -1
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            normalize(self.league, self.config, "example-league")
        self.league.teams[0].ties = 0
        self.league.league_id = 456
        with self.assertRaisesRegex(ValueError, "differs"):
            normalize(self.league, self.config, "example-league")

    def test_config_selects_entry_and_json_write(self):
        with tempfile.TemporaryDirectory() as folder:
            config_file = Path(folder) / "leagues.json"
            config_file.write_text('{"example-league":{"sport":"football","leagueId":123,"season":2026}}')
            self.assertEqual(read_config("example-league", config_file)["leagueId"], 123)
            output = Path(folder) / "data" / "league.json"
            write_json(output, normalize(self.league, self.config, "example-league"))
            self.assertIn('"ties": 1', output.read_text())

    def test_local_logo_override_by_team_id_takes_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "team-logos" / "team-2.png"
            image.parent.mkdir()
            image.write_bytes(b"fixture")
            config_file = root / "leagues.json"
            config_file.write_text('{"example-league":{"sport":"football","leagueId":123,"season":2026,"teamLogoOverrides":{"2":"team-logos/team-2.png"}}}')
            config = read_config("example-league", config_file, root)
            result = normalize(self.league, config, "example-league", logo_resolver=lambda url: None)
            self.assertEqual(result["standings"][1]["logo"], "team-logos/team-2.png")
            self.assertIsNone(result["standings"][0]["logo"])

    def test_inaccessible_espn_logo_is_omitted(self):
        class Response:
            status_code = 401
            url = "https://mystique-api.fantasy.espn.com/image"
            headers = {"content-type": "application/json"}
            def close(self):
                pass
        with patch("football_exporter.requests.get", return_value=Response()):
            self.assertIsNone(verified_logo("https://mystique-api.fantasy.espn.com/image"))


if __name__ == "__main__":
    unittest.main()
