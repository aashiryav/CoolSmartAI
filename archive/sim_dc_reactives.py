import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


SECONDS = 12 * 60
DT = 1
AMBIENT = 22.0

N_SERVERS = 3
SAFE_ON = 75.0
SAFE_OFF = 70.0

HEAT_K = 0.06
COOL_K = 4.0
NATURAL_K = 0.02

COOL_COST_PER_SEC = 1.0


PLOT_START = 0
PLOT_END = 300


def workload(server_id, t):
    base = [0.30, 0.35, 0.25][server_id]
    bursts = []
    if server_id == 0:
        bursts = [(120, 210, 0.90), (420, 480, 0.75)]
    elif server_id == 1:
        bursts = [(160, 260, 0.95), (360, 430, 0.80)]
    else:
        bursts = [(200, 320, 0.85), (500, 560, 0.70)]

    w = base
    for start, end, level in bursts:
        if start <= t < end:
            w = level
    return w


def reactive_cooling(temp, cooling):
    if temp > SAFE_ON:
        return 1.0
    if temp < SAFE_OFF:
        return 0.0
    return cooling


temps = np.array([30.0, 31.0, 29.5], dtype=float)
coolings = np.zeros(N_SERVERS, dtype=float)

records = []
total_cooling_cost = 0.0

for t in range(0, SECONDS, DT):
    for s in range(N_SERVERS):
        w = workload(s, t)

        coolings[s] = reactive_cooling(temps[s], coolings[s])

        heat_gain = HEAT_K * (w * 100)
        cool_loss = COOL_K * coolings[s]
        natural_loss = NATURAL_K * (temps[s] - AMBIENT)
        temps[s] = temps[s] + heat_gain - cool_loss - natural_loss

        total_cooling_cost += COOL_COST_PER_SEC * coolings[s]

        records.append({
            "time_s": t,
            "server": s + 1,
            "workload": float(w),
            "temp_c": float(temps[s]),
            "cooling": float(coolings[s]),
        })

df = pd.DataFrame(records)
df.to_csv("data/reactive_run.csv", index=False)

max_temp = df["temp_c"].max()
time_over_80 = (df["temp_c"] > 80).sum() * DT
avg_temp = df["temp_c"].mean()

print("=== REACTIVE RUN METRICS ===")
print(f"Max temp (C): {max_temp:.2f}")
print(f"Avg temp (C): {avg_temp:.2f}")
print(f"Time > 80C (seconds): {time_over_80}")
print(f"Total cooling cost units: {total_cooling_cost:.0f}")

dfw = df[(df["time_s"] >= PLOT_START) & (df["time_s"] <= PLOT_END)]


plt.figure(figsize=(10, 4))
for srv in range(1, N_SERVERS + 1):
    sub = dfw[dfw["server"] == srv]
    plt.plot(sub["time_s"], sub["temp_c"], label=f"Server {srv}")
plt.xlabel("Time (s)")
plt.ylabel("Temperature (C)")
plt.title(f"Reactive DC: Temperature by Server ({PLOT_START}-{PLOT_END}s)")
plt.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0)
plt.tight_layout()
plt.savefig("results/reactive_temps_300s.png", dpi=200, bbox_inches="tight")
plt.close()


plt.figure(figsize=(10, 4))
for srv in range(1, N_SERVERS + 1):
    sub = dfw[dfw["server"] == srv]
    plt.step(sub["time_s"], sub["cooling"], where="post", label=f"Server {srv}")
plt.xlabel("Time (s)")
plt.ylabel("Cooling (0=off, 1=on)")
plt.title(f"Reactive DC: Cooling Activation ({PLOT_START}-{PLOT_END}s)")
plt.ylim(-0.05, 1.05)
plt.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0)
plt.tight_layout()
plt.savefig("results/reactive_cooling_300s.png", dpi=200, bbox_inches="tight")
plt.close()

print("Saved CSV to data/reactive_run.csv")
print("Saved 300s plots to results/")
