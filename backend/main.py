from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware



import pandas as pd

import numpy as np

import pickle

import json
import re



from pathlib import Path

from datetime import timedelta





# ============================================================

# FASTAPI APPLICATION

# ============================================================



app = FastAPI(

    title="AI-Powered EV Charging Station Digital Twin API",

    description=(

        "REST API for EV charging analytics, demand forecasting, "

        "anomaly detection and historical digital twin replay."

    ),

    version="1.0.0"

)





# ============================================================

# CORS

# Allows our future React frontend to communicate with FastAPI

# ============================================================



app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)





# ============================================================

# PROJECT PATHS

# ============================================================



BASE_DIR = Path(__file__).resolve().parent

PROJECT_DIR = BASE_DIR.parent



SESSION_DATA_PATH = (

    PROJECT_DIR

    / "Data"

    / "processed"

    / "acn_caltech_2019_anomalies.csv"

)



DAILY_DATA_PATH = (

    PROJECT_DIR

    / "Data"

    / "processed"

    / "daily_energy_history.csv"

)



MODEL_PATH = (

    PROJECT_DIR

    / "models"

    / "demand_forecast_gb_holiday.pkl"

)



METADATA_PATH = (

    PROJECT_DIR

    / "models"

    / "demand_forecast_metadata.json"

)





# ============================================================

# LOAD SESSION DATA

# ============================================================



df = pd.read_csv(SESSION_DATA_PATH)



timestamp_cols = [

    "connectionTime_local",

    "disconnectTime_local",

    "doneChargingTime_local"

]



for col in timestamp_cols:



    df[col] = pd.to_datetime(

        df[col],

        utc=True

    ).dt.tz_convert("America/Los_Angeles")





CHARGER_IDS = sorted(

    df["stationID"]

    .dropna()

    .unique()

    .tolist()

)





# ============================================================

# LOAD DAILY ENERGY HISTORY

# ============================================================



daily_history = pd.read_csv(DAILY_DATA_PATH)



daily_history["date"] = pd.to_datetime(

    daily_history["date"]

)



daily_history = (

    daily_history

    .sort_values("date")

    .reset_index(drop=True)

)





# ============================================================

# LOAD FORECAST MODEL

# ============================================================



with open(MODEL_PATH, "rb") as file:

    forecast_model = pickle.load(file)





with open(METADATA_PATH, "r") as file:

    model_metadata = json.load(file)





print("-------------------------------------------")

print("EV DIGITAL TWIN BACKEND")

print("-------------------------------------------")

print(f"Sessions loaded: {len(df)}")

print(f"Chargers loaded: {len(CHARGER_IDS)}")

print(f"Daily history rows: {len(daily_history)}")

print(

    "Forecast model:",

    type(forecast_model).__name__

)

print("-------------------------------------------")





# ============================================================

# HOLIDAY DATES

# Same 2019 US federal holiday feature used during training

# ============================================================



HOLIDAYS_2019 = {

    "2019-01-01",

    "2019-01-21",

    "2019-02-18",

    "2019-05-27",

    "2019-07-04",

    "2019-09-02",

    "2019-10-14",

    "2019-11-11",

    "2019-11-28",

    "2019-12-25",

}





# ============================================================

# DIGITAL TWIN STATE ENGINE

# ============================================================



def get_charger_states(replay_time):



    try:



        replay_ts = pd.Timestamp(replay_time)



        if replay_ts.tzinfo is None:



            replay_ts = replay_ts.tz_localize(

                "America/Los_Angeles"

            )



        else:



            replay_ts = replay_ts.tz_convert(

                "America/Los_Angeles"

            )



    except Exception:



        raise HTTPException(

            status_code=400,

            detail="Invalid replay time."

        )



    states = []



    for charger in CHARGER_IDS:



        charger_sessions = df[

            df["stationID"] == charger

        ]



        active = charger_sessions[

            (

                charger_sessions["connectionTime_local"]

                <= replay_ts

            )

            &

            (

                charger_sessions["disconnectTime_local"]

                > replay_ts

            )

        ]



        if active.empty:



            states.append({

                "stationID": charger,

                "state": "Available",

                "anomaly_warning": False,

                "session_energy_kwh": None,

                "anomaly_score": None

            })



            continue



        session = active.iloc[0]



        done_time = session[

            "doneChargingTime_local"

        ]



        if pd.isna(done_time) or replay_ts < done_time:



            state = "Charging"



        else:



            state = "Connected / Idle"



        anomaly_warning = (

            session["status"] == "Anomaly"

        )



        score = session["anomaly_score"]



        states.append({

            "stationID": charger,

            "state": state,

            "anomaly_warning":

                bool(anomaly_warning),

            "session_energy_kwh":

                round(

                    float(

                        session["kWhDelivered"]

                    ),

                    2

                ),

            "anomaly_score":

                (

                    round(float(score), 4)

                    if pd.notna(score)

                    else None

                )

        })



    return states





# ============================================================

# FORECAST FEATURE ENGINE

# ============================================================



def build_forecast_features(target_date):



    target_date = pd.Timestamp(

        target_date

    ).normalize()



    previous_day = (

        target_date - timedelta(days=1)

    )



    previous_week = (

        target_date - timedelta(days=7)

    )



    previous_day_row = daily_history[

        daily_history["date"] == previous_day

    ]



    previous_week_row = daily_history[

        daily_history["date"] == previous_week

    ]



    historical_window = daily_history[

        (

            daily_history["date"]

            < target_date

        )

        &

        (

            daily_history["date"]

            >= target_date

            - timedelta(days=7)

        )

    ]



    if previous_day_row.empty:



        raise HTTPException(

            status_code=400,

            detail=(

                "Insufficient historical data "

                "for energy_lag_1."

            )

        )



    if previous_week_row.empty:



        raise HTTPException(

            status_code=400,

            detail=(

                "Insufficient historical data "

                "for energy_lag_7."

            )

        )



    if len(historical_window) < 7:



        raise HTTPException(

            status_code=400,

            detail=(

                "Insufficient historical data "

                "for 7-day rolling average."

            )

        )



    lag_1 = float(

        previous_day_row.iloc[0][

            "daily_energy_kwh"

        ]

    )



    lag_7 = float(

        previous_week_row.iloc[0][

            "daily_energy_kwh"

        ]

    )



    rolling_7 = float(

        historical_window[

            "daily_energy_kwh"

        ].mean()

    )



    is_holiday = int(

        target_date.strftime("%Y-%m-%d")

        in HOLIDAYS_2019

    )



    features = pd.DataFrame(

        [{

            "day_of_week":

                target_date.dayofweek,



            "month":

                target_date.month,



            "is_weekend":

                int(

                    target_date.dayofweek

                    >= 5

                ),



            "energy_lag_1":

                lag_1,



            "energy_lag_7":

                lag_7,



            "energy_rolling_7":

                rolling_7,



            "is_holiday":

                is_holiday

        }]

    )



    return features





# ============================================================

# HOME

# ============================================================



@app.get("/")

def home():



    return {

        "message":

            "EV Charging Digital Twin API is running",

        "status": "online"

    }





# ============================================================

# HEALTH

# ============================================================



@app.get("/api/health")

def health_check():



    return {

        "status": "healthy",

        "sessions_loaded": len(df),

        "chargers_loaded": len(CHARGER_IDS),

        "forecast_model_loaded": True

    }





# ============================================================

# DATASET SUMMARY

# ============================================================



@app.get("/api/station/summary")

def station_summary():



    return {

        "site": "Caltech ACN",

        "sessions": int(len(df)),

        "chargers": int(len(CHARGER_IDS)),



        "total_energy_kwh":

            round(

                float(

                    df["kWhDelivered"].sum()

                ),

                2

            ),



        "anomalous_sessions":

            int(

                (

                    df["status"]

                    == "Anomaly"

                ).sum()

            )

    }





# ============================================================

# DIGITAL TWIN

# ============================================================



@app.get("/api/twin")

def digital_twin(

    replay_time: str = "2019-01-08 10:30:00"

):



    states = get_charger_states(

        replay_time

    )



    available = sum(

        x["state"] == "Available"

        for x in states

    )



    charging = sum(

        x["state"] == "Charging"

        for x in states

    )



    connected_idle = sum(

        x["state"] == "Connected / Idle"

        for x in states

    )



    occupied = (

        charging + connected_idle

    )



    anomaly_warnings = sum(

        x["anomaly_warning"]

        for x in states

    )



    total = len(states)



    return {



        "site": "Caltech ACN",



        "replay_time": replay_time,



        "summary": {



            "total_chargers":

                total,



            "available":

                available,



            "charging":

                charging,



            "connected_idle":

                connected_idle,



            "occupied":

                occupied,



            "utilization_percent":

                round(

                    occupied / total * 100,

                    2

                ),



            "actively_charging_percent":

                round(

                    charging / total * 100,

                    2

                ),



            "anomaly_warnings":

                anomaly_warnings

        },



        "chargers": states

    }





# ============================================================

# ANOMALIES

# ============================================================



@app.get("/api/anomalies")

def anomalies(limit: int = 20):



    limit = max(

        1,

        min(limit, 100)

    )



    anomaly_df = (

        df[

            df["status"] == "Anomaly"

        ]

        .sort_values(

            "anomaly_score",

            ascending=False

        )

        .head(limit)

    )



    results = []



    for _, row in anomaly_df.iterrows():



        results.append({



            "sessionID":

                str(row["sessionID"]),



            "stationID":

                str(row["stationID"]),



            "energy_kwh":

                round(

                    float(

                        row["kWhDelivered"]

                    ),

                    2

                ),



            "connected_hours":

                round(

                    float(

                        row["connected_hours"]

                    ),

                    2

                ),



            "charging_hours":

                round(

                    float(

                        row["charging_hours"]

                    ),

                    2

                ),



            "idle_hours":

                round(

                    float(

                        row["idle_hours"]

                    ),

                    2

                ),



            "anomaly_score":

                round(

                    float(

                        row["anomaly_score"]

                    ),

                    4

                )

        })



    return {



        "method":

            "Isolation Forest",



        "total_anomalies":

            int(

                (

                    df["status"]

                    == "Anomaly"

                ).sum()

            ),



        "note":

            (

                "Anomaly indicates unusual "

                "session behaviour, not a "

                "confirmed charger fault."

            ),



        "sessions":

            results

    }





# ============================================================

# DEMAND FORECAST

# ============================================================



@app.get("/api/forecast")

def forecast(

    date: str = "2019-12-30"

):



    try:



        target_date = pd.Timestamp(

            date

        ).normalize()



    except Exception:



        raise HTTPException(

            status_code=400,

            detail="Invalid date."

        )



    features = build_forecast_features(

        target_date

    )



    prediction = float(

        forecast_model.predict(

            features

        )[0]

    )



    actual_row = daily_history[

        daily_history["date"]

        == target_date

    ]



    actual = None



    if not actual_row.empty:



        actual = round(

            float(

                actual_row.iloc[0][

                    "daily_energy_kwh"

                ]

            ),

            2

        )



    return {



        "date":

            target_date.strftime(

                "%Y-%m-%d"

            ),



        "predicted_energy_kwh":

            round(prediction, 2),



        "actual_energy_kwh":

            actual,



        "model":

            model_metadata[

                "model_name"

            ],



        "features": {

            key:

                round(float(value), 2)

            for key, value

            in features.iloc[0].items()

        },



        "model_performance": {



            "mae_kwh":

                model_metadata[

                    "mae_kwh"

                ],



            "rmse_kwh":

                model_metadata[

                    "rmse_kwh"

                ],



            "r2":

                model_metadata[

                    "r2"

                ]

        },



        "note":

            (

                "Prediction represents "

                "daily session-associated "

                "energy demand, not exact "

                "meter-measured site load."

            )

    }





# ============================================================

# ANALYTICS

# ============================================================



@app.get("/api/analytics")

def analytics():



    weekday_energy = (

        df

        .assign(

            day_name=

                df[

                    "connectionTime_local"

                ].dt.day_name()

        )

        .groupby(

            "day_name"

        )["kWhDelivered"]

        .mean()

        .round(2)

        .to_dict()

    )



    top_chargers = (

        df

        .groupby("stationID")

        .agg(

            sessions=(

                "sessionID",

                "count"

            ),

            total_energy_kwh=(

                "kWhDelivered",

                "sum"

            )

        )

        .sort_values(

            "sessions",

            ascending=False

        )

        .head(10)

        .reset_index()

    )



    top_charger_records = []



    for _, row in top_chargers.iterrows():



        top_charger_records.append({



            "stationID":

                row["stationID"],



            "sessions":

                int(row["sessions"]),



            "total_energy_kwh":

                round(

                    float(

                        row[

                            "total_energy_kwh"

                        ]

                    ),

                    2

                )

        })



    return {



        "average_session_energy_kwh":

            round(

                float(

                    df[

                        "kWhDelivered"

                    ].mean()

                ),

                2

            ),



        "average_connected_hours":

            round(

                float(

                    df[

                        "connected_hours"

                    ].mean()

                ),

                2

            ),



        "average_charging_hours":

            round(

                float(

                    df[

                        "charging_hours"

                    ].mean()

                ),

                2

            ),



        "average_idle_hours":

            round(

                float(

                    df[

                        "idle_hours"

                    ].mean()

                ),

                2

            ),



        "average_energy_by_weekday":

            weekday_energy,



        "top_chargers":

            top_charger_records

    }

# ============================================================

# GROUNDED LOCAL GENAI / LLM INSIGHTS

# Ollama + Qwen3 1.7B

# ============================================================



import json

import urllib.request

import urllib.error



from pydantic import BaseModel





OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

OLLAMA_MODEL = "qwen3:1.7b"





class AIInsightRequest(BaseModel):

    question: str

    replay_time: str = "2019-01-08 10:30:00"

    forecast_date: str = "2019-12-30"





def call_local_llm(system_prompt, user_prompt):



    payload = {

        "model": OLLAMA_MODEL,



        "messages": [

            {

                "role": "system",

                "content": system_prompt

            },

            {

                "role": "user",

                "content": user_prompt

            }

        ],



        # We need one complete JSON response.

        "stream": False,



        # Qwen3 normally spends tokens on internal thinking.

        # For this dashboard we want a fast, concise operator answer.

        "think": False,



        # Conservative settings for an 8 GB RAM laptop.

        "options": {

            "temperature": 0.1,

            "num_ctx": 3072,

            "num_predict": 300

        },



        # Unload soon after use to release RAM.

        "keep_alive": "1m"

    }



    request_data = json.dumps(payload).encode("utf-8")



    request = urllib.request.Request(

        OLLAMA_URL,

        data=request_data,

        headers={

            "Content-Type": "application/json"

        },

        method="POST"

    )



    try:



        with urllib.request.urlopen(

            request,

            timeout=180

        ) as response:



            result = json.loads(

                response.read().decode("utf-8")

            )



    except urllib.error.URLError as exc:



        raise HTTPException(

            status_code=503,

            detail=(

                "Local LLM is unavailable. "

                "Make sure Ollama is installed and running. "

                f"Technical detail: {str(exc)}"

            )

        )



    except TimeoutError:



        raise HTTPException(

            status_code=504,

            detail="The local LLM took too long to respond."

        )



    except Exception as exc:



        raise HTTPException(

            status_code=500,

            detail=(

                "Local LLM request failed: "

                f"{str(exc)}"

            )

        )



    try:



        answer = result["message"]["content"].strip()



        if not answer:

            raise HTTPException(

                status_code=500,

                detail=(

                    "The local LLM completed the request "

                    "but returned an empty answer."

                )

            )



        return answer



    except HTTPException:

        raise



    except Exception:



        raise HTTPException(

            status_code=500,

            detail="Ollama returned an unexpected response."

        )







def build_verified_derived_facts(twin_data, analytics_data, forecast_data):
    """
    Compute deterministic relationships in Python before the LLM sees them.

    These facts prevent the language model from making unsupported comparative
    claims from the same numbers (for example, saying that most connected time
    is spent charging when average idle time is actually greater).
    """

    connected = float(analytics_data["average_connected_hours"])
    charging = float(analytics_data["average_charging_hours"])
    idle = float(analytics_data["average_idle_hours"])

    if idle > charging:
        duration_relationship = "idle_exceeds_charging"
        duration_interpretation = (
            f"Average connected-idle duration ({idle:.2f} h) is greater than "
            f"average active-charging duration ({charging:.2f} h) by "
            f"{idle - charging:.2f} h per session."
        )
    elif charging > idle:
        duration_relationship = "charging_exceeds_idle"
        duration_interpretation = (
            f"Average active-charging duration ({charging:.2f} h) is greater "
            f"than average connected-idle duration ({idle:.2f} h) by "
            f"{charging - idle:.2f} h per session."
        )
    else:
        duration_relationship = "charging_equals_idle"
        duration_interpretation = (
            f"Average active-charging and connected-idle durations are both "
            f"{charging:.2f} h per session."
        )

    charging_share = (
        round(charging / connected * 100, 1)
        if connected > 0
        else None
    )

    idle_share = (
        round(idle / connected * 100, 1)
        if connected > 0
        else None
    )

    charging_time_majority = bool(
        connected > 0
        and charging > idle
        and charging / connected > 0.5
    )

    predicted = forecast_data.get("predicted_energy_kwh")
    actual = forecast_data.get("actual_energy_kwh")

    forecast_comparison = None

    if predicted is not None and actual is not None:
        predicted = float(predicted)
        actual = float(actual)
        difference = round(predicted - actual, 2)

        if difference > 0:
            direction = "prediction_above_observed"
            explanation = (
                f"The forecast is {abs(difference):.2f} kWh above the "
                f"observed session-associated energy for the selected date."
            )
        elif difference < 0:
            direction = "prediction_below_observed"
            explanation = (
                f"The forecast is {abs(difference):.2f} kWh below the "
                f"observed session-associated energy for the selected date."
            )
        else:
            direction = "prediction_equals_observed"
            explanation = (
                "The forecast equals the observed session-associated energy "
                "for the selected date."
            )

        forecast_comparison = {
            "direction": direction,
            "absolute_difference_kwh": abs(difference),
            "interpretation": explanation,
        }

    return {
        "average_connected_hours": connected,
        "average_charging_hours": charging,
        "average_idle_hours": idle,
        "duration_relationship": duration_relationship,
        "duration_interpretation": duration_interpretation,
        "charging_share_of_connected_time_percent": charging_share,
        "idle_share_of_connected_time_percent": idle_share,
        "charging_time_majority": charging_time_majority,
        "replay_utilization_percent":
            float(twin_data["summary"]["utilization_percent"]),
        "replay_utilization_definition":
            "occupied EVSE divided by total EVSE at the selected historical replay timestamp",
        "top_charger_ranking_basis":
            "session count; the historical_analytics.top_chargers list is sorted by sessions, not by total energy",
        "forecast_comparison":
            forecast_comparison,
    }


def enforce_grounding_guardrails(answer, verified_facts):
    """
    Final deterministic check for a known comparative failure mode.

    The LLM still writes the natural-language response, but if it contradicts
    a fact already computed by Python, this layer removes the contradictory
    sentence and inserts the correct relationship.
    """

    cleaned = answer.strip()

    if not verified_facts["charging_time_majority"]:
        bad_patterns = [
            (
                r"(?im)^[^\n.!?]*(?:majority|most)[^\n.!?]*"
                r"(?:charging|charged|active charging)[^\n.!?]*[.!?]?\s*$"
            ),
            (
                r"(?im)^[^\n.!?]*more time[^\n.!?]*"
                r"(?:charging|charged)[^\n.!?]*than[^\n.!?]*idle"
                r"[^\n.!?]*[.!?]?\s*$"
            ),
        ]

        original = cleaned

        for pattern in bad_patterns:
            cleaned = re.sub(pattern, "", cleaned)

        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        if cleaned != original:
            correction = verified_facts["duration_interpretation"]

            if cleaned:
                cleaned = (
                    f"{cleaned}\n\n"
                    f"**Verified duration interpretation:** {correction}"
                )
            else:
                cleaned = (
                    f"**Verified duration interpretation:** {correction}"
                )

    return cleaned


@app.post("/api/ai/insights")
def ai_insights(request: AIInsightRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    # ========================================================
    # GROUNDING CONTEXT
    #
    # These values come from OUR existing backend:
    #
    # 1. Digital Twin state engine
    # 2. Gradient Boosting forecast model
    # 3. Isolation Forest anomaly detector
    # 4. Historical analytics
    # 5. Station summary
    # 6. Deterministic Python-derived relationships
    #
    # The LLM does NOT generate these numbers.
    # ========================================================

    try:
        twin_data = digital_twin(
            replay_time=request.replay_time
        )

        forecast_data = forecast(
            date=request.forecast_date
        )

        anomaly_data = anomalies(
            limit=8
        )

        analytics_data = analytics()

        station_data = station_summary()

        verified_facts = build_verified_derived_facts(
            twin_data=twin_data,
            analytics_data=analytics_data,
            forecast_data=forecast_data,
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not build grounded system context: "
                f"{str(exc)}"
            )
        )

    # --------------------------------------------------------
    # Reduce digital-twin context size.
    #
    # Sending all 54 full charger records to a small local LLM
    # wastes context and memory. We send:
    #
    # - complete station-level state summary
    # - only currently occupied/warning charger records
    # --------------------------------------------------------

    relevant_chargers = [
        charger
        for charger in twin_data["chargers"]
        if (
            charger["state"] != "Available"
            or charger["anomaly_warning"]
        )
    ]

    context = {
        "station": {
            "name": station_data["site"],
            "analyzed_sessions":
                station_data["sessions"],
            "total_chargers":
                station_data["chargers"],
            "total_session_energy_kwh":
                station_data["total_energy_kwh"],
            "detected_unusual_sessions":
                station_data["anomalous_sessions"],
        },

        "historical_replay": {
            "replay_time":
                twin_data["replay_time"],
            "station_state":
                twin_data["summary"],
            "occupied_or_warning_chargers":
                relevant_chargers,
        },

        "demand_forecast":
            forecast_data,

        "unusual_sessions": {
            "method":
                anomaly_data["method"],
            "total_detected":
                anomaly_data["total_anomalies"],
            "important_note":
                anomaly_data["note"],
            "top_sessions":
                anomaly_data["sessions"],
        },

        "historical_analytics":
            analytics_data,

        "verified_derived_facts":
            verified_facts,
    }

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    system_prompt = """
You are the grounded AI decision-support assistant inside an
EV Charging Station Digital Twin project.

The system represents the Caltech ACN charging station using
historical charging-session data.

You receive structured context produced by the project's actual
data-processing pipeline, machine-learning models, anomaly
detector, analytics layer, historical digital-twin state engine,
and deterministic Python calculations.

Your job is to explain and interpret that supplied information
for an EV charging station operator.

STRICT GROUNDING RULES:

1. Use ONLY values and facts contained in the supplied SYSTEM
   CONTEXT when discussing this station.

2. Never invent charger states, energy values, utilization,
   anomaly scores, forecasts, model metrics, timestamps,
   session counts, causes, or operational events.

3. If the supplied context cannot answer the operator's question,
   clearly say that the available system data is insufficient.

4. The digital twin is a HISTORICAL STATE REPLAY reconstructed
   from charging-session timestamps.

   Never describe it as:
   - a live Caltech feed
   - real-time telemetry
   - live charger monitoring

5. Demand predictions come from the project's trained Gradient
   Boosting regression model.

6. Forecast values represent DAILY SESSION-ASSOCIATED ENERGY
   DEMAND based on session-start dates.

   They are NOT exact meter-measured site electrical load.

7. R-squared is a regression evaluation metric.
   Never call R-squared "accuracy".

8. Unusual sessions were identified using Isolation Forest.

   An anomaly means statistically unusual session behaviour.
   It does NOT prove:
   - charger failure
   - equipment damage
   - malicious activity
   - maintenance requirement

9. Do not claim this project performs predictive maintenance.

10. Distinguish clearly between:

    OBSERVED DATA:
    historical charging-session information.

    DIGITAL TWIN STATE:
    reconstructed historical charger states.

    ML FORECAST:
    predicted session-associated energy demand.

    ANOMALY DETECTION:
    statistically unusual sessions.

    AI INTERPRETATION:
    your natural-language explanation of those results.

11. Do not make causal claims unless the supplied data directly
    supports them.

    Do not invent explanations involving weather, holidays,
    vacations, equipment faults, user behaviour, traffic,
    maintenance, or any other external cause unless the context
    explicitly contains that evidence.

12. Be concise and professional.

13. Prefer specific supplied numbers when they help answer the
    question.

14. When identifying an operational concern, explain which
    supplied measurement or anomaly result caused you to flag it.

15. Do not present yourself as the forecasting model or anomaly
    detector. You are the natural-language interpretation layer
    above those components.

16. VERIFIED_DERIVED_FACTS are calculated deterministically by
    Python before you receive the context. Treat them as
    authoritative. Do not contradict them or independently
    reinterpret the same numbers in a different way.

17. Before making ANY comparison involving average connected,
    charging, or idle duration, read:
    verified_derived_facts.duration_relationship
    verified_derived_facts.duration_interpretation
    verified_derived_facts.charging_time_majority

18. If charging_time_majority is false, you MUST NOT say or imply:
    - a majority of connected time is spent charging
    - most connected time is spent charging
    - more time is spent charging than idle
    - charging dominates connected time

    Instead, use the supplied duration_interpretation or an
    equivalent statement.

19. Do NOT infer current station utilization from average session
    durations. Current utilization comes ONLY from:
    historical_replay.station_state.utilization_percent

20. Do not describe utilization as "high", "low", "busy",
    "underused", "heavy", or "light" unless the context supplies a
    threshold that defines that label. Prefer the exact percentage.

21. The historical_analytics.top_chargers list is ranked by
    SESSION COUNT. Do not call it a ranking by total energy unless
    the context explicitly says the ranking basis is total energy.

22. When forecast and observed energy are both available, use
    verified_derived_facts.forecast_comparison for the direction
    and absolute difference. Do not invent a reason for the error.

23. For a general station-summary question, prioritize:
    - replay timestamp and EVSE state counts/utilization
    - anomaly warnings/unusual-session evidence
    - selected-date forecast and observed value if available
    - one concise historical-duration observation
    Avoid unnecessary long tables unless the operator asks for one.

24. Silently check every sentence containing comparative words
    such as "more", "less", "majority", "most", "higher", "lower",
    "dominant", or "largest" against the supplied context before
    returning the final answer.
"""

    # ========================================================
    # USER PROMPT
    # ========================================================

    user_prompt = f"""
SYSTEM CONTEXT

{json.dumps(context, indent=2, default=str)}

OPERATOR QUESTION

{question}

Answer the operator's question using only the supplied system
context.

The VERIFIED_DERIVED_FACTS block is authoritative. If your own
language conflicts with it, correct your wording before answering.
"""

    # ========================================================
    # LOCAL LLM
    # ========================================================

    answer = call_local_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    # Deterministic final check for the known comparative failure
    # mode. This keeps the LLM as the interpretation layer while
    # preventing it from contradicting backend-computed facts.
    answer = enforce_grounding_guardrails(
        answer=answer,
        verified_facts=verified_facts,
    )

    return {
        "question":
            question,

        "answer":
            answer,

        "grounded":
            True,

        "llm_provider":
            "Ollama (Local)",

        "llm_model":
            OLLAMA_MODEL,

        "replay_time":
            request.replay_time,

        "forecast_date":
            request.forecast_date,

        "context_sources": [
            "station_summary",
            "digital_twin_historical_replay",
            "gradient_boosting_forecast",
            "isolation_forest_anomalies",
            "historical_analytics",
            "verified_python_derived_facts",
        ],

        "verified_facts":
            verified_facts,

        "limitations": [
            (
                "Historical replay is not a live "
                "Caltech charger feed."
            ),
            (
                "Forecast represents session-associated "
                "energy demand, not exact meter load."
            ),
            (
                "Detected anomalies are unusual sessions, "
                "not confirmed equipment faults."
            ),
        ],
    }


# ============================================================

# SQLITE DATABASE API

# ============================================================



from database import (

    initialize_database,

    get_connection,

    get_database_summary,

    get_top_chargers

)





# Initialize persistent SQLite storage when backend starts.

initialize_database()





@app.get("/api/database/summary")

def database_summary():



    connection = get_connection()



    try:

        summary = get_database_summary(connection)



        return {

            "database": "SQLite",

            "table": "charging_sessions",

            "source": "ACN Caltech 2019 processed sessions",

            **summary

        }



    finally:

        connection.close()





@app.get("/api/database/top-chargers")

def database_top_chargers(limit: int = 10):



    # Prevent accidentally requesting a huge result.

    limit = max(1, min(limit, 54))



    connection = get_connection()



    try:

        chargers = get_top_chargers(

            connection,

            limit=limit

        )



        return {

            "database": "SQLite",

            "query_type": "GROUP BY station_id",

            "count": len(chargers),

            "chargers": chargers

        }



    finally:

        connection.close()