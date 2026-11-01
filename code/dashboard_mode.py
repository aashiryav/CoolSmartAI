import matplotlib
matplotlib.use("TkAgg")

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

from code.hardware_bridge import FanController, FanControllerConfig


DT = 1
AMBIENT = 22.0

HEAT_K = 0.06
NATURAL_K = 0.02
COOL_K = 3.6  # Dashboard cooling coefficient.

SAFE_LIMIT = 75.0
OVERHEAT = 80.0

MIN_TEMP_FLOOR = 28.0
N_SERVERS = 3


CAP = 0.75
DECAY_STEP = 0.08

EMERGENCY_TEMP_ON = 79.8
EMERGENCY_PRED_ON = 80.2
EMERGENCY_LEVEL = 0.85
EMERGENCY_MIN_ON = 2


BASE_TRIG_ON = 78.0
BASE_TRIG_OFF = 74.0
BASE_CAP = 0.55
BASE_RAMP = 0.06


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def cooling_to_pwm(x: float) -> int:
    return int(max(0, min(255, round(x * 255))))


def load_workload(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path).sort_values(["time_s", "server"])
    df["time_s"] = df["time_s"].astype(int)
    df["server"] = df["server"].astype(int)
    return df


def get_workload_at(work_df: pd.DataFrame, t: int, server_id: int) -> float:
    row = work_df[(work_df["time_s"] == t) & (work_df["server"] == server_id)]
    if len(row) == 0:
        return 0.0
    return float(row["workload"].iloc[0])


def predictive_controller(t, temp_c, workload, current_cooling, model, emergency_until):
    """
    Returns:
      new_cooling (0..1),
      pred_display (what we plot),
      emergency_until (updated)
    """
    # Prediction used for decisions: "what happens if we DON'T add cooling now?"
    X_no = np.array([[temp_c, workload, 0.0]])
    pred_no_cool = float(model.predict(X_no)[0])

    # Prediction we display on the plot: "given current cooling setting"
    X_with = np.array([[temp_c, workload, current_cooling]])
    pred_display = float(model.predict(X_with)[0])

    # Emergency window: force cooling briefly once triggered
    if t < emergency_until:
        return EMERGENCY_LEVEL, pred_display, emergency_until

    if temp_c >= EMERGENCY_TEMP_ON or pred_no_cool >= EMERGENCY_PRED_ON:
        emergency_until = t + EMERGENCY_MIN_ON
        return EMERGENCY_LEVEL, pred_display, emergency_until

    
    if pred_no_cool >= 76 or temp_c >= 73:
        new_cooling = CAP
    elif pred_no_cool >= 73 or temp_c >= 71:
        new_cooling = max(current_cooling, 0.45)
    else:
        new_cooling = clamp(current_cooling - DECAY_STEP, 0.0, CAP)

    return new_cooling, pred_display, emergency_until


def baseline_traditional_controller(temp_c, current_cooling):
    """
    Temperature-triggered baseline with hysteresis, capped output, and ramp limiting.
    """
    target = current_cooling

    # hysteresis
    if temp_c >= BASE_TRIG_ON:
        target = BASE_CAP
    elif temp_c <= BASE_TRIG_OFF:
        target = 0.0

    # ramp limit
    if target > current_cooling:
        return min(target, current_cooling + BASE_RAMP)
    else:
        return max(target, current_cooling - BASE_RAMP)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hardware", action="store_true", help="enable Arduino fan output")
    parser.add_argument("--port", type=str, default=None, help="e.g. /dev/cu.usbmodem1101 (mac)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--workload_csv", type=str, default="data/test_workload.csv")
    parser.add_argument("--model_path", type=str, default="results/temp_predictor.joblib")
    parser.add_argument("--window", type=int, default=200, help="visible time window (seconds)")
    parser.add_argument("--speed", type=int, default=5, help="sim steps per animation frame")
    args = parser.parse_args()

    work = load_workload(args.workload_csv)
    seconds = int(work["time_s"].max()) + 1
    model = joblib.load(args.model_path)

    
    temps = np.array([30.0, 31.0, 29.5], dtype=float)
    coolings = np.zeros(N_SERVERS, dtype=float)
    emergency_until = np.zeros(N_SERVERS, dtype=int)

    
    temps_base = np.array([30.0, 31.0, 29.5], dtype=float)
    coolings_base = np.zeros(N_SERVERS, dtype=float)

    
    fan = FanController(
        FanControllerConfig(
            mock=(not args.hardware),
            channels=N_SERVERS,
            baud=args.baud,
            port=args.port,
        )
    )

    
    times = []
    hist_temp = [[] for _ in range(N_SERVERS)]
    hist_cool = [[] for _ in range(N_SERVERS)]
    hist_pred = [[] for _ in range(N_SERVERS)]

    hist_temp_base = [[] for _ in range(N_SERVERS)]
    hist_cool_base = [[] for _ in range(N_SERVERS)]

    
    
    
    plt.close("all")
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.subplots_adjust(top=0.92, bottom=0.10, hspace=0.40, wspace=0.25)

    
    status_ax = fig.add_axes([0.01, 0.93, 0.98, 0.06])
    status_ax.axis("off")
    txt_title = status_ax.text(0.01, 0.65, "CoolSmart AI Dashboard — Predictive vs Traditional Baseline (3 Servers)",
                               fontsize=14, fontweight="bold")
    txt_info = status_ax.text(0.01, 0.15, "t = 0s | Fans follow: PREDICTIVE output", fontsize=11)

    
    control = {"paused": False}
    button_ax = fig.add_axes([0.84, 0.01, 0.15, 0.06])
    pause_button = Button(button_ax, "Pause")

    def set_fans_zero():
        try:
            fan.set_pwms([0, 0, 0])
        except Exception:
            pass

    def toggle_pause(event=None):
        control["paused"] = not control["paused"]
        if control["paused"]:
            pause_button.label.set_text("Resume")
            set_fans_zero()  # Pause also stops the fans.
        else:
            pause_button.label.set_text("Pause")

    pause_button.on_clicked(toggle_pause)

    def on_key(event):
        if event.key == " ":
            toggle_pause()

    fig.canvas.mpl_connect("key_press_event", on_key)

    t_sim = {"t": 0}

    def step_once():
        
        t = t_sim["t"]
        if t >= seconds:
            return False

        
        for s in range(N_SERVERS):
            w = get_workload_at(work, t, s + 1)

            
            new_cool, pred_disp, new_emerg = predictive_controller(
                t, temps[s], w, coolings[s], model, emergency_until[s]
            )
            coolings[s] = new_cool
            emergency_until[s] = new_emerg

            
            heat_gain = HEAT_K * (w * 100)
            cool_loss = COOL_K * coolings[s]
            natural_loss = NATURAL_K * (temps[s] - AMBIENT)
            temps[s] = temps[s] + heat_gain - cool_loss - natural_loss
            if temps[s] < MIN_TEMP_FLOOR:
                temps[s] = MIN_TEMP_FLOOR

            
            coolings_base[s] = baseline_traditional_controller(temps_base[s], coolings_base[s])

            
            heat_gain_b = HEAT_K * (w * 100)
            cool_loss_b = COOL_K * coolings_base[s]
            natural_loss_b = NATURAL_K * (temps_base[s] - AMBIENT)
            temps_base[s] = temps_base[s] + heat_gain_b - cool_loss_b - natural_loss_b
            if temps_base[s] < MIN_TEMP_FLOOR:
                temps_base[s] = MIN_TEMP_FLOOR

            
            hist_temp[s].append(float(temps[s]))
            hist_cool[s].append(float(coolings[s]))
            hist_pred[s].append(float(pred_disp))

            hist_temp_base[s].append(float(temps_base[s]))
            hist_cool_base[s].append(float(coolings_base[s]))

        times.append(t)
        t_sim["t"] += 1
        return True

    def redraw_plots():
        
        start = max(0, len(times) - args.window)
        tw = times[start:]

        for s in range(N_SERVERS):
            axT = axes[0, s]
            axC = axes[1, s]
            axT.cla()
            axC.cla()

            tempw = hist_temp[s][start:]
            predw = hist_pred[s][start:]
            tempw_b = hist_temp_base[s][start:]

            coolw = hist_cool[s][start:]
            coolw_b = hist_cool_base[s][start:]

            
            axT.plot(tw, tempw, linewidth=2, label="Actual Temp (Predictive)")
            axT.plot(tw, predw, linestyle=":", linewidth=2, label="Predicted Future Temp")
            axT.plot(tw, tempw_b, linestyle="--", linewidth=2, label="Actual Temp (Traditional Baseline)")
            axT.axhline(SAFE_LIMIT, linestyle="--", linewidth=1, color="gray")
            axT.axhline(OVERHEAT, linestyle="--", linewidth=1, color="red")
            axT.set_title(f"Server {s+1}: Temperature")
            axT.set_ylim(20, 90)
            axT.set_xlim(max(0, tw[-1] - args.window), tw[-1] if tw else args.window)
            axT.set_xlabel("Time (s)")
            axT.set_ylabel("°C")
            axT.legend(fontsize=8, loc="upper left")

            
            axC.step(tw, coolw, where="post", linewidth=2, label="Cooling (Predictive)")
            axC.step(tw, coolw_b, where="post", linewidth=2, linestyle="--", label="Cooling (Baseline)")
            axC.set_title(f"Server {s+1}: Cooling Output")
            axC.set_ylim(-0.05, 1.05)
            axC.set_xlim(max(0, tw[-1] - args.window), tw[-1] if tw else args.window)
            axC.set_xlabel("Time (s)")
            axC.set_ylabel("0–1")
            axC.legend(fontsize=8, loc="upper left")

    def update(_frame):
        
        if control["paused"]:
            set_fans_zero()
            return

        
        for _ in range(args.speed):
            if not step_once():
                
                set_fans_zero()
                control["paused"] = True
                pause_button.label.set_text("Done")
                return

        
        try:
            fan.set_pwms([cooling_to_pwm(c) for c in coolings])
        except Exception as e:
            
            txt_info.set_text(f"Serial error (fans stopped): {e}")
            set_fans_zero()

        
        txt_info.set_text(f"t = {times[-1]}s | Fans follow: PREDICTIVE output")

        
        redraw_plots()

    ani = FuncAnimation(fig, update, interval=200, cache_frame_data=False)
    plt.show()

    
    try:
        set_fans_zero()
    finally:
        fan.close()


if __name__ == "__main__":
    main()
