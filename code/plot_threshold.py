import os
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
REACTIVE_CSV = os.path.join(BASE_DIR, "data", "test_reactive.csv")
PREDICTIVE_CSV = os.path.join(BASE_DIR, "data", "test_predictive.csv")
OUT_DIR = os.path.join(BASE_DIR, "results")
OUT_PATH = os.path.join(OUT_DIR, "time_above_75_threshold.png")

os.makedirs(OUT_DIR, exist_ok=True)


THRESHOLD = 75.0
SERVER = 1  # Server to plot.


react = pd.read_csv(REACTIVE_CSV)
pred  = pd.read_csv(PREDICTIVE_CSV)

r = react[react["server"] == SERVER].sort_values("time_s")
p = pred[pred["server"] == SERVER].sort_values("time_s")


fig, ax = plt.subplots(figsize=(9, 4.5))

ax.plot(p["time_s"], p["temp_c"], label="Predictive (AI)")
ax.plot(r["time_s"], r["temp_c"], linestyle="--", label="Reactive (Traditional)")

# Shade region above threshold for both
ax.fill_between(
    r["time_s"], THRESHOLD, r["temp_c"],
    where=(r["temp_c"] > THRESHOLD),
    alpha=0.2
)
ax.fill_between(
    p["time_s"], THRESHOLD, p["temp_c"],
    where=(p["temp_c"] > THRESHOLD),
    alpha=0.2
)

ax.axhline(THRESHOLD, linestyle=":", linewidth=2, label=f"{THRESHOLD:.0f}°C Threshold")

ax.set_title(f"Temperature vs Time (Shaded = Time Above {THRESHOLD:.0f}°C) — Server {SERVER}")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Temperature (°C)")
ax.legend()
fig.tight_layout()

fig.savefig(OUT_PATH, dpi=300)
plt.close(fig)

print(f"Saved: {OUT_PATH}")
