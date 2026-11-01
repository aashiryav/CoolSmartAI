import os
import pandas as pd
import matplotlib.pyplot as plt


REACTIVE_CSV = "data/test_reactive.csv"
PREDICTIVE_CSV = "data/test_predictive.csv"
OUT_DIR = "results"

N_SERVERS = 3
PLOT_START, PLOT_END = 0, 200
SAFE_THRESHOLD = 75  # Reference temperature.

os.makedirs(OUT_DIR, exist_ok=True)


for fname in ["compare_cooling_200s.png", "compare_temps_300s.png"]:
    path = os.path.join(OUT_DIR, fname)
    if os.path.exists(path):
        os.remove(path)
        print(f"Deleted old file: {fname}")

def prep(df):
    df = df.copy()
    df["time_s"] = df["time_s"].astype(int)
    df["server"] = df["server"].astype(int)
    return df.sort_values(["server", "time_s"])

def window(df, start, end):
    return df[(df["time_s"] >= start) & (df["time_s"] <= end)].copy()


react = window(prep(pd.read_csv(REACTIVE_CSV)), PLOT_START, PLOT_END)
pred  = window(prep(pd.read_csv(PREDICTIVE_CSV)), PLOT_START, PLOT_END)

for srv in range(1, N_SERVERS + 1):
    rsub = react[react["server"] == srv]
    psub = pred[pred["server"] == srv]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    
    l1, = ax1.plot(psub["time_s"], psub["temp_c"], linewidth=2, label="Predictive (AI)")
    l2, = ax1.plot(rsub["time_s"], rsub["temp_c"], linestyle="--", linewidth=2, label="Reactive (Traditional)")

    
    ax1.axhline(SAFE_THRESHOLD, linestyle="--", linewidth=1.5, color="gray", label="Safe Threshold (75°C)")

    ax1.set_ylabel("Temp (°C)")
    ax1.set_title(f"Server {srv}: Predictive vs Reactive ({PLOT_START}–{PLOT_END}s)")
    ax1.set_ylim(20, 110)  # keeps reactive spike visible if present

    
    ax2.step(psub["time_s"], psub["cooling"], where="post", linewidth=2)
    ax2.step(rsub["time_s"], rsub["cooling"], where="post", linestyle="--", linewidth=2)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Cooling (0–1)")
    ax2.set_ylim(-0.05, 1.05)

    
    handles, labels = ax1.get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="lower right",
        bbox_to_anchor=(0.98, 0.02),
        frameon=True
    )

    plt.tight_layout(rect=[0, 0.08, 1, 1])

    out = os.path.join(OUT_DIR, f"compare_server{srv}_0_200s.png")
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)

print("Saved ONLY 3 comparison plots (0–200s):")
print(" - compare_server1_0_200s.png")
print(" - compare_server2_0_200s.png")
print(" - compare_server3_0_200s.png")
