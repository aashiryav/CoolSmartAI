import os
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REACTIVE_CSV = os.path.join(BASE_DIR, "data", "test_reactive.csv")
PREDICTIVE_CSV = os.path.join(BASE_DIR, "data", "test_predictive.csv")
OUT_DIR = os.path.join(BASE_DIR, "results")
OUT_PATH = os.path.join(OUT_DIR, "temperature_oscillation_zoom.png")

os.makedirs(OUT_DIR, exist_ok=True)


SERVER = 1
ZOOM_START = 60
ZOOM_END = 140


react = pd.read_csv(REACTIVE_CSV)
pred  = pd.read_csv(PREDICTIVE_CSV)

r = react[(react["server"] == SERVER) &
          (react["time_s"] >= ZOOM_START) &
          (react["time_s"] <= ZOOM_END)].sort_values("time_s")

p = pred[(pred["server"] == SERVER) &
         (pred["time_s"] >= ZOOM_START) &
         (pred["time_s"] <= ZOOM_END)].sort_values("time_s")


fig, ax = plt.subplots(figsize=(9, 4.5))

ax.plot(p["time_s"], p["temp_c"], label="Predictive (AI)")
ax.plot(r["time_s"], r["temp_c"], linestyle="--", label="Reactive (Traditional)")

ax.set_title(f"Temperature Oscillation Zoom ({ZOOM_START}–{ZOOM_END}s) — Server {SERVER}")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Temperature (°C)")
ax.legend()

fig.tight_layout()
fig.savefig(OUT_PATH, dpi=300)
plt.close(fig)

print(f"Saved: {OUT_PATH}")
