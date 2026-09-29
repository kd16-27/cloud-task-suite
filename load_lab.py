"""Bounded, read-only chat load for an authorized lab; no secrets or accounts used."""
import argparse
import concurrent.futures
import json
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', required=True)
    p.add_argument('--seconds', type=int, default=120)
    p.add_argument('--workers', type=int, default=5)
    p.add_argument('--rps', type=int, default=10)
    a = p.parse_args()
    u = urllib.parse.urlparse(a.base_url)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('', '/'):
        p.error('Use a plain lab origin such as https://lab.example.com, without credentials/path/query.')
    if u.scheme == 'http' and u.hostname not in ('127.0.0.1', 'localhost'):
        p.error('Remote lab origins must use HTTPS.')
    if not (1 <= a.seconds <= 600 and 1 <= a.workers <= 20 and 1 <= a.rps <= 100):
        p.error('Bounds: seconds 1..600, workers 1..20, total requested rps 1..100.')
    print('Use only on an authorized lab. Ctrl+C stops; no database writes are performed.', flush=True)
    endpoint = a.base_url.rstrip('/') + '/api/chat'
    body = json.dumps({'question': 'How do I recover a lost bus ticket?'}).encode()
    stop = threading.Event()
    started = time.monotonic()
    until = started + a.seconds
    def worker(index):
        samples = []
        next_request = started + index / a.rps
        while not stop.is_set() and time.monotonic() < until:
            if stop.wait(max(0, next_request - time.monotonic())) or time.monotonic() >= until:
                break
            t = time.perf_counter()
            try:
                request = urllib.request.Request(endpoint, body, {'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(request, timeout=10) as response:
                    content = json.loads(response.read())
                    ok = response.status == 200 and content.get('intent') == 'recover'
            except (urllib.error.URLError, TimeoutError, ValueError):
                ok = False
            samples.append(((time.perf_counter() - t) * 1000, ok))
            next_request = max(next_request + a.workers / a.rps, time.monotonic())
        return samples
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=a.workers)
    futures = [pool.submit(worker, n) for n in range(a.workers)]
    try:
        concurrent.futures.wait(futures)
    except KeyboardInterrupt:
        stop.set()
    finally:
        pool.shutdown(wait=True)
    samples = [row for f in futures for row in f.result()]
    latencies = sorted(ms for ms, _ in samples)
    elapsed = time.monotonic() - started
    print(json.dumps({'requests': len(samples), 'errors': sum(not ok for _, ok in samples),
        'elapsed_seconds': round(elapsed, 2), 'observed_rps': round(len(samples) / elapsed, 2),
        'median_ms': round(statistics.median(latencies), 2) if samples else None,
        'p95_ms': round(latencies[max(0, int(len(latencies)*.95)-1)], 2) if samples else None,
        'note': 'Client-observed lab sample, not a production capacity guarantee.'}, indent=2))
