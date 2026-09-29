import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = BASE_DIR.parent

CSV_PATH = (
    PROJECT_ROOT
    / "Data"
    / "processed"
    / "acn_caltech_2019_clean.csv"
)

DATABASE_PATH = BASE_DIR / "ev_charging.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a connection to the local SQLite database.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# CREATE DATABASE TABLE
# ============================================================

def create_sessions_table(connection):

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS charging_sessions (

            session_id TEXT PRIMARY KEY,

            station_id TEXT NOT NULL,

            space_id TEXT,

            user_id TEXT,

            connection_time TEXT NOT NULL,

            disconnect_time TEXT NOT NULL,

            done_charging_time TEXT,

            energy_kwh REAL NOT NULL,

            connected_hours REAL,

            charging_hours REAL,

            idle_hours REAL,

            hour INTEGER,

            day_of_week INTEGER,

            day_name TEXT,

            month INTEGER,

            is_weekend INTEGER
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_sessions_station
        ON charging_sessions(station_id)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_sessions_connection_time
        ON charging_sessions(connection_time)
        """
    )

    connection.commit()


# ============================================================
# IMPORT PROCESSED DATA
# ============================================================

def import_sessions(connection):

    if not CSV_PATH.exists():

        raise FileNotFoundError(
            f"Processed dataset not found: {CSV_PATH}"
        )

    df = pd.read_csv(CSV_PATH)

    required_columns = [
        "sessionID",
        "stationID",
        "spaceID",
        "userID",
        "connectionTime_local",
        "disconnectTime_local",
        "doneChargingTime_local",
        "kWhDelivered",
        "connected_hours",
        "charging_hours",
        "hour",
        "day_of_week",
        "day_name",
        "month",
        "is_weekend"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing required CSV columns: "
            + ", ".join(missing_columns)
        )

    # Idle time is operationally useful:
    # connected duration minus active charging duration.
    df["idle_hours"] = (
        df["connected_hours"]
        - df["charging_hours"]
    )

    selected = df[
        required_columns
    ].copy()

    selected["idle_hours"] = df["idle_hours"]

    selected = selected.rename(
        columns={
            "sessionID": "session_id",
            "stationID": "station_id",
            "spaceID": "space_id",
            "userID": "user_id",
            "connectionTime_local": "connection_time",
            "disconnectTime_local": "disconnect_time",
            "doneChargingTime_local": "done_charging_time",
            "kWhDelivered": "energy_kwh"
        }
    )

    # Convert NaN values into None so SQLite stores NULL.
    selected = selected.astype(object).where(
        pd.notnull(selected),
        None
    )

    records = selected.to_dict(
        orient="records"
    )

    sql = """
        INSERT OR REPLACE INTO charging_sessions (

            session_id,
            station_id,
            space_id,
            user_id,
            connection_time,
            disconnect_time,
            done_charging_time,
            energy_kwh,
            connected_hours,
            charging_hours,
            idle_hours,
            hour,
            day_of_week,
            day_name,
            month,
            is_weekend

        )

        VALUES (

            :session_id,
            :station_id,
            :space_id,
            :user_id,
            :connection_time,
            :disconnect_time,
            :done_charging_time,
            :energy_kwh,
            :connected_hours,
            :charging_hours,
            :idle_hours,
            :hour,
            :day_of_week,
            :day_name,
            :month,
            :is_weekend

        )
    """

    connection.executemany(
        sql,
        records
    )

    connection.commit()

    return len(records)


# ============================================================
# DATABASE SUMMARY USING SQL
# ============================================================

def get_database_summary(connection):

    result = connection.execute(
        """
        SELECT

            COUNT(*) AS total_sessions,

            COUNT(DISTINCT station_id)
                AS total_chargers,

            ROUND(
                SUM(energy_kwh),
                2
            ) AS total_energy_kwh,

            ROUND(
                AVG(energy_kwh),
                2
            ) AS average_session_energy_kwh,

            ROUND(
                AVG(connected_hours),
                2
            ) AS average_connected_hours,

            ROUND(
                AVG(charging_hours),
                2
            ) AS average_charging_hours,

            ROUND(
                AVG(idle_hours),
                2
            ) AS average_idle_hours

        FROM charging_sessions
        """
    ).fetchone()

    return dict(result)


# ============================================================
# TOP CHARGERS USING SQL
# ============================================================

def get_top_chargers(
    connection,
    limit=10
):

    rows = connection.execute(
        """
        SELECT

            station_id,

            COUNT(*) AS sessions,

            ROUND(
                SUM(energy_kwh),
                2
            ) AS total_energy_kwh,

            ROUND(
                AVG(energy_kwh),
                2
            ) AS average_energy_kwh

        FROM charging_sessions

        GROUP BY station_id

        ORDER BY sessions DESC

        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    connection = get_connection()

    try:

        create_sessions_table(
            connection
        )

        existing_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM charging_sessions
            """
        ).fetchone()[0]

        if existing_count == 0:

            imported = import_sessions(
                connection
            )

            print(
                f"SQLite: imported "
                f"{imported} charging sessions"
            )

        else:

            print(
                f"SQLite: database already contains "
                f"{existing_count} charging sessions"
            )

        summary = get_database_summary(
            connection
        )

        print(
            f"SQLite database ready: "
            f"{DATABASE_PATH}"
        )

        print(
            f"SQL sessions: "
            f"{summary['total_sessions']}"
        )

        print(
            f"SQL chargers: "
            f"{summary['total_chargers']}"
        )

    finally:

        connection.close()


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    initialize_database()