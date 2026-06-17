import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import joblib

app = FastAPI(
    title="Concrete Compressive Strength Predictor API - Real World Calibrated",
    description="API for predicting concrete compressive strength calibrated with regional and code-based parameters",
    version="1.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.joblib")
METRICS_PATH = os.path.join(BASE_DIR, "metrics.json")

# Global variables
model = None
metadata = None

def load_resources():
    global model, metadata
    if os.path.exists(MODEL_PATH) and os.path.exists(METRICS_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            with open(METRICS_PATH, "r") as f:
                metadata = json.load(f)
            print("Model and metadata loaded successfully.")
        except Exception as e:
            print(f"Error loading model resources: {e}")
    else:
        print("Model resources not found. Please run training first.")

# Extended schemas for real-world calibration
class ConcreteMixInput(BaseModel):
    # Proportions (kg/m3) and Age
    cement: float = Field(..., ge=0)
    slag: float = Field(..., ge=0)
    ash: float = Field(..., ge=0)
    water: float = Field(..., ge=0)
    superplastic: float = Field(..., ge=0)
    coarseagg: float = Field(..., ge=0)
    fineagg: float = Field(..., ge=0)
    age: float = Field(..., ge=1)
    
    # Real-world Calibration Parameters
    cement_type: str = Field("type_i", description="OPC Type I, III, IV or Pozzolanic IP")
    aggregate_shape: str = Field("angular", description="Aggregate angularity: angular, rounded, flaky")
    water_quality: str = Field("potable", description="Water composition: potable, recycled, brackish")
    curing_method: str = Field("standard_wet", description="Curing: standard_wet, steam, poor_dry")
    quality_control: str = Field("good", description="QC standard deviation: excellent, good, fair")
    design_code: str = Field("eurocode_2", description="Design code safety factors: aci_318, eurocode_2")
    safety_factor: float = Field(1.5, description="Material safety factor (gamma_c or 1/phi)", ge=1.0)

class SensitivityInput(BaseModel):
    mix: ConcreteMixInput
    target_feature: str = Field(..., description="Feature to sweep across range")

def get_concrete_grade(strength: float) -> str:
    if strength < 15:
        return "Non-structural / Lean Concrete (< C15)"
    elif strength < 20:
        return "C15 (M15 equivalent) - Lightweight structural"
    elif strength < 25:
        return "C20 (M20 equivalent) - Standard domestic slabs/foundations"
    elif strength < 30:
        return "C25 (M25 equivalent) - General construction, reinforced slabs"
    elif strength < 35:
        return "C30 (M30 equivalent) - High strength, heavy-duty paving/foundations"
    elif strength < 40:
        return "C35 (M35 equivalent) - Commercial buildings, piling"
    elif strength < 50:
        return "C40 (M40 equivalent) - Highly durable, marine/reinforced structures"
    else:
        return "C50+ High-Performance Concrete - Pre-stressed concrete/skyscrapers"

def calculate_wb_ratio(mix: dict) -> float:
    binders = mix["cement"] + mix["slag"] + mix["ash"]
    if binders == 0:
        return 0.0
    return mix["water"] / binders

def compute_calibration_factors(mix: dict) -> tuple:
    """
    Computes calibration factors based on chemistry, aggregates, water, and curing.
    Returns: (total_factor, cement_factor, agg_factor, water_factor, curing_factor)
    """
    age = mix.get("age", 28)
    
    # 1. Cement Type / Chemistry Factor
    c_type = mix.get("cement_type", "type_i")
    cement_factor = 1.0
    if c_type == "type_iii": # High early strength (increased C3S/fine grind)
        if age < 7:
            cement_factor = 1.22
        elif age >= 28:
            cement_factor = 1.02
    elif c_type == "type_iv": # Low heat hydration (high C2S, low C3S/C3A)
        if age < 7:
            cement_factor = 0.68
        elif age >= 28 and age < 90:
            cement_factor = 0.88
        elif age >= 90:
            cement_factor = 1.06
    elif c_type == "type_ip": # Pozzolanic (Fly ash/Silica fume blended)
        if age < 7:
            cement_factor = 0.76
        elif age >= 28 and age < 90:
            cement_factor = 0.95
        elif age >= 90:
            cement_factor = 1.10
            
    # 2. Aggregate Shape & Bond Factor
    agg_shape = mix.get("aggregate_shape", "angular")
    agg_factor = 1.0
    if agg_shape == "angular": # Crushed stone - better mechanical interlocking
        agg_factor = 1.05
    elif agg_shape == "rounded": # Rounded gravel - weaker aggregate-cement bond
        agg_factor = 0.96
    elif agg_shape == "flaky": # Elongated/flaky - poor packing, creates internal stresses
        agg_factor = 0.82
        
    # 3. Water Quality Factor
    water_q = mix.get("water_quality", "potable")
    water_factor = 1.0
    if water_q == "recycled": # Wash water (suspended solids, sulfates)
        water_factor = 0.94
    elif water_q == "brackish": # High salinity (chlorides/alkali)
        water_factor = 0.82
        
    # 4. Curing Method Efficiency Factor
    curing = mix.get("curing_method", "standard_wet")
    curing_factor = 1.0
    if curing == "steam": # Steam cure - quick early strength but lower ultimate strength
        if age <= 3:
            curing_factor = 1.20
        else:
            curing_factor = 0.90
    elif curing == "poor_dry": # Poor curing on site - water evaporates, hydration halts
        curing_factor = 0.76
        
    total_factor = cement_factor * agg_factor * water_factor * curing_factor
    return total_factor, cement_factor, agg_factor, water_factor, curing_factor

@app.get("/api/metadata")
async def get_metadata():
    if metadata is None:
        load_resources()
    if metadata is None:
        raise HTTPException(status_code=503, detail="Model/metadata is not loaded.")
    return metadata

@app.post("/api/predict")
async def predict_strength(mix_input: ConcreteMixInput):
    global model
    if model is None:
        load_resources()
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded.")
    
    input_dict = mix_input.model_dump()
    
    # 1. Base prediction using raw ML model
    base_features = {k: input_dict[k] for k in ['cement', 'slag', 'ash', 'water', 'superplastic', 'coarseagg', 'fineagg', 'age']}
    base_df = pd.DataFrame([base_features])
    
    try:
        raw_prediction = float(model.predict(base_df)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
        
    # 2. Apply Calibration factors
    total_factor, f_cement, f_agg, f_water, f_curing = compute_calibration_factors(input_dict)
    calibrated_mean = raw_prediction * total_factor
    
    # 3. Code-based Design Safety Calculations
    # Get standard deviation based on quality control
    qc = input_dict.get("quality_control", "good")
    if qc == "excellent":
        std_dev = 3.0 # Excellent field control (MPa)
    elif qc == "fair":
        std_dev = 5.0 # Fair control (MPa)
    else:
        std_dev = 4.0 # Good control (MPa)
        
    # Characteristic strength (5% fractile value, f_ck = f_mean - 1.645 * sigma)
    characteristic_strength = max(0.0, calibrated_mean - 1.645 * std_dev)
    
    # Design strength based on ACI or Eurocode
    code = input_dict.get("design_code", "eurocode_2")
    sf = input_dict.get("safety_factor", 1.5)
    
    if code == "eurocode_2":
        # Eurocode: f_cd = f_ck / gamma_c (gamma_c is concrete safety factor, default 1.5)
        design_strength = characteristic_strength / sf
        reduction_label = "f_cd (Design Strength = f_ck / gamma_c)"
    else:
        # ACI 318: Uses strength reduction factor phi (phi = 1 / safety_factor, e.g. 1 / 1.54 = 0.65)
        phi = 1.0 / sf
        design_strength = characteristic_strength * phi
        reduction_label = "phi * f'c (Reduced Design Strength = f_ck * phi)"
        
    # Calculate Water/Binder ratio
    wb_ratio = calculate_wb_ratio(input_dict)
    
    # Generate safety and calibration warning triggers
    alerts = []
    if input_dict["curing_method"] == "poor_dry":
        alerts.append("Poor Curing: Lack of moisture causes premature drying, stopping hydration and decreasing strength by 24%.")
    if input_dict["water_quality"] == "brackish":
        alerts.append("Brackish Water: Saline content will corrode reinforcement steel and degrades long-term structural concrete durability.")
    if input_dict["aggregate_shape"] == "flaky":
        alerts.append("Flaky aggregates create internal voids and stress concentration, reducing strength by 18%.")
    if wb_ratio > 0.55:
        alerts.append("High W/B ratio: Porous concrete structure, highly susceptible to carbonation and freeze-thaw degradation.")
        
    wb_feedback = "Optimal range (0.40 - 0.50) for general structural concrete."
    if wb_ratio > 0.60:
        wb_feedback = "Warning: High water-to-binder ratio (>0.60) can lead to low compressive strength and high permeability."
    elif wb_ratio > 0.50:
        wb_feedback = "Slightly high water-to-binder ratio. Good workability but strength might be slightly compromised."
    elif wb_ratio < 0.30:
        wb_feedback = "Warning: Very low water-to-binder ratio (<0.30). Extremely dry mixture, will require significant superplasticizer."
    elif wb_ratio < 0.40:
        wb_feedback = "Low water-to-binder ratio. High strength potential, monitor workability."

    return {
        "raw_prediction": round(raw_prediction, 2),
        "calibrated_mean": round(calibrated_mean, 2),
        "characteristic_strength": round(characteristic_strength, 2),
        "design_strength": round(design_strength, 2),
        "reduction_label": reduction_label,
        "grade": get_concrete_grade(calibrated_mean),
        "wb_ratio": round(wb_ratio, 3),
        "wb_feedback": wb_feedback,
        "factors": {
            "cement": round(f_cement, 2),
            "aggregate": round(f_agg, 2),
            "water": round(f_water, 2),
            "curing": round(f_curing, 2),
            "total": round(total_factor, 2)
        },
        "alerts": alerts
    }

@app.post("/api/sensitivity")
async def get_sensitivity(input_data: SensitivityInput):
    global model, metadata
    if model is None or metadata is None:
        load_resources()
    if model is None or metadata is None:
        raise HTTPException(status_code=503, detail="Model/metadata is not loaded.")
        
    target = input_data.target_feature
    mix_dict = input_data.mix.model_dump()
    
    if target not in metadata["feature_limits"]:
        raise HTTPException(status_code=400, detail=f"Invalid target feature: {target}")
        
    limits = metadata["feature_limits"][target]
    grid = np.linspace(limits["min"], limits["max"], 20)
    
    rows = []
    for val in grid:
        temp_mix = mix_dict.copy()
        temp_mix[target] = float(val)
        
        # We need to only pass the ML features to the model prediction
        base_features = {k: temp_mix[k] for k in ['cement', 'slag', 'ash', 'water', 'superplastic', 'coarseagg', 'fineagg', 'age']}
        rows.append(base_features)
        
    df_grid = pd.DataFrame(rows)
    
    try:
        raw_preds = model.predict(df_grid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sensitivity calculation error: {str(e)}")
        
    chart_data = []
    for val, raw_pred in zip(grid, raw_preds):
        temp_mix = mix_dict.copy()
        temp_mix[target] = float(val)
        
        # Apply calibration factor to each grid point
        total_factor, _, _, _, _ = compute_calibration_factors(temp_mix)
        calibrated_pred = raw_pred * total_factor
        
        wb = calculate_wb_ratio(temp_mix)
        chart_data.append({
            "value": round(float(val), 2),
            "strength": round(float(calibrated_pred), 2),
            "wb_ratio": round(wb, 3)
        })
        
    return {
        "feature": target,
        "data": chart_data
    }

# Mount frontend directory for static assets
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
