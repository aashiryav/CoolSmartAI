import numpy as np
import pandas as pd

N_SERVERS = 3
SECONDS = 12 * 60
SEED = 2026

rng = np.random.default_rng(SEED)

def make_schedule(seconds, rng):
    w = np.zeros((seconds, N_SERVERS))
    base = rng.uniform(0.20, 0.40, size=N_SERVERS)
    w[:] = base

    # Bursty test workload with a separate random seed.
    for s in range(N_SERVERS):
        n_bursts = rng.integers(3, 6)
        for _ in range(n_bursts):
            start = int(rng.integers(20, seconds - 90))
            dur = int(rng.integers(30, 160))
            end = min(seconds, start + dur)
            level = float(rng.uniform(0.75, 1.0))
            w[start:end, s] = level

    
    w += rng.normal(0, 0.02, size=w.shape)
    w = np.clip(w, 0, 1)
    return w

sched = make_schedule(SECONDS, rng)

rows = []
for t in range(SECONDS):
    for s in range(N_SERVERS):
        rows.append({"time_s": t, "server": s + 1, "workload": float(sched[t, s])})

df = pd.DataFrame(rows)
df.to_csv("data/test_workload.csv", index=False)

print("Saved data/test_workload.csv")
print("Rows:", len(df))
