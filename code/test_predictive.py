import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from code.hardware_bridge import FanController, FanControllerConfig


TRIAL_NAME = "Predictive AI (20s Forecast Final Test)"

DT = 1
AMBIENT = 20.0
N_SERVERS = 3

SAFE_LIMIT = 75.0
OVERHEAT = 80.0

HEAT_K = 0.06
COOL_K = 4.5
NATURAL_K = 0.02

CAP = 0.7
DECAY_STEP = 0.3
EMERGENCY_LEVEL = 0.95

EMERGENCY_TEMP_ON = 78.0
EMERGENCY_PRED_ON = 79.0
EMERGENCY_DELTA_ON = 8.0
EMERGENCY_MIN_ON = 3

MIN_TEMP_FLOOR = 28.0

USE_HARDWARE = True  # Enable serial output to the Arduino.


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def cooling_to_pwm(x: float) -> int:
    return int(max(0, min(255, round(x * 255))))


def predictive_controller(
    t: int,
    temp_c: float,
    workload: float,
    current_cooling: float,
    model,
    emergency_until: int,
    prev_pred_signal: float,
):
    X_no = np.array([[temp_c, workload, 0.0]])
    pred_no_raw = float(model.predict(X_no)[0])

    X_with = np.array([[temp_c, workload, current_cooling]])
    pred_with_raw = float(model.predict(X_with)[0])

    pred_raw = max(pred_no_raw, pred_with_raw)
    pred_clipped = float(np.clip(pred_raw, temp_c - 2.0, temp_c + 18.0))
    pred_signal = 0.6 * prev_pred_signal + 0.4 * pred_clipped
    pred_delta = pred_signal - temp_c

    if t < emergency_until:
        return EMERGENCY_LEVEL, pred_signal, emergency_until

    if (
        temp_c >= EMERGENCY_TEMP_ON
        or pred_signal >= EMERGENCY_PRED_ON
        or pred_delta >= EMERGENCY_DELTA_ON
    ):
        emergency_until = t + EMERGENCY_MIN_ON
        return EMERGENCY_LEVEL, pred_signal, emergency_until

    if pred_delta >= 7.0 or temp_c >= 74.0:
        new_cooling = 0.80
    elif pred_delta >= 5.0 or temp_c >= 71.5:
        new_cooling = 0.55
    elif pred_delta >= 3.0 or temp_c >= 68.5:
        new_cooling = 0.30
    else:
        new_cooling = clamp(current_cooling - 0.15, 0.0, CAP)

    return new_cooling, pred_signal, emergency_until


work = pd.read_csv("data/test_workload.csv").sort_values(["time_s", "server"])
model = joblib.load("results/temp_predictor.joblib")
seconds = int(work["time_s"].max()) + 1


temps = np.array([30.0, 31.0, 29.5], dtype=float)
coolings = np.zeros(N_SERVERS, dtype=float)
emergency_until = np.zeros(N_SERVERS, dtype=int)

# start prediction signal near current temperature
pred_signals = temps.copy()

records = []
total_cost = 0.0


fan = FanController(
    FanControllerConfig(
        mock=(not USE_HARDWARE),
        channels=3,
        baud=115200,
        port=None,
    )
)

try:
    
    for t in range(seconds):
        for s in range(N_SERVERS):
            row = work[(work["time_s"] == t) & (work["server"] == s + 1)]
            w = 0.0 if len(row) == 0 else float(row["workload"].iloc[0])

            new_cooling, pred_signal, new_emerg = predictive_controller(
                t,
                temps[s],
                w,
                coolings[s],
                model,
                emergency_until[s],
                pred_signals[s],
            )

            coolings[s] = new_cooling
            emergency_until[s] = new_emerg
            pred_signals[s] = pred_signal

            heat_gain = HEAT_K * (w * 100)
            cool_loss = COOL_K * coolings[s]
            natural_loss = NATURAL_K * (temps[s] - AMBIENT)

            temps[s] = temps[s] + heat_gain - cool_loss - natural_loss

            if temps[s] < MIN_TEMP_FLOOR:
                temps[s] = MIN_TEMP_FLOOR

            total_cost += coolings[s]

            records.append(
                {
                    "time_s": t,
                    "server": s + 1,
                    "workload": w,
                    "temp_c": float(temps[s]),
                    "cooling": float(coolings[s]),
                    "pred_temp_20s": float(pred_signal),
                }
            )

        fan.set_pwms([cooling_to_pwm(c) for c in coolings])

    
    df = pd.DataFrame(records)
    df.to_csv("data/test_predictive.csv", index=False)

    max_temp = df["temp_c"].max()
    avg_temp = df["temp_c"].mean()
    time_over_80 = (df["temp_c"] > OVERHEAT).sum() * DT

    print("=== TEST PREDICTIVE METRICS ===")
    print(f"Max temp (C): {max_temp:.2f}")
    print(f"Avg temp (C): {avg_temp:.2f}")
    print(f"Time > 80C (seconds): {time_over_80}")
    print(f"Total cooling cost units: {total_cost:.0f}")

    
    plt.figure(figsize=(10, 4))
    for srv in range(1, N_SERVERS + 1):
        sub = df[df["server"] == srv]
        plt.plot(sub["time_s"], sub["temp_c"], label=f"Server {srv}")
    plt.axhline(SAFE_LIMIT, linestyle="--")
    plt.xlabel("Time (s)")
    plt.ylabel("Temp (C)")
    plt.title(TRIAL_NAME)
    plt.legend()
    plt.tight_layout()
    plt.savefig("results/test_predictive_temps.png", dpi=200)
    plt.close()

    print("Saved data/test_predictive.csv and results/test_predictive_temps.png")

finally:
    fan.close()
