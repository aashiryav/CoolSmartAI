import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

HORIZON = 20  # predict temp 20 seconds ahead

df = pd.read_csv("data/training_data.csv")

# Sort to ensure correct shifting
df = df.sort_values(["episode", "server", "time_s"])

# Create target: future temperature
df["temp_future"] = df.groupby(["episode", "server"])["temp_c"].shift(-HORIZON)

# Drop rows where future is missing
df = df.dropna().copy()


X = df[["temp_c", "workload", "cooling"]].values
y = df["temp_future"].values

model = RandomForestRegressor(
    n_estimators=200,
    random_state=0,
    max_depth=12,
    n_jobs=-1
)

model.fit(X, y)

joblib.dump(model, "results/temp_predictor.joblib")
print("Saved model to results/temp_predictor.joblib")
