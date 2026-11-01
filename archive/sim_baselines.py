import numpy as np
import matplotlib.pyplot as plt

SECONDS = 10 * 60
DT = 1
AMBIENT = 22.0

PLOT_START = 0
PLOT_END = 300

temp = 30.0
cooling = 0.0

temps = []
coolings = []
times = []

def workload_pattern(t):
    if 120 <= t < 240:
        return 0.9
    elif 360 <= t < 420:
        return 0.7
    else:
        return 0.35

for t in range(0, SECONDS, DT):
    w = workload_pattern(t)

    if temp > 75:
        cooling = 1.0
    elif temp < 70:
        cooling = 0.0

    heat_gain = 0.06 * (w * 100)
    cool_loss = 4.0 * cooling
    natural_loss = 0.02 * (temp - AMBIENT)
    temp = temp + heat_gain - cool_loss - natural_loss

    times.append(t)
    temps.append(temp)
    coolings.append(cooling)

mask = [(PLOT_START <= t <= PLOT_END) for t in times]
times_w = [t for t, m in zip(times, mask) if m]
coolings_w = [x for x, m in zip(coolings, mask) if m]


plt.figure(figsize=(10, 4))
plt.step(times_w, coolings_w, where="post")
plt.xlabel("Time (s)")
plt.ylabel("Cooling (0=off, 1=on)")
plt.title(f"Baseline Reactive: Cooling ({PLOT_START}-{PLOT_END}s)")
plt.ylim(-0.05, 1.05)
plt.tight_layout()
plt.savefig("results/cooling_plot_300s.png", dpi=200, bbox_inches="tight")
plt.close()

print("Saved 300s cooling plot to results/ folder.")
