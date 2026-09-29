import { useEffect, useMemo, useState } from "react";

import {

  Activity,

  AlertTriangle,

  BarChart3,

  BatteryCharging,

  BrainCircuit,

  ChevronRight,

  Clock3,

  Database,

  Gauge,

  History,

  PlugZap,

  RefreshCw,

  Send,

  Server,

  Zap,

} from "lucide-react";



import "./App.css";



const API = "http://127.0.0.1:8000";

const AI_GROUNDING_RULES = `STRICT INTERPRETATION RULES:
- Use only values supplied by the EV Digital Twin backend context. If evidence is missing, explicitly say the context is insufficient.
- Historical replay is reconstructed from 2019 session timestamps; never describe it as live or real-time telemetry.
- Session-duration averages do not measure overall station utilization. Never infer site utilization from average connected, charging or idle duration.
- Compare connected, charging and idle durations numerically. Only say a majority of connected time is spent charging when charging time is greater than half of connected time AND greater than idle time.
- If average idle time exceeds average charging time, state that sessions spend slightly more connected time idle than actively charging on average.
- The forecast is daily session-associated energy based on session-start dates, not exact meter-measured site load.
- R² is a regression goodness-of-fit metric, not model accuracy.
- Isolation Forest flags statistically unusual sessions. Never call them confirmed charger faults, failures, malicious activity, predictive-maintenance findings or maintenance diagnoses.
- Top-charger statistics are historical aggregates, not current live rankings.
- The LLM interprets backend outputs; it does not generate measurements, forecasts or anomaly scores.
- Do not invent causes, measurements, probabilities or operational conclusions unsupported by the supplied numbers.`;



function App() {

  const [summary, setSummary] = useState(null);

  const [twin, setTwin] = useState(null);

  const [forecast, setForecast] = useState(null);

  const [anomalies, setAnomalies] = useState(null);

  const [analytics, setAnalytics] = useState(null);

  const [database, setDatabase] = useState(null);



  const [replayTime, setReplayTime] = useState("2019-01-08T10:30");

  const [forecastDate, setForecastDate] = useState("2019-12-30");



  const [selectedCharger, setSelectedCharger] = useState(null);



  const [aiQuestion, setAiQuestion] = useState(

    "Summarize the charging station status and identify any operational concerns."

  );

  const [aiAnswer, setAiAnswer] = useState("");

  const [aiLoading, setAiLoading] = useState(false);

  const [aiError, setAiError] = useState("");



  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");



  async function getJSON(url, options = undefined) {

    const response = await fetch(url, options);



    if (!response.ok) {

      let detail = `${response.status} ${response.statusText}`;



      try {

        const body = await response.json();

        detail = body.detail || detail;

      } catch {

        // Keep HTTP status text.

      }



      throw new Error(detail);

    }



    return response.json();

  }



  async function loadDashboard() {

    try {

      setLoading(true);

      setError("");



      const [

        summaryData,

        twinData,

        forecastData,

        anomalyData,

        analyticsData,

        databaseData,

      ] = await Promise.all([

        getJSON(`${API}/api/station/summary`),



        getJSON(

          `${API}/api/twin?replay_time=${encodeURIComponent(

            replayTime.replace("T", " ")

          )}`

        ),



        getJSON(`${API}/api/forecast?date=${forecastDate}`),



        getJSON(`${API}/api/anomalies?limit=8`),



        getJSON(`${API}/api/analytics`),



        getJSON(`${API}/api/database/summary`),

      ]);



      setSummary(summaryData);

      setTwin(twinData);

      setForecast(forecastData);

      setAnomalies(anomalyData);

      setAnalytics(analyticsData);

      setDatabase(databaseData);



      setSelectedCharger((current) => {

        if (!current) {

          return (

            twinData.chargers.find((charger) => charger.anomaly_warning) ||

            twinData.chargers.find((charger) => charger.state === "Charging") ||

            twinData.chargers[0]

          );

        }



        return (

          twinData.chargers.find(

            (charger) => charger.stationID === current.stationID

          ) || twinData.chargers[0]

        );

      });

    } catch (err) {

      console.error(err);

      setError(

        "Could not connect to the EV Digital Twin backend. Confirm FastAPI is running on port 8000."

      );

    } finally {

      setLoading(false);

    }

  }



  async function askAI(event) {

    event?.preventDefault();

    const question = aiQuestion.trim();

    if (!question) return;

    try {
      setAiLoading(true);
      setAiError("");

      const durationCrossCheck = analytics
        ? `Current duration cross-check from backend analytics: average connected ${analytics.average_connected_hours} h, average active charging ${analytics.average_charging_hours} h, average connected idle ${analytics.average_idle_hours} h.`
        : "";

      const groundedQuestion = [
        question,
        AI_GROUNDING_RULES,
        durationCrossCheck,
      ]
        .filter(Boolean)
        .join("\n\n");

      const result = await getJSON(`${API}/api/ai/insights`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: groundedQuestion,
          replay_time: replayTime.replace("T", " "),
          forecast_date: forecastDate,
        }),
      });

      setAiAnswer(result.answer || "No response was returned.");
    } catch (err) {
      console.error(err);
      setAiError(
        `Local AI request failed: ${err.message}. Confirm Ollama is running and qwen3:1.7b is available.`
      );
    } finally {
      setAiLoading(false);
    }
  }

  useEffect(() => {

    loadDashboard();

  }, []);



  const stateCounts = twin?.summary || {};



  const anomalyRate =

    summary && summary.sessions

      ? ((summary.anomalous_sessions / summary.sessions) * 100).toFixed(1)

      : "0.0";



  const selectedSessionAnomaly = useMemo(() => {

    if (!selectedCharger || !anomalies?.sessions) return null;



    return anomalies.sessions.find(

      (row) => row.stationID === selectedCharger.stationID

    );

  }, [selectedCharger, anomalies]);



  function stateKey(charger) {

    if (charger.anomaly_warning) return "warning";

    if (charger.state === "Charging") return "charging";

    if (charger.state === "Connected / Idle") return "idle";

    return "available";

  }



  function stateLabel(charger) {

    if (charger.anomaly_warning) return "Anomaly warning";

    return charger.state;

  }



  if (loading) {

    return (

      <div className="center-screen">

        <RefreshCw className="spin" size={30} />

        <h2>Loading charging operations...</h2>

        <p>Retrieving digital-twin, ML and SQL data from FastAPI.</p>

      </div>

    );

  }



  if (error) {

    return (

      <div className="center-screen">

        <AlertTriangle size={38} />

        <h2>Backend connection unavailable</h2>

        <p>{error}</p>

        <button onClick={loadDashboard}>Retry connection</button>

      </div>

    );

  }



  return (

    <div className="app-shell">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">

            <PlugZap size={20} />

          </div>



          <div>

            <strong>EV Station DT</strong>

            <span>Engineering Operations</span>

          </div>

        </div>



        <div className="site-block">

          <span className="site-label">ACTIVE SITE</span>

          <strong>Caltech ACN</strong>

          <small>Historical operations dataset</small>

        </div>



        <nav className="side-nav">

          <a href="#operations" className="active">

            <Gauge size={16} />

            Operations

          </a>



          <a href="#twin">

            <BatteryCharging size={16} />

            Digital Twin

          </a>



          <a href="#forecast">

            <Activity size={16} />

            Demand Forecast

          </a>



          <a href="#events">

            <AlertTriangle size={16} />

            Anomaly Events

          </a>



          <a href="#assistant">

            <BrainCircuit size={16} />

            Operations Assistant

          </a>

        </nav>



        <div className="sidebar-system">

          <div className="status-row">

            <span className="status-indicator online" />

            <div>

              <strong>Backend connected</strong>

              <small>FastAPI · SQLite · ML</small>

            </div>

          </div>



          <div className="status-row">

            <span className="status-indicator local" />

            <div>

              <strong>Local GenAI</strong>

              <small>Ollama · Qwen3 1.7B</small>

            </div>

          </div>

        </div>

      </aside>



      <main className="workspace">

        <header className="operations-header" id="operations">

          <div>

            <div className="breadcrumb">

              Charging Operations

              <ChevronRight size={13} />

              Caltech ACN

            </div>



            <h1>Charging Operations</h1>



            <p>

              Historical EVSE state reconstruction, demand forecasting and

              anomaly intelligence.

            </p>

          </div>



          <div className="header-status">

            <div className="header-status-line">

              <Server size={14} />

              SYSTEM CONNECTED

            </div>



            <span>Historical replay · not live telemetry</span>

          </div>

        </header>



        <section className="operations-strip">

          <div className="replay-context">

            <History size={17} />



            <div>

              <span>REPLAY TIMESTAMP</span>

              <strong>{replayTime.replace("T", " ")}</strong>

            </div>

          </div>



          <OperationalStat

            label="EVSE"

            value={stateCounts.total_chargers}

          />



          <OperationalStat

            label="Charging"

            value={stateCounts.charging}

            status="charging"

          />



          <OperationalStat

            label="Connected / Idle"

            value={stateCounts.connected_idle}

            status="idle"

          />



          <OperationalStat

            label="Available"

            value={stateCounts.available}

            status="available"

          />



          <OperationalStat

            label="Warnings"

            value={stateCounts.anomaly_warnings}

            status="warning"

          />

        </section>



        <section className="kpi-grid">

          <KPI

            label="Station utilization"

            value={`${stateCounts.utilization_percent}%`}

            detail={`${stateCounts.occupied} of ${stateCounts.total_chargers} EVSE occupied`}

          />



          <KPI

            label="Actively charging"

            value={`${stateCounts.actively_charging_percent}%`}

            detail={`${stateCounts.charging} EVSE delivering charge`}

          />



          <KPI

            label="Analyzed sessions"

            value={summary.sessions.toLocaleString()}

            detail="Valid analytical session subset"

          />



          <KPI

            label="Session energy"

            value={`${summary.total_energy_kwh.toLocaleString()} kWh`}

            detail="Analyzed historical sessions"

          />

        </section>



        <section id="twin" className="section-block twin-section">

          <div className="section-title-row">

            <div>

              <span className="section-kicker">DIGITAL TWIN</span>

              <h2>EVSE State Reconstruction</h2>

              <p>

                Charger states reconstructed from historical connection,

                charging-completion and disconnection timestamps.

              </p>

            </div>



            <div className="replay-controls">

              <label>

                Replay time

                <input

                  type="datetime-local"

                  value={replayTime}

                  onChange={(event) => setReplayTime(event.target.value)}

                />

              </label>



              <button onClick={loadDashboard}>

                <RefreshCw size={15} />

                Apply replay

              </button>

            </div>

          </div>



          <div className="twin-workspace">

            <div className="station-canvas">

              <div className="canvas-toolbar">

                <div className="legend">

                  <LegendItem status="available" label="Available" />

                  <LegendItem status="charging" label="Charging" />

                  <LegendItem status="idle" label="Connected / Idle" />

                  <LegendItem status="warning" label="Anomaly warning" />

                </div>



                <span>{twin.chargers.length} EVSE mapped</span>

              </div>



              <div className="facility-label">

                <span>CALTECH ACN · EV CHARGING AREA</span>

                <small>Historical state replay</small>

              </div>



              <div className="facility-roadway" aria-hidden="true">
                <span>VEHICLE AISLE / ACCESS</span>
                <span>54 EVSE PARKING BAYS</span>
              </div>

              <div className="charging-bays">

                {twin.chargers.map((charger, index) => {

                  const status = stateKey(charger);

                  const selected =

                    selectedCharger?.stationID === charger.stationID;



                  return (

                    <button

                      type="button"

                      key={charger.stationID}

                      className={`evse-bay ${status} ${

                        selected ? "selected" : ""

                      }`}

                      onClick={() => setSelectedCharger(charger)}

                    >

                      <span className="bay-number">

                        EVSE {String(index + 1).padStart(2, "0")}

                      </span>



                      <span className="bay-icon">

                        <PlugZap size={17} />

                      </span>



                      <strong>

                        {charger.stationID.split("-").slice(-1)[0]}

                      </strong>



                      <small>{stateLabel(charger)}</small>

                    </button>

                  );

                })}

              </div>

            </div>



            <aside className="engineering-panel">

              <div className="engineering-heading">

                <div>

                  <span>SELECTED ASSET</span>

                  <h3>{selectedCharger?.stationID || "No EVSE selected"}</h3>

                </div>



                {selectedCharger && (

                  <StateBadge

                    status={stateKey(selectedCharger)}

                    label={stateLabel(selectedCharger)}

                  />

                )}

              </div>



              {selectedCharger && (

                <>

                  <EngineeringRow

                    label="Operational state"

                    value={selectedCharger.state}

                  />



                  <EngineeringRow

                    label="Session energy"

                    value={

                      selectedCharger.session_energy_kwh == null

                        ? "No active session"

                        : `${selectedCharger.session_energy_kwh} kWh`

                    }

                  />



                  <EngineeringRow

                    label="Anomaly warning"

                    value={selectedCharger.anomaly_warning ? "Active" : "None"}

                    warning={selectedCharger.anomaly_warning}

                  />



                  <EngineeringRow

                    label="Anomaly score"

                    value={

                      selectedCharger.anomaly_score == null

                        ? "—"

                        : selectedCharger.anomaly_score

                    }

                  />



                  {selectedSessionAnomaly && (

                    <div className="asset-event">

                      <AlertTriangle size={16} />



                      <div>

                        <strong>Unusual session identified</strong>

                        <p>

                          {selectedSessionAnomaly.connected_hours} h connected ·{" "}

                          {selectedSessionAnomaly.charging_hours} h charging ·{" "}

                          {selectedSessionAnomaly.idle_hours} h idle

                        </p>

                      </div>

                    </div>

                  )}



                  <div className="asset-note">

                    Asset state is reconstructed from historical session

                    timestamps and is not live charger telemetry.

                  </div>

                </>

              )}

            </aside>

          </div>

        </section>



        <div className="analysis-grid">

          <section id="forecast" className="section-block">

            <div className="section-title-row compact">

              <div>

                <span className="section-kicker">DEMAND FORECASTING</span>

                <h2>Daily Energy Forecast</h2>

                <p>Gradient Boosting regression model</p>

              </div>



              <BarChart3 size={20} />

            </div>



            <div className="forecast-input-row">

              <label>

                Forecast date

                <input

                  type="date"

                  value={forecastDate}

                  min="2019-01-08"

                  max="2019-12-30"

                  onChange={(event) => setForecastDate(event.target.value)}

                />

              </label>



              <button onClick={loadDashboard}>Run forecast</button>

            </div>



            <div className="forecast-primary">

              <span>PREDICTED SESSION-ASSOCIATED ENERGY</span>



              <div>

                <strong>{forecast.predicted_energy_kwh}</strong>

                <small>kWh</small>

              </div>

            </div>



            <div className="forecast-comparison">

              <DataPair

                label="Observed"

                value={

                  forecast.actual_energy_kwh == null

                    ? "N/A"

                    : `${forecast.actual_energy_kwh} kWh`

                }

              />



              <DataPair

                label="Model"

                value="Gradient Boosting"

              />

            </div>



            <div className="model-metrics">

              <ModelMetric

                label="MAE"

                value={`${forecast.model_performance.mae_kwh} kWh`}

              />



              <ModelMetric

                label="RMSE"

                value={`${forecast.model_performance.rmse_kwh} kWh`}

              />



              <ModelMetric

                label="R²"

                value={forecast.model_performance.r2}

              />

            </div>



            <p className="technical-note">

              Forecast represents daily session-associated energy demand based

              on session-start dates, not exact meter-measured site load.

            </p>

          </section>



          <section className="section-block">

            <div className="section-title-row compact">

              <div>

                <span className="section-kicker">SESSION ANALYTICS</span>

                <h2>Operational Statistics</h2>

                <p>Historical charging-session behaviour</p>

              </div>



              <Activity size={20} />

            </div>



            <div className="analytics-table">

              <DataRow

                label="Average session energy"

                value={`${analytics.average_session_energy_kwh} kWh`}

              />



              <DataRow

                label="Average connected duration"

                value={`${analytics.average_connected_hours} h`}

              />



              <DataRow

                label="Average active charging"

                value={`${analytics.average_charging_hours} h`}

              />



              <DataRow

                label="Average connected idle"

                value={`${analytics.average_idle_hours} h`}

              />



              <DataRow

                label="Unusual-session rate"

                value={`${anomalyRate}%`}

              />



              <DataRow

                label="Detected unusual sessions"

                value={summary.anomalous_sessions}

              />

            </div>



            <div className="operations-observation">

              <Clock3 size={17} />



              <div>

                <strong>Connection-time observation</strong>

                <p>

                  Average connection duration is{" "}

                  {analytics.average_connected_hours} h while average active

                  charging duration is {analytics.average_charging_hours} h,

                  leaving {analytics.average_idle_hours} h of connected idle

                  time on average.

                </p>

              </div>

            </div>

          </section>



          <section className="section-block database-panel">

            <div className="section-title-row compact">

              <div>

                <span className="section-kicker">DATA LAYER</span>

                <h2>SQLite Repository</h2>

                <p>Persistent processed-session storage</p>

              </div>



              <Database size={20} />

            </div>



            <div className="database-state">

              <div>

                <span>DATABASE</span>

                <strong>{database.database}</strong>

              </div>



              <div>

                <span>TABLE</span>

                <strong>{database.table}</strong>

              </div>

            </div>



            <div className="analytics-table">

              <DataRow

                label="Stored sessions"

                value={database.total_sessions?.toLocaleString()}

              />



              <DataRow

                label="Distinct chargers"

                value={database.total_chargers}

              />



              <DataRow

                label="Stored energy"

                value={`${database.total_energy_kwh?.toLocaleString()} kWh`}

              />



              <DataRow

                label="Average session energy"

                value={`${database.average_session_energy_kwh} kWh`}

              />

            </div>



            <p className="technical-note">

              Cleaned ACN sessions are persisted in SQLite and queried through

              FastAPI SQL-backed endpoints.

            </p>

          </section>

        </div>



        <section id="events" className="section-block">

          <div className="section-title-row">

            <div>

              <span className="section-kicker">ANOMALY INTELLIGENCE</span>

              <h2>Unusual Session Events</h2>

              <p>

                Isolation Forest results ranked by statistical unusualness.

              </p>

            </div>



            <div className="event-count">

              <AlertTriangle size={14} />

              {anomalies.total_anomalies} detected

            </div>

          </div>



          <div className="event-table-wrap">

            <table className="event-table">

              <thead>

                <tr>

                  <th>STATUS</th>

                  <th>EVSE ID</th>

                  <th>SESSION</th>

                  <th>ENERGY</th>

                  <th>CONNECTED</th>

                  <th>CHARGING</th>

                  <th>IDLE</th>

                  <th>ANOMALY SCORE</th>

                </tr>

              </thead>



              <tbody>

                {anomalies.sessions.map((row) => (

                  <tr key={row.sessionID}>

                    <td>

                      <span className="event-status">

                        <span />

                        Unusual

                      </span>

                    </td>



                    <td className="mono">{row.stationID}</td>



                    <td className="mono session-id">

                      {String(row.sessionID).slice(0, 12)}

                    </td>



                    <td>{row.energy_kwh} kWh</td>

                    <td>{row.connected_hours} h</td>

                    <td>{row.charging_hours} h</td>

                    <td>{row.idle_hours} h</td>

                    <td className="mono">{row.anomaly_score}</td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>



          <p className="technical-note">

            These are statistically unusual historical charging sessions. They

            are not confirmed charger faults or maintenance diagnoses.

          </p>

        </section>



        <section id="assistant" className="section-block assistant-section">

          <div className="section-title-row">

            <div>

              <span className="section-kicker">DECISION SUPPORT</span>

              <h2>Grounded Operations Assistant</h2>

              <p>

                Natural-language interpretation of actual digital-twin, ML,

                anomaly and analytics outputs.

              </p>

            </div>



            <div className="local-model">

              <span className="status-indicator local" />

              Ollama · Qwen3 1.7B

            </div>

          </div>



          <div className="assistant-layout">

            <div className="assistant-context">

              <span className="context-heading">ACTIVE CONTEXT</span>



              <ContextRow

                label="Replay"

                value={replayTime.replace("T", " ")}

              />



              <ContextRow

                label="Forecast date"

                value={forecastDate}

              />



              <ContextRow

                label="Charging"

                value={`${stateCounts.charging} EVSE`}

              />



              <ContextRow

                label="Warnings"

                value={stateCounts.anomaly_warnings}

              />



              <ContextRow

                label="Forecast"

                value={`${forecast.predicted_energy_kwh} kWh`}

              />

              <ContextRow

                label="Avg charging"

                value={`${analytics.average_charging_hours} h`}

              />

              <ContextRow

                label="Avg idle"

                value={`${analytics.average_idle_hours} h`}

              />



              <div className="grounding-note">

                <BrainCircuit size={16} />

                <p>

                  The LLM receives structured context from the backend. It does

                  not generate station measurements or ML predictions itself.

                </p>

              </div>

            </div>



            <div className="assistant-console">

              <div className="console-header">

                <div>

                  <span className="console-dot" />

                  LOCAL ANALYSIS CONSOLE

                </div>



                <small>Grounded response</small>

              </div>



              <div className="assistant-response">

                {aiLoading ? (

                  <div className="ai-working">

                    <RefreshCw className="spin" size={18} />

                    Qwen is interpreting the current system context...

                  </div>

                ) : aiError ? (

                  <div className="ai-error">

                    <AlertTriangle size={17} />

                    {aiError}

                  </div>

                ) : aiAnswer ? (

                  <MarkdownResponse text={aiAnswer} />

                ) : (

                  <div className="assistant-empty">

                    <BrainCircuit size={26} />

                    <strong>Ask about the current replay state</strong>

                    <span>

                      The assistant can interpret the forecast, station state,

                      analytics and unusual-session results.

                    </span>

                  </div>

                )}

              </div>



              <form className="assistant-input" onSubmit={askAI}>

                <textarea

                  value={aiQuestion}

                  onChange={(event) => setAiQuestion(event.target.value)}

                  rows={3}

                  placeholder="Ask an operational question..."

                />



                <button type="submit" disabled={aiLoading}>

                  <Send size={15} />

                  {aiLoading ? "Analyzing..." : "Ask assistant"}

                </button>

              </form>



              <div className="quick-prompts">

                <button

                  type="button"

                  onClick={() =>

                    setAiQuestion(

                      "Summarize the charging station status and identify any operational concerns."

                    )

                  }

                >

                  Summarize station

                </button>



                <button

                  type="button"

                  onClick={() =>

                    setAiQuestion(

                      "Explain the demand forecast and compare it with the observed energy for the selected date."

                    )

                  }

                >

                  Explain forecast

                </button>



                <button

                  type="button"

                  onClick={() =>

                    setAiQuestion(

                      "Which unusual charging sessions should an operator review first, and why?"

                    )

                  }

                >

                  Review anomalies

                </button>

              </div>

            </div>

          </div>

        </section>



        <footer className="footer">

          <span>EV Charging Station Digital Twin</span>

          <span>Caltech ACN 2019 · Historical replay</span>

          <span>FastAPI · SQLite · ML · Ollama</span>

        </footer>

      </main>

    </div>

  );

}



function OperationalStat({ label, value, status }) {

  return (

    <div className="operational-stat">

      <span className={`status-indicator ${status || "neutral"}`} />

      <div>

        <span>{label}</span>

        <strong>{value}</strong>

      </div>

    </div>

  );

}



function KPI({ label, value, detail }) {

  return (

    <div className="kpi">

      <span>{label}</span>

      <strong>{value}</strong>

      <small>{detail}</small>

    </div>

  );

}



function LegendItem({ status, label }) {

  return (

    <span className="legend-item">

      <span className={`status-indicator ${status}`} />

      {label}

    </span>

  );

}



function StateBadge({ status, label }) {

  return (

    <span className={`state-badge ${status}`}>

      <span className={`status-indicator ${status}`} />

      {label}

    </span>

  );

}



function EngineeringRow({ label, value, warning = false }) {

  return (

    <div className="engineering-row">

      <span>{label}</span>

      <strong className={warning ? "warning-text" : ""}>{value}</strong>

    </div>

  );

}



function DataPair({ label, value }) {

  return (

    <div className="data-pair">

      <span>{label}</span>

      <strong>{value}</strong>

    </div>

  );

}



function ModelMetric({ label, value }) {

  return (

    <div className="model-metric">

      <span>{label}</span>

      <strong>{value}</strong>

    </div>

  );

}



function DataRow({ label, value }) {

  return (

    <div className="data-row">

      <span>{label}</span>

      <strong>{value}</strong>

    </div>

  );

}



function ContextRow({ label, value }) {

  return (

    <div className="context-row">

      <span>{label}</span>

      <strong>{value}</strong>

    </div>

  );

}



function ForecastBars({ predicted, observed }) {
  const p = Number(predicted) || 0;
  const o = observed == null ? null : Number(observed) || 0;
  const max = Math.max(p, o || 0, 1);

  return (
    <div className="forecast-bars" aria-label="Predicted and observed energy comparison">
      <div className="forecast-bar-row">
        <span>Predicted</span>
        <div className="forecast-track">
          <div className="forecast-fill predicted" style={{ width: `${(p / max) * 100}%` }} />
        </div>
        <strong>{p.toFixed(2)} kWh</strong>
      </div>

      <div className="forecast-bar-row">
        <span>Observed</span>
        <div className="forecast-track">
          <div
            className="forecast-fill observed"
            style={{ width: `${o == null ? 0 : (o / max) * 100}%` }}
          />
        </div>
        <strong>{o == null ? "N/A" : `${o.toFixed(2)} kWh`}</strong>
      </div>
    </div>
  );
}

function MarkdownResponse({ text }) {
  const lines = String(text || "").split(/\r?\n/);
  const blocks = [];
  let i = 0;

  const inline = (value) => {
    const parts = String(value).split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, index) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={index}>{part.slice(2, -2)}</strong>
      ) : (
        <span key={index}>{part}</span>
      )
    );
  };

  while (i < lines.length) {
    const line = lines[i].trim();

    if (!line) {
      i += 1;
      continue;
    }

    if (line.startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i].trim());
        i += 1;
      }
      const rows = tableLines
        .map((row) => row.split("|").slice(1, -1).map((cell) => cell.trim()))
        .filter((row) => !row.every((cell) => /^:?-{3,}:?$/.test(cell)));
      if (rows.length) {
        blocks.push(
          <div className="md-table-wrap" key={`table-${i}`}>
            <table className="md-table">
              <thead>
                <tr>{rows[0].map((cell, c) => <th key={c}>{inline(cell)}</th>)}</tr>
              </thead>
              <tbody>
                {rows.slice(1).map((row, r) => (
                  <tr key={r}>{row.map((cell, c) => <td key={c}>{inline(cell)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    if (/^#{1,4}\s+/.test(line)) {
      const level = line.match(/^#+/)[0].length;
      const content = line.replace(/^#{1,4}\s+/, "");
      const Tag = level <= 2 ? "h3" : "h4";
      blocks.push(<Tag className="md-heading" key={`h-${i}`}>{inline(content)}</Tag>);
      i += 1;
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ul className="md-list" key={`ul-${i}`}>
          {items.map((item, idx) => <li key={idx}>{inline(item)}</li>)}
        </ul>
      );
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ol className="md-list" key={`ol-${i}`}>
          {items.map((item, idx) => <li key={idx}>{inline(item)}</li>)}
        </ol>
      );
      continue;
    }

    blocks.push(<p className="md-paragraph" key={`p-${i}`}>{inline(line)}</p>);
    i += 1;
  }

  return <div className="markdown-response">{blocks}</div>;
}

export default App;