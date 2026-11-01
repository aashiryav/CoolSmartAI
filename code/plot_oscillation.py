import pandas as pd
import matplotlib.pyplot as plt


p = pd.read_csv("data/test_predictive.csv")
r = pd.read_csv("data/test_reactive.csv")


SERVER = 1
p = p[p["server"] == SERVER]
r = r[r["server"] == SERVER]


START = 100
END = 150

p = p[(p["time_s"] >= START) & (p["time_s"] <= END)]
r = r[(r["time_s"] >= START) & (r["time_s"] <= END)]


plt.figure(figsize=(8,4))

plt.plot(p["time_s"], p["temp_c"], label="Predictive", linewidth=2)
plt.plot(r["time_s"], r["temp_c"], linestyle="--", label="Reactive", linewidth=2)

plt.xlabel("Time (s)")
plt.ylabel("Temperature (°C)")
plt.title(f"Temperature Oscillation ({START}-{END}s)")
plt.legend()

plt.tight_layout()
plt.savefig("results/temperature_oscillation_zoom.png", dpi=200)
plt.show()
