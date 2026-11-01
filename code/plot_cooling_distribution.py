import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
REACTIVE_CSV = os.path.join(BASE_DIR, "data", "test_reactive.csv")
PREDICTIVE_CSV = os.path.join(BASE_DIR, "data", "test_predictive.csv")
OUT_DIR = os.path.join(BASE_DIR, "results")
OUT_PATH = os.path.join(OUT_DIR, "cooling_distribution_clean.png")

os.makedirs(OUT_DIR, exist_ok=True)


react = pd.read_csv(REACTIVE_CSV)
pred  = pd.read_csv(PREDICTIVE_CSV)

SERVER = 1  # Server to plot.

r = react[react["server"] == SERVER].copy()
p = pred[pred["server"] == SERVER].copy()

# Round cooling levels so we get clean bins
r_levels = r["cooling"].round(1)
p_levels = p["cooling"].round(1)

levels = sorted(set(r_levels.unique()).union(set(p_levels.unique())))

r_counts = [(r_levels == lvl).sum() for lvl in levels]
p_counts = [(p_levels == lvl).sum() for lvl in levels]

x = np.arange(len(levels))
width = 0.38


fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(x - width/2, p_counts, width, label="Predictive (AI)")
ax.bar(x + width/2, r_counts, width, label="Reactive (Traditional)")

ax.set_xticks(x)
ax.set_xticklabels([f"{lvl:.1f}" for lvl in levels])
ax.set_xlabel("Cooling Level (0–1)")
ax.set_ylabel("Frequency (seconds)")
ax.set_title(f"Cooling Intensity Distribution (Server {SERVER})")
ax.legend()

fig.tight_layout()
fig.savefig(OUT_PATH, dpi=300)
plt.close(fig)

print(f"Saved: {OUT_PATH}")
