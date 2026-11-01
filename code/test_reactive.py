import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hardware_bridge import FanController, FanControllerConfig

USE_HARDWARE = True  # Enable serial output to the Arduino.


DT = 1
AMBIENT = 22.0
N_SERVERS = 3

SAFE_ON = 95.0
SAFE_OFF = 50.0

HEAT_K = 0.06
COOL_K = 4
NATURAL_K = 0.02

COOL_COST_PER_SEC = 1.0

PLOT_START = 0
PLOT_END = 200


work = pd.read_csv("data/test_workload.csv").sort_values(["time_s", "server"])
seconds = int(work["time_s"].max()) + 1


temps = np.array([30.0, 31.0, 29.5], dtype=float)
coolings = np.zeros(N_SERVERS, dtype=float)

records = []
total_cost = 0.0


def reactive_cooling(temp: float, current: float) -> float:
    if temp > SAFE_ON:
        return 1.0
    if temp < SAFE_OFF:
        return 0.0
    return current


def cooling_to_pwm(x: float) -> int:
    return int(max(0, min(255, round(x * 255))))


fan = FanController(
    FanControllerConfig(
        mock=(not USE_HARDWARE),
        channels=N_SERVERS,
        baud=115200,
        port=None,
    )
)

try:
    
    for t in range(seconds):
        for s in range(N_SERVERS):
            row = work[(work["time_s"] == t) & (work["server"] == s + 1)]
            w = 0.0 if len(row) == 0 else float(row["workload"].iloc[0])

            coolings[s] = reactive_cooling(temps[s], coolings[s])

            heat_gain = HEAT_K * (w * 100)
            cool_loss = COOL_K * coolings[s]
            natural_loss = NATURAL_K * (temps[s] - AMBIENT)

            temps[s] = temps[s] + heat_gain - cool_loss - natural_loss

            total_cost += COOL_COST_PER_SEC * coolings[s]

            records.append(
                {
                    "time_s": t,
                    "server": s + 1,
                    "workload": w,
                    "temp_c": float(temps[s]),
                    "cooling": float(coolings[s]),
                }
            )

        fan.set_pwms([cooling_to_pwm(c) for c in coolings])

    
    df = pd.DataFrame(records)
    df.to_csv("data/test_reactive.csv", index=False)

    max_temp = df["temp_c"].max()
    avg_temp = df["temp_c"].mean()
    time_over_80 = (df["temp_c"] > 80).sum() * DT

    print("=== TEST REACTIVE METRICS ===")
    print(f"Max temp (C): {max_temp:.2f}")
    print(f"Avg temp (C): {avg_temp:.2f}")
    print(f"Time > 80C (seconds): {time_over_80}")
    print(f"Total cooling cost units: {total_cost:.0f}")

    
    dfw = df[(df["time_s"] >= PLOT_START) & (df["time_s"] <= PLOT_END)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    for s in range(1, N_SERVERS + 1):
        sub = dfw[dfw["server"] == s]
        ax1.plot(sub["time_s"], sub["temp_c"], label=f"Server {s}")
    ax1.set_ylabel("Temp (C)")
    ax1.set_title(f"Reactive on Unseen Workload: Temps + Cooling ({PLOT_START}-{PLOT_END}s)")

    for s in range(1, N_SERVERS + 1):
        sub = dfw[dfw["server"] == s]
        ax2.step(sub["time_s"], sub["cooling"], where="post")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Cooling (0/1)")
    ax2.set_ylim(-0.05, 1.05)

    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc="center left", bbox_to_anchor=(1.02, 0.5))

    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig("results/test_reactive_0_200s.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    print("Saved data/test_reactive.csv and plot results/test_reactive_0_200s.png")

finally:
    fan.close()
