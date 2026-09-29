%% AI-Powered EV Charging Station Digital Twin
% MATLAB Engineering Scenario Simulation
%
% Purpose:
% Simulate station-level electrical demand under:
% 1. Normal Operation
% 2. Peak Demand
% 3. Abnormal Charger Behaviour
%
% This simulation complements the historical ACN-data digital twin.
% It is NOT measured Caltech power telemetry.

clear;
clc;
close all;

%% =========================================================
% STATION CONFIGURATION
% ==========================================================

numChargers = 54;

% Assumed Level-2 charger rated power for scenario simulation.
chargerRatedPower_kW = 7.2;

stationRatedPower_kW = ...
    numChargers * chargerRatedPower_kW;

fprintf('\n=============================================\n');
fprintf(' EV CHARGING STATION SCENARIO SIMULATION\n');
fprintf('=============================================\n');

fprintf('Number of chargers: %d\n', numChargers);
fprintf('Assumed charger rating: %.1f kW\n', ...
    chargerRatedPower_kW);

fprintf('Theoretical station capacity: %.1f kW\n\n', ...
    stationRatedPower_kW);


%% =========================================================
% TIME AXIS
% 24-hour simulation with 15-minute resolution
% ==========================================================

timeHours = 0:0.25:23.75;

numSteps = length(timeHours);


%% =========================================================
% NORMAL OPERATION
% ==========================================================

% Synthetic daily charging-demand profile.
% Morning and afternoon peaks are represented using
% Gaussian-shaped demand components.

morningPeak = ...
    115 * exp(-((timeHours - 9) / 2.2).^2);

afternoonPeak = ...
    85 * exp(-((timeHours - 15) / 3).^2);

baseLoad = 18;

normalDemand_kW = ...
    baseLoad + morningPeak + afternoonPeak;

normalDemand_kW = min( ...
    normalDemand_kW, ...
    stationRatedPower_kW);


%% =========================================================
% PEAK-DEMAND SCENARIO
% ==========================================================

peakDemand_kW = normalDemand_kW;

peakWindow = ...
    timeHours >= 8 & timeHours <= 11;

peakDemand_kW(peakWindow) = ...
    peakDemand_kW(peakWindow) * 1.45;

peakDemand_kW = min( ...
    peakDemand_kW, ...
    stationRatedPower_kW);


%% =========================================================
% ABNORMAL CHARGER SCENARIO
% ==========================================================

abnormalDemand_kW = normalDemand_kW;

% Simulated abnormal event:
% unexpected additional 45 kW demand between 14:00–16:00.

abnormalWindow = ...
    timeHours >= 14 & timeHours <= 16;

abnormalDemand_kW(abnormalWindow) = ...
    abnormalDemand_kW(abnormalWindow) + 45;

abnormalDemand_kW = min( ...
    abnormalDemand_kW, ...
    stationRatedPower_kW);


%% =========================================================
% ENGINEERING THRESHOLD
% ==========================================================

warningThreshold_kW = ...
    0.70 * stationRatedPower_kW;

normalWarnings = ...
    normalDemand_kW > warningThreshold_kW;

peakWarnings = ...
    peakDemand_kW > warningThreshold_kW;

abnormalWarnings = ...
    abnormalDemand_kW > warningThreshold_kW;


%% =========================================================
% ENERGY CALCULATION
% ==========================================================

timeStepHours = 0.25;

normalEnergy_kWh = ...
    sum(normalDemand_kW) * timeStepHours;

peakEnergy_kWh = ...
    sum(peakDemand_kW) * timeStepHours;

abnormalEnergy_kWh = ...
    sum(abnormalDemand_kW) * timeStepHours;


%% =========================================================
% PEAK POWER
% ==========================================================

normalPeak_kW = max(normalDemand_kW);

peakScenarioPeak_kW = max(peakDemand_kW);

abnormalPeak_kW = max(abnormalDemand_kW);


%% =========================================================
% UTILIZATION RELATIVE TO ASSUMED STATION CAPACITY
% ==========================================================

normalUtilization = ...
    100 * normalPeak_kW / stationRatedPower_kW;

peakUtilization = ...
    100 * peakScenarioPeak_kW / stationRatedPower_kW;

abnormalUtilization = ...
    100 * abnormalPeak_kW / stationRatedPower_kW;


%% =========================================================
% RESULTS TABLE
% ==========================================================

Scenario = [
    "Normal Operation"
    "Peak Demand"
    "Abnormal Behaviour"
];

PeakPower_kW = [
    normalPeak_kW
    peakScenarioPeak_kW
    abnormalPeak_kW
];

DailyEnergy_kWh = [
    normalEnergy_kWh
    peakEnergy_kWh
    abnormalEnergy_kWh
];

PeakUtilization_percent = [
    normalUtilization
    peakUtilization
    abnormalUtilization
];

WarningIntervals = [
    sum(normalWarnings)
    sum(peakWarnings)
    sum(abnormalWarnings)
];

results = table( ...
    Scenario, ...
    PeakPower_kW, ...
    DailyEnergy_kWh, ...
    PeakUtilization_percent, ...
    WarningIntervals ...
);

disp(results);


%% =========================================================
% VISUALIZATION 1 — NORMAL OPERATION
% ==========================================================

figure;

plot( ...
    timeHours, ...
    normalDemand_kW, ...
    'LineWidth', 2 ...
);

hold on;

yline( ...
    warningThreshold_kW, ...
    '--', ...
    'Warning Threshold', ...
    'LineWidth', 1.5 ...
);

xlabel('Time of Day (hours)');
ylabel('Station Demand (kW)');

title( ...
    'EV Charging Station — Normal Operation Scenario' ...
);

grid on;

xlim([0 24]);


%% =========================================================
% VISUALIZATION 2 — SCENARIO COMPARISON
% ==========================================================

figure;

plot( ...
    timeHours, ...
    normalDemand_kW, ...
    'LineWidth', 2 ...
);

hold on;

plot( ...
    timeHours, ...
    peakDemand_kW, ...
    'LineWidth', 2 ...
);

plot( ...
    timeHours, ...
    abnormalDemand_kW, ...
    'LineWidth', 2 ...
);

yline( ...
    warningThreshold_kW, ...
    '--', ...
    'Warning Threshold', ...
    'LineWidth', 1.5 ...
);

xlabel('Time of Day (hours)');
ylabel('Station Demand (kW)');

title( ...
    'EV Charging Station Digital Twin — Scenario Comparison' ...
);

legend( ...
    'Normal Operation', ...
    'Peak Demand', ...
    'Abnormal Behaviour', ...
    'Warning Threshold', ...
    'Location', ...
    'best' ...
);

grid on;

xlim([0 24]);


%% =========================================================
% VISUALIZATION 3 — DAILY ENERGY COMPARISON
% ==========================================================

figure;

bar( ...
    categorical(Scenario), ...
    DailyEnergy_kWh ...
);

ylabel('Simulated Daily Energy (kWh)');

title( ...
    'Energy Requirement Across Simulation Scenarios' ...
);

grid on;


%% =========================================================
% SAVE RESULTS
% ==========================================================

writetable( ...
    results, ...
    'ev_scenario_results.csv' ...
);

fprintf('\nSimulation complete.\n');
fprintf('Results saved to ev_scenario_results.csv\n');

fprintf( ...
    ['IMPORTANT: MATLAB values are engineering scenario ', ...
     'simulations and are not measured Caltech power data.\n'] ...
);