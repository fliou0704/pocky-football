"""ESPN football to season-scoped public JSON contracts."""

import json
import math
import os
import re
import tempfile
from pathlib import Path

from dotenv import load_dotenv
import requests


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "leagues.json"
PUBLIC_DATA = ROOT / "frontend" / "public" / "data"
PUBLIC_ROOT = ROOT / "frontend" / "public"


def read_config(slug, path=CONFIG_PATH, public_root=PUBLIC_ROOT):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("League slug must use lowercase letters, numbers, and hyphens")
    configs = json.loads(Path(path).read_text())
    if slug not in configs:
        raise ValueError(f"Unknown league: {slug}. Available: {', '.join(sorted(configs))}")
    config = configs[slug]
    if config.get("sport") != "football":
        raise ValueError("Stage 1 exporter supports football only")
    if type(config.get("leagueId")) is not int or config["leagueId"] <= 0:
        raise ValueError("leagueId must be a positive integer")
    if type(config.get("season")) is not int or config["season"] < 2000:
        raise ValueError("season must be an integer year")
    first = config.get("firstSeason", config["season"])
    if type(first) is not int or first < 2000 or first > config["season"]:
        raise ValueError("firstSeason must be an integer year no later than season")
    credential_names = config.get("credentials", {})
    for key in ("espnS2Env", "swidEnv"):
        name = credential_names.get(key)
        if name is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"credentials.{key} must be an environment variable name")
    overrides = config.get("teamLogoOverrides", {})
    if not isinstance(overrides, dict):
        raise ValueError("teamLogoOverrides must map team IDs to local image paths")
    for team_id, relative in overrides.items():
        if not re.fullmatch(r"[1-9][0-9]*", team_id):
            raise ValueError("Logo override keys must be positive team IDs")
        if not isinstance(relative, str) or not re.fullmatch(r"team-logos/[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp|svg)", relative, re.IGNORECASE):
            raise ValueError("Logo overrides must point to files in frontend/public/team-logos")
        if not (Path(public_root) / relative).is_file():
            raise ValueError(f"Logo override for team {team_id} does not exist")
    owner_overrides = config.get("ownerNameOverrides", {})
    if not isinstance(owner_overrides, dict):
        raise ValueError("ownerNameOverrides must map seasons to team IDs and names")
    for year, names in owner_overrides.items():
        if not re.fullmatch(r"20[0-9]{2}", year) or not isinstance(names, dict):
            raise ValueError("ownerNameOverrides must map seasons to team IDs and names")
        for team_id, name in names.items():
            if not re.fullmatch(r"[1-9][0-9]*", team_id) or not isinstance(name, str) or not name.strip():
                raise ValueError("Each owner override needs a team ID and nonempty name")
    return config


def verified_logo(url):
    """Return a browser-accessible image URL, or None without failing generation."""
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return None
    try:
        response = requests.get(url, stream=True, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        try:
            if response.status_code == 200 and response.url.startswith("https://") and response.headers.get("content-type", "").lower().startswith("image/"):
                return response.url
        finally:
            response.close()
    except requests.RequestException:
        pass
    return None


def normalize(league, config, slug, logo_resolver=None):
    logo_resolver = logo_resolver or (lambda url: url)
    teams = sorted(league.teams, key=lambda team: team.standing)
    overrides = config.get("teamLogoOverrides", {})
    logos = {}
    for team in teams:
        logos[team.team_id] = overrides.get(str(team.team_id)) or logo_resolver(team.logo_url)
    payload = {
        "schemaVersion": 1,
        "league": {
            "id": league.league_id,
            "slug": slug,
            "sport": config["sport"],
            "season": league.year,
            "name": league.settings.name,
        },
        "standings": [
            {
                "teamId": team.team_id,
                "name": team.team_name,
                "rank": team.standing,
                "wins": team.wins,
                "losses": team.losses,
                "ties": team.ties,
                "pointsFor": round(team.points_for, 2),
                "pointsAgainst": round(team.points_against, 2),
                "logo": logos[team.team_id],
            }
            for team in teams
        ],
    }
    validate(payload, config)
    return payload


def validate(payload, config):
    league = payload["league"]
    if league["id"] != config["leagueId"] or league["season"] != config["season"]:
        raise ValueError("ESPN league ID or season differs from configuration")
    if not isinstance(league["name"], str) or not league["name"].strip():
        raise ValueError("ESPN league name is missing")
    teams = payload["standings"]
    if not teams:
        raise ValueError("ESPN returned no teams")
    ids = [team["teamId"] for team in teams]
    ranks = [team["rank"] for team in teams]
    if any(type(team_id) is not int or team_id <= 0 for team_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Team IDs must be unique positive integers")
    if any(not isinstance(team["name"], str) or not team["name"].strip() for team in teams):
        raise ValueError("Every team needs a name")
    if ranks != list(range(1, len(teams) + 1)):
        raise ValueError("Standings ranks must be a complete order starting at 1")
    for team in teams:
        if any(type(team[field]) is not int or team[field] < 0 for field in ("wins", "losses", "ties")):
            raise ValueError("Wins, losses, and ties must be nonnegative integers")
        if any(not isinstance(team[field], (int, float)) or not math.isfinite(team[field]) for field in ("pointsFor", "pointsAgainst")):
            raise ValueError("Points totals must be finite numbers")
        logo = team["logo"]
        if logo is not None and not (isinstance(logo, str) and (logo.startswith("https://") or logo.startswith("team-logos/"))):
            raise ValueError("Invalid team logo path")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        temporary = Path(temp.name)
        try:
            json.dump(payload, temp, ensure_ascii=False, indent=2, allow_nan=False)
            temp.write("\n")
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)


def generate(slug, config_path=CONFIG_PATH, output=PUBLIC_DATA):
    config = read_config(slug, config_path)
    load_dotenv(ROOT / ".env", override=False)
    names = config.get("credentials", {})
    s2_name, swid_name = names.get("espnS2Env"), names.get("swidEnv")
    missing = [name for name in (s2_name, swid_name) if name and not os.environ.get(name)]
    if missing:
        raise ValueError("Missing environment variables: " + ", ".join(missing))
    from espn_api.football import League

    from football_seasons import build_season
    from football_home import build_home, validate_home
    logo_cache = {}
    def cached_logo(url):
        if url not in logo_cache:
            logo_cache[url] = verified_logo(url)
        return logo_cache[url]
    years = list(range(int(config.get("firstSeason", config["season"])), config["season"] + 1))
    destination = None
    team_seasons = {}
    for year in years:
        league = League(league_id=config["leagueId"], year=year,
                        espn_s2=os.environ.get(s2_name) if s2_name else None,
                        swid=os.environ.get(swid_name) if swid_name else None)
        payload, teams = build_season(league, config, slug, cached_logo)
        for team in payload['standings']:
            team_seasons.setdefault(str(team['teamId']), []).append(year)
        folder = Path(output) / slug / str(year)
        write_json(folder / "league.json", payload)
        write_json(folder / "teams.json", teams)
        if year == config["season"]:
            home = build_home(league, payload)
            validate_home(home, payload)
            write_json(folder / "home.json", home)
            destination = folder / "league.json"
    write_json(Path(output) / "site.json", {
        "schemaVersion": 1,
        "leaguePath": f"{slug}/{config['season']}/league.json",
        "seasons": list(reversed(years)),
        "teamSeasons": team_seasons,
    })
    return destination
