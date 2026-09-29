# AI-Powered EV Charging Station Digital Twin

A software-first EV charging operations platform built from real Caltech ACN charging-session data.

The project combines historical digital-twin replay, machine-learning demand forecasting, anomaly detection, SQLite-backed analytics, a React operations dashboard, MATLAB scenario simulation, and a grounded local LLM assistant.

## Key Features

- Historical replay of 54 EV charging points (EVSEs)
- Charger states: Available, Charging, Connected / Idle, Anomaly Warning
- Daily session-associated energy forecasting using Gradient Boosting
- Forecast evaluation:
  - MAE: 69.34 kWh
  - RMSE: 94.27 kWh
  - R²: 0.505
- Isolation Forest anomaly detection
  - 491 statistically unusual sessions identified in the analyzed subset
- Session and charger analytics
- SQLite persistent data layer
- FastAPI REST backend
- React + Vite engineering operations dashboard
- Grounded local GenAI assistant using Ollama + Qwen3 1.7B
- MATLAB station-level scenario simulation

## Dataset

Source: Caltech Adaptive Charging Network (ACN-Data)

This project uses historical 2019 Caltech charging-session data.

Important distinction:
- The digital twin is a historical state reconstruction, not a live Caltech feed.
- Forecast values represent daily session-associated energy demand, not exact meter-measured site load.
- Detected anomalies represent statistically unusual sessions, not confirmed charger faults.

## Architecture

```text
Caltech ACN session data
        |
        v
Data cleaning + feature engineering
        |
        +-------------------+
        |                   |
        v                   v
Gradient Boosting      Isolation Forest
Demand Forecasting     Anomaly Detection
        |                   |
        +---------+---------+
                  |
                  v
              SQLite
                  |
                  v
             FastAPI REST API
                  |
        +---------+---------+
        |                   |
        v                   v
React Operations UI   Local Ollama / Qwen3
                          Grounded Insights

MATLAB scenario simulation complements the historical digital twin.
```

## Tech Stack

**Backend**
- Python
- FastAPI
- Pandas
- NumPy
- scikit-learn
- SQLite

**Frontend**
- React
- Vite
- JavaScript
- Lucide React

**AI / ML**
- GradientBoostingRegressor
- Isolation Forest
- Ollama
- Qwen3 1.7B

**Engineering Simulation**
- MATLAB

## Project Structure

```text
EV_Charging_Digital_Twin/
|
|-- Data/
|   |-- processed/
|
|-- backend/
|   |-- main.py
|   |-- database.py
|
|-- frontend/
|   |-- src/
|   |-- package.json
|
|-- models/
|   |-- demand_forecast_gb_holiday.pkl
|   |-- demand_forecast_metadata.json
|
|-- notebooks/
|   |-- 01_data_inspection.ipynb
|   |-- 02_data_cleaning.ipynb
|   |-- 03_exploratory_data_analysis.ipynb
|   |-- 04_demand_forecasting.ipynb
|   |-- 05_anomaly_detection.ipynb
|   |-- 06_digital_twin.ipynb
|
|-- matlab/
|   |-- ev_station_scenario_simulation.m
|
|-- requirements.txt
|-- README.md
```

## Run Locally

### 1. Python environment

```bash
python -m pip install -r requirements.txt
```

### 2. Local LLM

Install Ollama, then pull:

```bash
ollama pull qwen3:1.7b
```

### 3. Backend

From the project root:

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

API:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Main API Endpoints

```text
GET  /api/station/summary
GET  /api/twin
GET  /api/forecast
GET  /api/anomalies
GET  /api/analytics
GET  /api/database/summary
GET  /api/database/top-chargers
POST /api/ai/insights
```

## Model Notes

The demand model was evaluated using a chronological train/test split to avoid future leakage.

Final forecasting model:
- Gradient Boosting Regressor
- Holiday-aware temporal features
- MAE: 69.34 kWh
- RMSE: 94.27 kWh
- R²: 0.505

The anomaly detector is unsupervised, so anomaly labels indicate unusual session behavior rather than verified equipment faults.

## Resume Summary

Built an AI-powered EV Charging Station Digital Twin using real Caltech ACN data, combining historical EVSE state reconstruction, Gradient Boosting demand forecasting, Isolation Forest anomaly detection, FastAPI, SQLite, React, MATLAB simulation, and a grounded local Qwen3 LLM assistant.

## Author

Deandra Faith Fernandes
B.Tech Electrical and Computer Engineering
MIT World Peace University, Pune
