# ConstructAI - Concrete Strength Predictor & Calibration Engine

ConstructAI is a full-stack, AI-powered decision support system designed for civil engineers and concrete batch plants. It predicts the compressive strength of concrete based on mix designs and curing time, and then **calibrates** the predictions to account for real-world material variations (cement mineralogy, aggregate shape, water quality, curing efficiency) and safety factors specified by international structural codes (**ACI 318** and **Eurocode 2**).

---

## 🏗️ The Civil Engineering Context

In structural concrete design, verifying compressive strength requires casting concrete cylinders or cubes and curing them in water for **28 days** before crushing them under a hydraulic press.
* **The Problem**: Waiting 28 days for trial mixes slows down structural construction, increases lab testing costs, and makes mix design optimization highly tedious.
* **The Solution**: ConstructAI trains an AI model on 1,030 mix formulations to instantly predict strength. It then applies physical correction coefficients (cement kinetics, aggregate morphology, salinity) and code safety factors to convert raw ML predictions into safe **Design Strengths ($f_{cd}$ / $\phi f'_c$)** used directly in reinforcement design.

---

## 🚀 Key Features

* **AI Compressive Strength Predictor**: Baseline regression model trained using a Random Forest Regressor ($R^2 = 88.11\%$).
* **Materials Science Calibration**: Adjusts predicted values using modifiers for:
  * *Cement Hydration Kinetics*: Standard Type I, High-Early Type III, Low-Heat Type IV, Blended PPC Type IP.
  * *Aggregate Morphology*: Angular (crushed stone), Rounded (gravel), Flaky (poor packing).
  * *Water Impurities*: Potable water, Recycled wash water, Brackish/saline water.
  * *Curing Quality*: Steam curing, standard curing, poor/dry site curing.
* **Structural Code Safety Engine**:
  * Implements statistical reductions ($f_{ck} = f_{mean} - 1.645\sigma$) based on Quality Control standards (Excellent, Good, Fair).
  * Applies code-specific strength reduction factors ($\gamma_c$ for Eurocode 2 or $\phi$ for ACI 318).
* **Calibrated Sensitivity Sweeps**: An interactive parameter sweep graph (using Chart.js) that lets users vary one ingredient (like cement or water) to see strength curves under local calibrated conditions.
* **Premium Glassmorphic UI**: High-fidelity dark mode dashboard built with Vanilla CSS for responsive and fluid animations.

---

## 📊 ML Model Performance

The regressor was trained on the UCI Machine Learning Concrete Dataset:
* **Dataset Size**: 1,030 mix designs
* **R-Squared ($R^2$)**: `0.8811` (88.1% of strength variance captured)
* **Mean Absolute Error (MAE)**: `3.78 MPa`
* **Root Mean Squared Error (RMSE)**: `5.54 MPa`

---

## 🛠️ Project Structure

```
concrete-prediction/
├── backend/
│   ├── main.py        # FastAPI endpoints (predictions, calibration, sensitivity, stat safety)
│   ├── train.py       # Data pipeline & Random Forest Regressor training script
│   └── concrete.csv   # Local dataset mirror
├── frontend/
│   ├── index.html     # Dashboard layout & structure
│   ├── style.css      # Custom glassmorphic styling
│   └── app.js         # State management & Chart.js graph binding
├── requirements.txt   # Python dependencies
└── run.py             # Automation script to install libraries, train model, and launch API
```

---

## 💻 Tech Stack

* **Backend**: Python, FastAPI, Scikit-learn, Pandas, NumPy, Joblib, Uvicorn
* **Frontend**: HTML5, Vanilla CSS3 (Custom Variables, Flexbox, Grid), JavaScript (ES6+), Chart.js, FontAwesome

---

## ⚡ Quick Start

### Prerequisites
Make sure you have **Python 3.10+** and **pip** installed.

### Setup and Start
1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/construct-ai.git
   cd construct-ai
   ```

2. Run the start orchestrator. This will automatically install dependencies, download the dataset, train the machine learning model, and start the local web server:
   ```bash
   python run.py
   ```

3. Open your web browser and navigate to:
   👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📝 Civil Engineering Equations Implemented

### 1. Water-to-Binder (W/B) Ratio
\[ \text{W/B Ratio} = \frac{\text{Water}}{\text{Cement} + \text{Slag} + \text{Fly Ash}} \]
*(Slag and Fly Ash are supplementary cementitious materials, acting as binders in hydration).*

### 2. Characteristic Strength ($f_{ck}$)
According to structural safety theory:
\[ f_{ck} = f_{\text{mean\_calibrated}} - 1.645 \times \sigma \]
*(Where $\sigma$ represents the standard deviation in MPa depending on the Quality Control level).*

### 3. Factored Structural Design Strength
* **Eurocode 2**:
  \[ f_{cd} = \frac{f_{ck}}{\gamma_c} \quad (\text{Default } \gamma_c = 1.50) \]
* **ACI 318**:
  \[ \phi f'_c = f_{ck} \times \phi \quad (\text{Default } \phi = 0.65) \]
