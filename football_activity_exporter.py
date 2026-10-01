"""Refresh only backend activity/draft contracts, leaving all site features untouched."""
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from football_exporter import ROOT, PUBLIC_DATA, read_config
from football_activity import generate_activity


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--league',default='pocky-football')
    args=parser.parse_args();config=read_config(args.league)
    load_dotenv(ROOT/'.env',override=False)
    credentials=config.get('credentials',{})
    s2=os.environ.get(credentials.get('espnS2Env','ESPN_S2'))
    swid=os.environ.get(credentials.get('swidEnv','SWID'))
    if not s2 or not swid:raise SystemExit('Required ESPN credentials are missing from the environment.')
    from espn_api.requests.espn_requests import EspnFantasyRequests
    unsuccessful=[]
    for season in range(config.get('firstSeason',config['season']),config['season']+1):
        folder=PUBLIC_DATA/args.league/str(season)
        teams={t['teamId'] for t in json.loads((folder/'league.json').read_text())['standings']}
        client=EspnFantasyRequests('nfl',season,config['leagueId'],cookies={'espn_s2':s2,'SWID':swid})
        data=generate_activity(client,folder,season,teams)
        draft_complete=data['coverage'].get('draft',{}).get('complete',False)
        print(f"{season}: {len(data['events'])} executed events; {data['coverage']['status']}; draft complete={draft_complete}")
        if data['coverage']['status'] in ('partial','stale','unavailable') or not draft_complete:unsuccessful.append(season)
    if unsuccessful:raise SystemExit('Refresh requires review for seasons: '+', '.join(map(str,unsuccessful)))


if __name__=='__main__':main()
