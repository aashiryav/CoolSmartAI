import os
print("RUNNING:", os.getcwd())
print("START generate_training_data.py")

import numpy as np
import pandas as pd


N_SERVERS = 3
DT = 1
AMBIENT = 22.0


HEAT_K = 0.06
COOL_K = 4.0
NATURAL_K = 0.02


EPISODES = 40
SECONDS = 10 * 60
SEED = 42

rng = np.random.default_rng(SEED)


def random_workload_schedule(seconds, rng):
    """
    Generate a synthetic bursty workload in [0, 1] for each server.
    Returns array shape (seconds, N_SERVERS).
    """
    w = np.zeros((seconds, N_SERVERS))
    base = rng.uniform(0.15, 0.45, size=N_SERVERS)
    w[:] = base

    for s in range(N_SERVERS):
        n_bursts = rng.integers(3, 7)
        for _ in range(n_bursts):
            start = int(rng.integers(20, seconds - 60))
            dur = int(rng.integers(20, 140))
            end = min(seconds, start + dur)
            level = float(rng.uniform(0.65, 1.0))
            w[start:end, s] = level

    w += rng.normal(0, 0.02, size=w.shape)
    w = np.clip(w, 0.05, 0.95)
    return w


records = []

for ep in range(EPISODES):
    temps = np.array([30.0, 31.0, 29.5], dtype=float) + rng.normal(0, 1.0, size=N_SERVERS)

    # start with varied but not extreme cooling
    coolings = rng.uniform(0.1, 0.6, size=N_SERVERS)

    sched = random_workload_schedule(SECONDS, rng)

    for t in range(SECONDS):
        for s in range(N_SERVERS):
            w = float(sched[t, s])

            r = rng.random()

            if r < 0.18:
                # full random reset sometimes
                coolings[s] = float(rng.uniform(0.1, 0.9))
            elif r < 0.55:
                # otherwise do a local step up/down
                coolings[s] = float(np.clip(coolings[s] + rng.uniform(-0.25, 0.25), 0.05, 0.95))

            # Occasionally adjust cooling according to workload.
            if w > 0.75 and rng.random() < 0.25:
                coolings[s] = float(np.clip(coolings[s] + rng.uniform(0.10, 0.35), 0.05, 0.95))
            elif w < 0.30 and rng.random() < 0.20:
                coolings[s] = float(np.clip(coolings[s] - rng.uniform(0.05, 0.20), 0.05, 0.95))

            heat_gain = HEAT_K * (w * 100)
            cool_loss = COOL_K * coolings[s]
            natural_loss = NATURAL_K * (temps[s] - AMBIENT)

            temps[s] = temps[s] + heat_gain - cool_loss - natural_loss

            if temps[s] < 28.0:
                temps[s] = 28.0

            records.append({
                "episode": ep,
                "time_s": t,
                "server": s + 1,
                "workload": w,
                "cooling": float(coolings[s]),
                "temp_c": float(temps[s]),
            })

df = pd.DataFrame(records)
df.to_csv("data/training_data.csv", index=False)

print("WROTE FILE:", os.path.abspath("data/training_data.csv"))
print("Saved training dataset to data/training_data.csv")
print("Rows:", len(df))
print("DONE. Wrote data/training_data.csv")
