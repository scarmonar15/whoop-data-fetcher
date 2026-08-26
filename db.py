import sqlite3
import os

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), 'whoop_data.db'))

def get_connection(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Create profile table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profile (
        user_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        height_meter REAL,
        weight_kg REAL,
        max_heart_rate INTEGER
    )
    ''')

    # Create cycles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cycles (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        created_at TEXT,
        updated_at TEXT,
        start_time TEXT,
        end_time TEXT,
        timezone_offset TEXT,
        score_state TEXT,
        strain REAL,
        average_heart_rate INTEGER,
        max_heart_rate INTEGER,
        kilocalories REAL
    )
    ''')

    # Create recovery table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recovery (
        cycle_id TEXT PRIMARY KEY,
        sleep_id TEXT,
        user_id TEXT,
        created_at TEXT,
        updated_at TEXT,
        score_state TEXT,
        user_calibrating INTEGER,
        recovery_score INTEGER,
        resting_heart_rate INTEGER,
        hrv_rmssd REAL,
        spo2 REAL,
        skin_temp_celsius REAL
    )
    ''')

    # Create sleeps table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sleeps (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        created_at TEXT,
        updated_at TEXT,
        start_time TEXT,
        end_time TEXT,
        timezone_offset TEXT,
        nap INTEGER,
        score_state TEXT,
        sleep_performance_percentage INTEGER,
        sleep_consistency_percentage INTEGER,
        respiratory_rate REAL,
        deep_sleep_milli INTEGER,
        light_sleep_milli INTEGER,
        rem_sleep_milli INTEGER,
        wake_milli INTEGER,
        disturbance_count INTEGER,
        sleep_cycle_count INTEGER
    )
    ''')

    # Create workouts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workouts (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        created_at TEXT,
        updated_at TEXT,
        start_time TEXT,
        end_time TEXT,
        timezone_offset TEXT,
        sport_id INTEGER,
        score_state TEXT,
        strain REAL,
        average_heart_rate INTEGER,
        max_heart_rate INTEGER,
        kilocalories REAL,
        distance_meter REAL
    )
    ''')

    # Create habits table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        date TEXT,
        habit_id TEXT,
        completed INTEGER,
        PRIMARY KEY (date, habit_id)
    )
    ''')

    conn.commit()
    conn.close()

def save_profile(profile_data, db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO profile (user_id, first_name, last_name, email, height_meter, weight_kg, max_heart_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        profile_data.get('user_id'),
        profile_data.get('first_name'),
        profile_data.get('last_name'),
        profile_data.get('email'),
        profile_data.get('height_meter'),
        profile_data.get('weight_kg'),
        profile_data.get('max_heart_rate')
    ))
    conn.commit()
    conn.close()

def save_cycles(cycles_list, db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for cycle in cycles_list:
        score = cycle.get('score') or {}
        cursor.execute('''
        INSERT OR REPLACE INTO cycles (
            id, user_id, created_at, updated_at, start_time, end_time, 
            timezone_offset, score_state, strain, average_heart_rate, 
            max_heart_rate, kilocalories
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cycle.get('id'),
            cycle.get('user_id'),
            cycle.get('created_at'),
            cycle.get('updated_at'),
            cycle.get('start'),
            cycle.get('end'),
            cycle.get('timezone_offset'),
            cycle.get('score_state'),
            score.get('strain'),
            score.get('average_heart_rate'),
            score.get('max_heart_rate'),
            score.get('kilocalories')
        ))
    conn.commit()
    conn.close()

def save_recovery(recovery_list, db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for rec in recovery_list:
        score = rec.get('score') or {}
        cursor.execute('''
        INSERT OR REPLACE INTO recovery (
            cycle_id, sleep_id, user_id, created_at, updated_at, score_state,
            user_calibrating, recovery_score, resting_heart_rate, hrv_rmssd,
            spo2, skin_temp_celsius
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rec.get('cycle_id'),
            rec.get('sleep_id'),
            rec.get('user_id'),
            rec.get('created_at'),
            rec.get('updated_at'),
            rec.get('score_state'),
            1 if score.get('user_calibrating') else 0,
            score.get('recovery_score'),
            score.get('resting_heart_rate'),
            score.get('hrv_rmssd_milli'),
            score.get('spo2_percentage'),
            score.get('skin_temp_celsius')
        ))
    conn.commit()
    conn.close()

def save_sleeps(sleeps_list, db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for sleep in sleeps_list:
        score = sleep.get('score') or {}
        stages = score.get('stage_summary') or {}
        cursor.execute('''
        INSERT OR REPLACE INTO sleeps (
            id, user_id, created_at, updated_at, start_time, end_time,
            timezone_offset, nap, score_state, sleep_performance_percentage,
            sleep_consistency_percentage, respiratory_rate, deep_sleep_milli,
            light_sleep_milli, rem_sleep_milli, wake_milli, disturbance_count,
            sleep_cycle_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sleep.get('id'),
            sleep.get('user_id'),
            sleep.get('created_at'),
            sleep.get('updated_at'),
            sleep.get('start'),
            sleep.get('end'),
            sleep.get('timezone_offset'),
            1 if sleep.get('nap') else 0,
            sleep.get('score_state'),
            score.get('sleep_performance_percentage'),
            score.get('sleep_consistency_percentage'),
            score.get('respiratory_rate'),
            stages.get('deep_sleep_milli'),
            stages.get('light_sleep_milli'),
            stages.get('rem_sleep_milli'),
            stages.get('wake_milli'),
            stages.get('disturbance_count'),
            stages.get('sleep_cycle_count')
        ))
    conn.commit()
    conn.close()

def save_workouts(workouts_list, db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for w in workouts_list:
        score = w.get('score') or {}
        cursor.execute('''
        INSERT OR REPLACE INTO workouts (
            id, user_id, created_at, updated_at, start_time, end_time,
            timezone_offset, sport_id, score_state, strain, average_heart_rate,
            max_heart_rate, kilocalories, distance_meter
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            w.get('id'),
            w.get('user_id'),
            w.get('created_at'),
            w.get('updated_at'),
            w.get('start'),
            w.get('end'),
            w.get('timezone_offset'),
            w.get('sport_id'),
            w.get('score_state'),
            score.get('strain'),
            score.get('average_heart_rate'),
            score.get('max_heart_rate'),
            score.get('kilocalories'),
            score.get('distance_meter')
        ))
    conn.commit()
    conn.close()

def get_latest_updated_at(table_name, db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        # Check if table has data and return the latest updated_at
        cursor.execute(f"SELECT MAX(updated_at) FROM {table_name}")
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()

def get_habits(date_str, db_path=DEFAULT_DB_PATH):
    """Retrieves completion status of habits for a specific date (YYYY-MM-DD)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT habit_id, completed FROM habits WHERE date = ?", (date_str,))
        rows = cursor.fetchall()
        return {row["habit_id"]: bool(row["completed"]) for row in rows}
    except Exception as e:
        print(f"[-] Error loading habits: {e}")
        return {}
    finally:
        conn.close()

def toggle_habit(date_str, habit_id, db_path=DEFAULT_DB_PATH):
    """Toggles completion status of a habit for a specific date."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        # Check current status
        cursor.execute("SELECT completed FROM habits WHERE date = ? AND habit_id = ?", (date_str, habit_id))
        row = cursor.fetchone()
        
        if row is None:
            new_val = 1
            cursor.execute("INSERT INTO habits (date, habit_id, completed) VALUES (?, ?, ?)", (date_str, habit_id, new_val))
        else:
            new_val = 0 if row["completed"] else 1
            cursor.execute("UPDATE habits SET completed = ? WHERE date = ? AND habit_id = ?", (new_val, date_str, habit_id))
            
        conn.commit()
        return bool(new_val)
    except Exception as e:
        print(f"[-] Error toggling habit: {e}")
        return False
    finally:
        conn.close()
