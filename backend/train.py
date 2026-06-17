import os
import json
import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Constants
DATA_URL = "https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/concrete.csv"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(DATA_DIR, "model.joblib")
METRICS_PATH = os.path.join(DATA_DIR, "metrics.json")
LOCAL_CSV_PATH = os.path.join(DATA_DIR, "concrete.csv")

def download_data():
    """Downloads the concrete dataset if not already present locally."""
    if not os.path.exists(LOCAL_CSV_PATH):
        print(f"Downloading dataset from {DATA_URL}...")
        response = requests.get(DATA_URL)
        response.raise_for_status()
        with open(LOCAL_CSV_PATH, 'wb') as f:
            f.write(response.content)
        print("Download complete.")
    else:
        print("Dataset already exists locally.")

def train_model():
    """Loads dataset, trains Random Forest model, and saves model & metadata."""
    download_data()
    
    # Load dataset
    df = pd.read_csv(LOCAL_CSV_PATH)
    print("Dataset shape:", df.shape)
    
    # Features and Target
    # Column mapping:
    # cement, slag, ash, water, superplastic, coarseagg, fineagg, age -> strength
    feature_cols = ['cement', 'slag', 'ash', 'water', 'superplastic', 'coarseagg', 'fineagg', 'age']
    target_col = 'strength'
    
    X = df[feature_cols]
    y = df[target_col]
    
    # Get feature limits (min, max, mean) to help the frontend build sliders
    feature_limits = {}
    for col in feature_cols:
        feature_limits[col] = {
            "min": float(X[col].min()),
            "max": float(X[col].max()),
            "mean": float(X[col].mean()),
            "step": 0.1 if col not in ['age'] else 1.0
        }
        
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train Random Forest Regressor
    print("Training Random Forest Regressor...")
    model = RandomForestRegressor(n_estimators=150, random_state=42, max_depth=15, min_samples_split=2)
    model.fit(X_train, y_train)
    
    # Make predictions and evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Evaluation Metrics:")
    print(f"  R-squared (R²): {r2:.4f}")
    print(f"  Mean Absolute Error (MAE): {mae:.4f} MPa")
    print(f"  Root Mean Squared Error (RMSE): {rmse:.4f} MPa")
    
    # Save the trained model
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    
    # Get feature importances
    importances = model.feature_importances_
    feature_importances = {feature_cols[i]: float(importances[i]) for i in range(len(feature_cols))}
    
    # Sort feature importances descending
    feature_importances = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True))
    
    # Save metrics and metadata
    metrics_and_metadata = {
        "metrics": {
            "r2": float(r2),
            "mae": float(mae),
            "rmse": float(rmse),
            "sample_count": int(df.shape[0])
        },
        "feature_importances": feature_importances,
        "feature_limits": feature_limits
    }
    
    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics_and_metadata, f, indent=4)
    print(f"Metrics and metadata saved to {METRICS_PATH}")

if __name__ == "__main__":
    train_model()
