# CoolSmart AI

Predictive cooling experiments for three simulated servers, with an optional Arduino fan demonstration. A Random Forest forecasts temperature 20 seconds ahead from temperature, workload, and cooling level.

The temperature traces are simulated. Hardware mode sends the predictive or reactive cooling commands to physical fans; the Python code does not read temperature sensors or measure electrical energy.

Built locally from June 2025 to April 2026 for regional science fairs and ISEF. Uploaded to GitHub in October 2026 for portfolio review, so earlier version history isn’t available.

## Setup

Run commands from the project root. Python 3.12 is recommended to match the supplied environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows activation: `.venv\Scripts\activate`.

The dashboard requires Python's Tk support because it selects Matplotlib's `TkAgg` backend. Tk is a Python/system dependency, rather than a package in requirements.txt.

## Live dashboard

```bash
python -m code.dashboard_mode
```

With Arduino fans:

```bash
python -m code.dashboard_mode --hardware
```

Auto-detection chooses the first matching serial device. Select a device explicitly when needed:

```bash
python -m serial.tools.list_ports
python -m code.dashboard_mode --hardware --port YOUR_SERIAL_PORT
```

The window shows temperature and cooling output for each server. Physical fans follow the predictive controller. The Pause button or Space stops the fans and pauses simulation. Closing the window normally stops the fans and closes serial communication.

`--speed` sets simulation steps per animation frame, which is scheduled every 200 ms. This is an accelerated simulation, not a real-time hardware thermal experiment.

## Standalone experiments

The supplied `code/test_predictive.py` and `code/test_reactive.py` have `USE_HARDWARE = True`, matching the uploaded project. Set it to `False` in both files for simulation-only runs. Run only one hardware program at a time and close Arduino Serial Monitor before running it.

```bash
python -m code.test_reactive
python -m code.test_predictive
python -m code.plot_comparison
```

These scripts save CSVs and PNGs; `plot_comparison` saves three images in `results/`, rather than opening a graph window. The dashboard above provides live graphs and hardware output together.

Additional plots:

```bash
python -m code.plot_cooling_distribution
python -m code.plot_threshold
python -m code.plot_oscillation
python -m code.plot_zoom
```

`plot_oscillation` and `plot_zoom` write the same output filename; the later run overwrites it. Some scripts overwrite their existing outputs, and `plot_comparison` removes two legacy plot filenames if present.

## Data and training

The supplied model and datasets allow the experiments to run without retraining. To regenerate them:

```bash
python archive/generate_training_datas.py
python -m code.make_test_workload
python -m code.train_temp_model
```

These commands overwrite the existing training data, test workload, and saved model. The training generator specifies 40 episodes of 600 seconds for three servers. The test generator specifies 720 seconds for three servers. Training uses 200 trees, maximum depth 12, and random seed 0. Targets are shifted within each episode/server group by 20 one-second samples. The training script fits the model without reporting held-out prediction accuracy.

The uploaded model was truncated and failed to load. This copy includes a replacement trained from the supplied training CSV using the unchanged training script and scikit-learn 1.8.0. Dependencies are pinned to versions recovered from the uploaded virtual environment. Only load trusted joblib model files.

## Hardware interface

`code/hardware_bridge.py` sends newline-terminated comma-separated PWM values, for example `128,128,128\n`, at 115200 baud. Each channel accepts 0–255. Mock mode skips serial communication. The Arduino must already have compatible listener firmware; the upload did not include an Arduino sketch or wiring diagram.

## Interpretation

The dashboard and standalone experiments use different controller and thermal constants. In particular, standalone reactive cooling uses ambient 22°C and cooling coefficient 4.0, while standalone predictive cooling uses ambient 20°C and coefficient 4.5. The dashboard uses 22°C and 3.6 for both controllers, with different output caps and control rules. These configurations are preserved from the original project and are not controlled evidence of the predictor's isolated benefit.

Cooling cost is the sum of normalized cooling output over simulation steps, not measured kWh or dollars. Reported time above 80°C aggregates samples across all three servers, so its unit is server-seconds. Saved plots and metrics are historical artifacts and are not guaranteed to match the current scripts; regenerate outputs for a consistent run. No percentage energy-saving claim is established by this repository cleanup.

## Layout

- `code/`: dashboard, hardware bridge, experiments, training, and plots.
- `archive/`: training-data generator and earlier baseline simulations.
- `data/`: training data, test workload, and recorded runs.
- `results/`: saved model, figures, and historical metric summaries.

## GitHub upload

The model is a large binary file. For the initial upload, use Git from the terminal rather than GitHub's browser uploader. The included `.gitignore` excludes virtual environments, bytecode, local secrets, and duplicate backups.

Create an empty repository on GitHub, then run from this folder:

```bash
git init
git add .
git status
git commit -m "Add CoolSmart AI project"
git branch -M main
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

Review `git status` before committing. Replace `YOUR_REPOSITORY_URL` with the URL of your empty repository. Git may ask you to configure your name/email or sign in.
