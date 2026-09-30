"""
benchmark_backend.py - measures REAL end-to-end latency of POST /api/predict against a running backend
(upload + decode + preprocess + inference + guidance lookup + DB log + JSON response).

    # terminal 1 (from backend/):  uvicorn app.main:app
    # terminal 2 (from ml/):       python evaluation/benchmark_backend.py --url http://127.0.0.1:8000 --n 60

Writes ml/evaluation/results/latency_end_to_end.json. Numbers depend on the machine it runs on.
"""
import argparse
import json
import platform
import statistics
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=60)
    a = ap.parse_args()

    files = sorted((ROOT / "tests" / "samples").rglob("*.*"))
    health = httpx.get(f"{a.url}/api/health", timeout=10).json()
    wall, server_total, server_inf, server_pre = [], [], [], []
    with httpx.Client(timeout=60) as c:
        for i in range(a.n + 3):                                    # first 3 = warm-up, discarded
            f = files[i % len(files)]
            t0 = time.perf_counter()
            r = c.post(f"{a.url}/api/predict", files={"image": (f.name, f.read_bytes(), "image/jpeg")}, data={"language": "en"})
            dt = (time.perf_counter() - t0) * 1000
            r.raise_for_status()
            if i >= 3:
                t = r.json()["timing_ms"]
                wall.append(dt); server_total.append(t["total"]); server_inf.append(t["inference"]); server_pre.append(t["preprocess"])

    def stats(x):
        x = sorted(x)
        return {"mean": round(statistics.mean(x), 1), "median": round(statistics.median(x), 1),
                "p95": round(x[int(0.95 * (len(x) - 1))], 1), "max": round(x[-1], 1)}

    out = {"requests": a.n, "model": health["model"], "wall_clock_ms_client": stats(wall),
           "server_total_ms": stats(server_total), "server_inference_ms": stats(server_inf),
           "server_preprocess_ms": stats(server_pre),
           "machine": f"{platform.processor() or platform.machine()} / {platform.system()} (client and server on same host)"}
    (Path(__file__).parent / "results").mkdir(exist_ok=True)
    (Path(__file__).parent / "results" / "latency_end_to_end.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
