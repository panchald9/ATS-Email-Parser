"""
High-concurrency load testing script for Resume Parser API.
Simulates 1200+ concurrent requests against /health, /parse, and /parse-batch endpoints.
"""

import asyncio
import io
import time
import argparse
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ["API_KEY"] = "dev-secret-key"
os.environ["ENABLE_RATE_LIMIT"] = "false"

from httpx import AsyncClient, ASGITransport
import main_resume_api as api_module


def create_dummy_pdf_file() -> bytes:
    return b"%PDF-1.4\n%fake pdf content for concurrency test\nendstream\nendobj"


async def run_load_test(total_requests: int = 1200, max_concurrency: int = 200):
    print(f"\nStarting High-Concurrency Load Test...")
    print(f"Total Requests  : {total_requests}")
    print(f"Max Concurrency : {max_concurrency}")
    print("-" * 60)

    transport = ASGITransport(app=api_module.app)
    dummy_pdf = create_dummy_pdf_file()

    headers = {"x-api-key": api_module.API_KEY}

    semaphore = asyncio.Semaphore(max_concurrency)
    successes = 0
    failures = 0
    status_codes = {}
    latencies = []

    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def worker(request_id: int):
            nonlocal successes, failures
            async with semaphore:
                start_time = time.perf_counter()
                try:
                    # Alternate between endpoints: 70% /health, 20% /parse, 10% /parse-batch
                    mod = request_id % 10
                    if mod < 7:
                        response = await client.get("/health")
                    elif mod < 9:
                        files = {"file": ("test_resume.pdf", dummy_pdf, "application/pdf")}
                        response = await client.post("/parse", files=files, headers=headers)
                    else:
                        files = [
                            ("files", ("batch_1.pdf", dummy_pdf, "application/pdf")),
                            ("files", ("batch_2.pdf", dummy_pdf, "application/pdf")),
                        ]
                        response = await client.post("/parse-batch", files=files, headers=headers)

                    elapsed = (time.perf_counter() - start_time) * 1000
                    latencies.append(elapsed)

                    code = response.status_code
                    status_codes[code] = status_codes.get(code, 0) + 1

                    if code in (200, 422):  # 422 is expected for dummy PDF parsing failure, but request completes cleanly
                        successes += 1
                    else:
                        failures += 1
                except Exception:
                    failures += 1
                    status_codes["ERR"] = status_codes.get("ERR", 0) + 1

        start_total = time.perf_counter()
        tasks = [worker(i) for i in range(total_requests)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_total

    rps = total_requests / total_time if total_time > 0 else 0
    latencies.sort()

    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0

    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total Requests Executed : {total_requests}")
    print(f"Total Duration          : {total_time:.2f} seconds")
    print(f"Throughput (Req / Sec)  : {rps:.2f} req/s")
    print(f"Successful Requests     : {successes} ({(successes / total_requests) * 100:.1f}%)")
    print(f"Failed Requests         : {failures}")
    print(f"Status Code Breakdown   : {status_codes}")
    print(f"Latency p50             : {p50:.2f} ms")
    print(f"Latency p95             : {p95:.2f} ms")
    print(f"Latency p99             : {p99:.2f} ms")
    print("=" * 60 + "\n")

    return failures == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="High Concurrency API Load Test")
    parser.add_argument("--requests", type=int, default=1200, help="Total requests to execute")
    parser.add_argument("--concurrency", type=int, default=200, help="Max parallel concurrent requests")
    args = parser.parse_args()

    success = asyncio.run(run_load_test(args.requests, args.concurrency))
    if not success:
        sys.exit(1)
