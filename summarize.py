import json
import statistics
from pathlib import Path

files = sorted(Path("results").glob("run_*.json"))
if not files:
    raise SystemExit("No results/run_*.json files found. Run run_experiment.py first.")

runs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
names = list(runs[0]["strategies"].keys())

print(f"========== SUMMARY over {len(runs)} saved runs ==========")
for name in names:
    scores, costs, lats, calls, n_q = [], [], [], 0, 10
    for run in runs:
        s = run["strategies"][name]
        n_q = len(s["questions"])
        scores.append(round(s["accuracy"] * n_q))
        costs.append(s["usage"]["est_cost_usd"])
        lats.append(s["latency_s"])
        calls = s["usage"]["calls"]
    mean, std = statistics.mean(scores), statistics.pstdev(scores)
    cost, lat = statistics.mean(costs), statistics.mean(lats)
    print(f"{name:34} {mean:4.1f}/{n_q} +/- {std:.1f}  runs={scores}  calls={calls:3}  ~${cost:.6f}  {lat:.0f}s")