import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests
from PIL import Image
from football_team_logos import (synchronize, observation, public_url, encode_image, download,
                                validate_catalog, valid_asset, refresh_catalog, AUTH_HOST)
from football_exporter import PUBLIC_DATA

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36"><rect width="36" height="36" fill="green"/></svg>'


def row(year=2026, tid=1, owner='owner-a', logo='https://images.example/logo.svg', name='Old Team'):
    return observation({'id':tid,'name':name,'abbrev':'OT','logo':logo,'logoType':'CUSTOM_VALID',
                        'owners':[owner] if owner else []}, year)


class LogoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fetch = Mock(return_value=(SVG,'svg'))

    def sync(self, rows, **kwargs):
        return synchronize(self.root, 'pocky-football', rows, downloader=self.fetch, **kwargs)

    def test_exact_season_change_and_archive_survive_rename_outage(self):
        first = self.sync([row()])['seasons']['2026']['1']
        self.assertTrue(valid_asset(self.root,first['asset']))
        second = self.sync([row(name='Renamed Team')])['seasons']['2026']['1']
        self.assertEqual(first['asset'],second['asset'])
        self.assertEqual(self.fetch.call_count,1)
        self.fetch.side_effect = requests.ConnectionError('offline')
        preserved = self.sync([row(logo=None,name='Renamed Again')])['seasons']['2026']['1']
        self.assertEqual(preserved['asset'], first['asset'])
        self.assertEqual(preserved['provenance'],'archived-exact-season')
        changed = self.sync([row(logo='https://images.example/new.svg')])['seasons']['2026']['1']
        self.assertEqual(changed['asset'],first['asset'])
        self.assertEqual(changed['provenance'],'archived-exact-season')

    def test_new_logo_does_not_replace_prior_year(self):
        self.sync([row(2025)])
        self.fetch.return_value = (SVG.replace(b'green',b'blue'),'svg')
        catalog = self.sync([row(2025),row(2026,logo='https://images.example/new.svg')])
        self.assertNotEqual(catalog['seasons']['2025']['1']['asset'],catalog['seasons']['2026']['1']['asset'])

    def test_exact_beats_alternate_and_duplicate_sources_download_once(self):
        c = self.sync([row(2025),row(2026),row(2026,tid=2,owner='other')])
        self.assertEqual(self.fetch.call_count,1)
        self.assertEqual(c['seasons']['2026']['1']['provenance'],'exact-espn-season')
        self.assertEqual(len(list((self.root/'pocky-football/team-logos').glob('*'))),1)

    def test_same_franchise_fallback_needs_adjacent_id_and_owner_evidence(self):
        c = self.sync([row(2025),row(2026,logo=None,name='New Name')])
        r = c['seasons']['2026']['1']
        self.assertEqual(r['provenance'],'same-franchise-fallback')
        self.assertEqual(r['sourceSeason'],2025)
        for newer in (row(2026,owner='changed',logo=None),row(2026,owner=None,logo=None),row(2026,tid=2,logo=None)):
            with tempfile.TemporaryDirectory() as tmp:
                c = synchronize(tmp,'pocky-football',[row(2025),newer],downloader=self.fetch)
                self.assertIsNone(c['seasons']['2026'][str(newer['teamId'])]['asset'])
        with tempfile.TemporaryDirectory() as tmp:
            c=synchronize(tmp,'pocky-football',[row(2024),row(2026,logo=None)],downloader=self.fetch)
            self.assertIsNone(c['seasons']['2026']['1']['asset'])

    def test_same_season_owner_transfer_cannot_reuse_old_identity(self):
        self.sync([row(2025),row()])
        c=self.sync([row(owner='new owner',logo=None)])
        self.assertIsNone(c['seasons']['2026']['1']['asset'])
        self.assertEqual(c['seasons']['2026']['1']['provenance'],'generated-badge')
        self.assertFalse(c['continuity'][0]['verified'])

    def test_partial_team_metadata_preserves_catalog_and_raw_alias(self):
        before=self.sync([row()])
        client=Mock();client.league_get.side_effect=ValueError('upstream unavailable')
        self.assertEqual(before,refresh_catalog(client,self.root,'pocky-football',2026,{}))
        alias=observation({'id':1,'logoUrl':'https://images.example/alias.svg','owners':['a']},2026)
        self.assertEqual(alias['logoFields']['logo'],'https://images.example/alias.svg')

    def test_bad_images_are_not_saved_or_mistaken_for_logos(self):
        for data,kind in [(b'<html>Access denied</html>','text/html'),(b'<html/>','image/jpeg'),
                          (b'<svg onload="alert(1)"/>','image/svg+xml'),
                          (b'<svg><script>alert(1)</script></svg>','image/svg+xml')]:
            with self.assertRaises((ValueError,OSError)):
                encode_image(data,kind)
        self.assertEqual(encode_image(SVG,'image/svg+xml'),(SVG,'svg'))
        internal=SVG.replace(b'fill="green"',b'''fill="url('#local')"''')
        self.assertEqual(encode_image(internal,'image/svg+xml'),(internal,'svg'))
        image=Image.new('RGB',(600,300),'green');buffer=BytesIO();image.save(buffer,'PNG')
        data,kind=encode_image(buffer.getvalue(),'image/png')
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.size,(256,128))
        self.assertEqual(kind,'webp')
        for url in ('http://example.com/a','https://user:secret@example.com/x','https://example.com/x?token=x',
                    'https://127.0.0.1/x','https://localhost/x','https://bad:wrong/x'):
            self.assertFalse(public_url(url))

    def test_asset_corruption_fails_integrity_validation(self):
        c=self.sync([row()]);asset=c['seasons']['2026']['1']['asset']
        (self.root/asset.removeprefix('data/')).write_bytes(b'not an image')
        with self.assertRaisesRegex(ValueError,'Invalid archived'):
            validate_catalog(self.root,'pocky-football')

    def test_automatic_refresh_discovers_new_current_image_and_preserves_history(self):
        from types import SimpleNamespace
        before=self.sync([row(2025)])['seasons']['2025']['1']
        def metadata(client):
            if client.year not in (2025,2026): raise ValueError('optional history unavailable')
            return [{'id':1,'name':'New name','abbrev':'NN','owners':['owner-a'],
                     'logo':'https://images.example/new.svg' if client.year==2026 else 'https://images.example/logo.svg'}]
        self.fetch.return_value=(SVG.replace(b'green',b'blue'),'svg')
        with patch('football_team_logos.read_teams',side_effect=metadata), patch('football_team_logos.download',self.fetch):
            catalog=refresh_catalog(SimpleNamespace(year=2026),self.root,'pocky-football',2026,{})
        self.assertEqual(catalog['seasons']['2025']['1']['asset'],before['asset'])
        self.assertNotEqual(catalog['seasons']['2026']['1']['asset'],before['asset'])
        self.assertTrue(catalog['continuity'][0]['verified'])

    def test_credentials_are_restricted_to_espn_and_removed_on_redirect(self):
        redirect=Mock(status_code=302,headers={'Location':'https://images.example/x.svg'})
        image=Mock(status_code=200,headers={'content-type':'image/svg+xml'})
        image.iter_content.return_value=[SVG]
        responses=[]
        for response in (redirect,image):
            context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
            responses.append(context)
        with patch('football_team_logos.socket.getaddrinfo',return_value=[(None,None,None,None,('8.8.8.8',443))]), \
             patch('football_team_logos.requests.get',side_effect=responses) as get:
            download('https://'+AUTH_HOST+'/apis/v1/domains/lm/images/00000000-0000-0000-0000-000000000000',{'SWID':'test','espn_s2':'test'})
            self.assertEqual(get.call_args_list[0].kwargs['cookies'],{'SWID':'test','espn_s2':'test'})
            self.assertIsNone(get.call_args_list[1].kwargs['cookies'])

    def test_committed_real_coverage_and_identity_evidence(self):
        catalog=validate_catalog(PUBLIC_DATA,'pocky-football')
        entries=[r for y,teams in catalog['seasons'].items() if 2021<=int(y)<=2026 for r in teams.values()]
        self.assertEqual(len(entries),66)
        self.assertEqual(sum(r['provenance']=='exact-espn-season' for r in entries),63)
        self.assertEqual(sum(r['provenance']=='same-franchise-fallback' for r in entries),3)
        self.assertTrue(all(r['asset'] for r in entries))
        self.assertTrue(all(e['verified'] for e in catalog['continuity']))
        for year in range(2021,2027):
            standings=json.loads((PUBLIC_DATA/'pocky-football'/str(year)/'league.json').read_text())['standings']
            self.assertEqual({str(t['teamId']) for t in standings},set(catalog['seasons'][str(year)]))
        serialized=json.dumps(catalog)
        self.assertNotIn('ESPN_S2',serialized)
        self.assertNotIn('ownerHash',serialized)
        self.assertNotIn('owners',serialized)


if __name__=='__main__': unittest.main()
