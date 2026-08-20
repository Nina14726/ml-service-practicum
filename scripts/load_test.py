#!/usr/bin/env python3

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def request_once(url: str, timeout: float) -> tuple[bool, float, int | None]:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as response:
            response.read()
            status = response.status
            ok = 200 <= status < 400
    except HTTPError as exc:
        status = exc.code
        ok = False
    except (URLError, TimeoutError, OSError):
        status = None
        ok = False
    return ok, time.perf_counter() - started, status


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percent))))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Small HTTP load test for the ML service")
    parser.add_argument("base_url", help="Service URL, for example http://localhost")
    parser.add_argument("--path", default="/health", help="Endpoint to test")
    parser.add_argument("--requests", type=int, default=100, help="Total request count")
    parser.add_argument("--concurrency", type=int, default=10, help="Parallel requests")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be positive")

    url = args.base_url.rstrip("/") + "/" + args.path.lstrip("/")
    started = time.perf_counter()
    results = []

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(request_once, url, args.timeout) for _ in range(args.requests)]
        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.perf_counter() - started
    durations = [duration for _, duration, _ in results]
    successes = sum(1 for ok, _, _ in results if ok)
    failures = len(results) - successes
    statuses: dict[str, int] = {}
    for _, _, status in results:
        key = str(status) if status is not None else "connection_error"
        statuses[key] = statuses.get(key, 0) + 1

    print(f"URL: {url}")
    print(f"Requests: {len(results)}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Success: {successes}")
    print(f"Failures: {failures}")
    print(f"Elapsed: {elapsed:.3f} s")
    print(f"Throughput: {len(results) / elapsed:.2f} req/s")
    print(f"Average latency: {statistics.fmean(durations) * 1000:.2f} ms")
    print(f"p95 latency: {percentile(durations, 0.95) * 1000:.2f} ms")
    print(f"Max latency: {max(durations, default=0.0) * 1000:.2f} ms")
    print(f"Statuses: {statuses}")


if __name__ == "__main__":
    main()
