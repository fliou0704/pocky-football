"""Redacted, process-scoped HTTP metrics and bounded read-only JSON requests."""
from collections import defaultdict
from contextlib import contextmanager
import json
import os
import threading
import time
from urllib.parse import urlsplit, parse_qs
from unittest.mock import patch

import requests

_active = None


def cache_hit(label):
    """Static category labels only; callers never pass a URL or cache key."""
    if _active is not None:
        with _active.lock:
            _active.local_cache[label] += 1


def category(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ''
    if host == 'lm-api-reads.fantasy.espn.com':
        return 'fantasy:' + ','.join(sorted(parse_qs(parsed.query).get('view', ['other'])))
    if host in ('site.api.espn.com', 'sports.core.api.espn.com'):
        return 'nfl:' + ('scoreboard' if 'scoreboard' in parsed.path else 'eventlog' if 'eventlog' in parsed.path else 'status')
    if host.endswith('espncdn.com') or host == 'mystique-api.fantasy.espn.com':
        return 'images:espn'
    return 'other'  # Never retain arbitrary hostnames, paths, query strings or headers.


class Metrics:
    def __init__(self):
        self.started = time.perf_counter()
        self.rows = defaultdict(lambda: dict(requests=0, failed=0, retries=0, conditional=0,
                                             cacheHits=0, decodedBytes=0, contentLengthBytes=0, seconds=0.0))
        self.intervals = []
        self.local_cache = defaultdict(int)
        self.lock = threading.Lock()

    def summary(self):
        end = time.perf_counter()
        intervals = sorted(self.intervals)
        merged = []
        for start, finish in intervals:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(finish, merged[-1][1])
            else:
                merged.append([start, finish])
        collection = sum(b-a for a, b in merged)
        return {'categories': {k: {**v, 'seconds': round(v['seconds'], 4)} for k,v in sorted(self.rows.items())},
                'totalRequests': sum(v['requests'] for v in self.rows.values()),
                'localCacheHits':dict(sorted(self.local_cache.items())),
                'collectionWallSeconds': round(collection, 4),
                'processingWallSeconds': round(end-self.started-collection, 4),
                'totalSeconds': round(end-self.started, 4),
                'bytesSemantics': 'decoded body when consumed; Content-Length separately, not added to decoded bytes'}


@contextmanager
def instrument(label):
    """Observe requests used by the pinned library and its worker threads without changing them."""
    global _active
    metrics = Metrics()
    previous = _active
    _active = metrics
    original = requests.Session.send
    def send(session, request, **kwargs):
        start = time.perf_counter()
        key = category(request.url)
        response = None
        try:
            response = original(session, request, **kwargs)
            return response
        finally:
            end = time.perf_counter()
            if key == 'other' and response is not None and response.headers.get('Content-Type','').lower().startswith('image/'):
                key = 'images:external'
            with metrics.lock:
                row = metrics.rows[key]
                row['requests'] += 1
                row['seconds'] += end-start
                row['failed'] += int(response is None or response.status_code >= 400)
                row['conditional'] += int(response is not None and response.status_code == 304)
                if response is not None:
                    row['cacheHits'] += int('HIT' in response.headers.get('X-Cache', '').upper())
                    if response._content_consumed and isinstance(response._content, bytes):
                        row['decodedBytes'] += len(response._content)
                    size = response.headers.get('Content-Length', '')
                    row['contentLengthBytes'] += int(size) if size.isdigit() else 0
                metrics.intervals.append((start, end))
    with patch.object(requests.Session, 'send', send):
        try:
            yield metrics
        finally:
            _active = previous
            result = metrics.summary()
            print('HTTP metrics ' + label + ': ' + json.dumps(result, sort_keys=True), flush=True)
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
                    output.write('\n### HTTP metrics: '+label+'\n\n```json\n'+json.dumps(result, indent=2)+'\n```\n')


def get_json(url, *, params=None, headers=None, cookies=None, metrics=None):
    """At most two attempts; no retry on auth/rate limiting; no redirects with credentials."""
    for attempt in range(2):
        try:
            response = requests.get(url, params=params, headers=headers, cookies=cookies,
                                    timeout=(5, 20), allow_redirects=False)
            if response.status_code in (401, 403, 429):
                response.close()
                raise ValueError('Upstream access/rate limit; preserving last valid snapshot')
            if response.status_code >= 500 and attempt == 0:
                response.close()
                if metrics: metrics.rows[category(requests.Request('GET', url, params=params).prepare().url)]['retries'] += 1
                time.sleep(0.5)
                continue
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError('Unexpected upstream response')
            try:
                return response.json()
            finally:
                response.close()
        except (requests.Timeout, requests.ConnectionError):
            if attempt:
                raise ValueError('Upstream unavailable; preserving last valid snapshot') from None
            if metrics: metrics.rows[category(requests.Request('GET', url, params=params).prepare().url)]['retries'] += 1
            time.sleep(0.5)
    raise ValueError('Upstream unavailable')
