# AI-Powered EV Charging Station Digital Twin

An end-to-end EV charging operations platform built using real charging-session data from the Caltech Adaptive Charging Network (ACN).

The project combines a historical digital twin, machine-learning demand forecasting, anomaly detection, operational analytics, a React dashboard, MATLAB scenario simulation, and a locally hosted GenAI assistant.

## Key Features

- Historical replay of 54 EV charging points (EVSEs)
- Charger states: Available, Charging, Connected / Idle, and Anomaly Warning
- Daily session-associated energy forecasting using Gradient Boosting
- Forecast evaluation:
  - MAE: 69.34 kWh
  - RMSE: 94.27 kWh
  - R²: 0.505
- Isolation Forest anomaly detection
  - 491 statistically unusual sessions identified in the analyzed subset
- Session-level and charger-level analytics
- SQLite-backed data storage
- FastAPI REST backend
- React + Vite operations dashboard
- Local GenAI assistant using Ollama + Qwen3 1.7B
- MATLAB-based station scenario simulation

## Dataset

**Source:** Caltech Adaptive Charging Network (ACN-Data)

The project uses historical charging-session data from 2019.

A few important notes about how the data is used:

- The digital twin reconstructs historical charger activity; it is not connected to a live Caltech feed.
- Forecast values represent daily session-associated energy demand rather than exact meter-measured site load.
- Anomaly detection identifies statistically unusual sessions and does not classify confirmed charger faults.

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
             FastAPI API
                  |
        +---------+---------+
        |                   |
        v                   v
React Operations UI   Ollama + Qwen3 1.7B
                        Grounded Assistant

MATLAB scenario simulation complements the historical digital twin.
```

## Tech Stack

### Backend

- Python
- FastAPI
- Pandas
- NumPy
- scikit-learn
- SQLite

### Frontend

- React
- Vite
- JavaScript
- Lucide React

### AI / ML

- GradientBoostingRegressor
- Isolation Forest
- Ollama
- Qwen3 1.7B

### Engineering Simulation

- MATLAB

## Project Structure

```text
EV_Charging_Digital_Twin/
|
|-- Data/
|   `-- processed/
|
|-- backend/
|   |-- main.py
|   `-- database.py
|
|-- frontend/
|   |-- src/
|   `-- package.json
|
|-- models/
|   |-- demand_forecast_gb_holiday.pkl
|   `-- demand_forecast_metadata.json
|
|-- notebooks/
|   |-- 01_data_inspection.ipynb
|   |-- 02_data_cleaning.ipynb
|   |-- 03_exploratory_data_analysis.ipynb
|   |-- 04_demand_forecasting.ipynb
|   |-- 05_anomaly_detection.ipynb
|   `-- 06_digital_twin.ipynb
|
|-- matlab/
|   `-- ev_station_scenario_simulation.m
|
|-- requirements.txt
|-- start_backend.bat
|-- start_frontend.bat
`-- README.md
```

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/deandrafernandes14/ai-ev-charging-digital-twin.git
cd ai-ev-charging-digital-twin
```

### 2. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Set up the local LLM

Install Ollama, then pull the model:

```bash
ollama pull qwen3:1.7b
```

### 4. Start the backend

From the project root:

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 5. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

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

## Forecasting Model

The demand model uses a chronological train/test split to avoid using future data during training.

The final Gradient Boosting model uses:

- day of week
- month
- weekend indicator
- previous-day demand
- seven-day lag
- seven-day rolling demand
- holiday indicator

Final test results:

| Metric | Value |
|---|---:|
| MAE | 69.34 kWh |
| RMSE | 94.27 kWh |
| R² | 0.505 |

The model is evaluated against a seasonal-naive baseline to confirm that it improves on a simple historical reference.

## Anomaly Detection

Isolation Forest is used to flag unusual charging sessions based on:

- delivered energy
- connected duration
- active charging duration
- idle duration

Because the dataset does not include verified anomaly labels, the model output is treated as an indicator for sessions that deserve review rather than as a fault diagnosis.

## Digital Twin

The digital twin reconstructs charger states from historical session timestamps.

At any selected replay time, the system can show:

- total EVSEs
- available chargers
- actively charging chargers
- connected / idle chargers
- occupied chargers
- utilization
- anomaly warnings
- individual charger status and session information

## Local GenAI Assistant

The operations assistant runs locally through Ollama using Qwen3 1.7B.

It receives structured project data from the backend and can answer questions about:

- current replay state
- charging and idle behavior
- demand forecasts
- anomaly events
- charger statistics
- model outputs
- digital-twin behavior

The assistant is grounded in project data and is designed to avoid presenting unsupported assumptions as facts.

## MATLAB Scenario Simulation

The MATLAB component models three station-level operating scenarios:

- Normal Operation
- Peak Demand
- Abnormal Charger Behaviour

These simulations are used for engineering analysis and are separate from the historical Caltech charging data.

## Limitations

- The project uses historical replay rather than live EVSE telemetry.
- Forecast values represent session-associated daily energy, not exact site meter load.
- Anomaly detection is unsupervised and does not provide confirmed fault labels.
- The GenAI assistant is limited to the data supplied by the backend.
- MATLAB results are simulated engineering scenarios rather than measured Caltech power traces.

## Author

**Deandra Faith Fernandes**  
B.Tech Electrical and Computer Engineering  
MIT World Peace University, Pune
