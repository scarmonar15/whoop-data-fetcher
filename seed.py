import sqlite3
import os
import random
from datetime import datetime, timedelta

# Import database module
import db

def seed_database():
    db.init_db()
    conn = db.get_connection()
    cursor = conn.cursor()

    print("[*] Seeding database with realistic WHOOP mock data...")

    # Clear existing data to avoid mixing or duplicate primary key issues
    cursor.execute("DELETE FROM profile")
    cursor.execute("DELETE FROM cycles")
    cursor.execute("DELETE FROM recovery")
    cursor.execute("DELETE FROM sleeps")
    cursor.execute("DELETE FROM workouts")
    conn.commit()

    # 1. Profile Seed
    user_id = "mock-user-12345"
    cursor.execute('''
    INSERT OR REPLACE INTO profile (user_id, first_name, last_name, email, height_meter, weight_kg, max_heart_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, "Alex", "Morgan", "alex.morgan@fitness.com", 1.78, 74.5, 194))

    # 2. Cycles, Recovery, Sleeps, Workouts over the last 30 days
    base_time = datetime.utcnow() - timedelta(days=30)
    
    # Sports dictionary mapping
    sports = [0, 4, 36, 40, 97] # Run, Strength, Indoor Cycle, HIIT, Jiu Jitsu

    for i in range(31):
        day_date = base_time + timedelta(days=i)
        date_str = day_date.strftime("%Y-%m-%d")
        
        # UUIDs for relation
        cycle_id = f"cycle-uuid-{i}"
        sleep_id = f"sleep-uuid-{i}"
        workout_id = f"workout-uuid-{i}"

        # Setup timestamps
        # Sleep usually starts night before, e.g. 10:30 PM to 6:30 AM
        sleep_start = datetime(day_date.year, day_date.month, day_date.day, 22, 30) - timedelta(days=1)
        sleep_start += timedelta(minutes=random.randint(-30, 30))
        sleep_end = sleep_start + timedelta(hours=7, minutes=random.randint(0, 90))
        
        cycle_start = sleep_start
        cycle_end = day_date.replace(hour=22, minute=0)

        # Baseline health values with small variations
        base_hrv = 68.0
        base_rhr = 52.0
        
        # 1 in 5 days is a high-strain day resulting in poor recovery next day
        is_hard_day = (i % 6 == 0) and (i > 0)
        is_recovery_day = (i % 7 == 3)

        if is_hard_day:
            strain = random.uniform(16.5, 19.8)
            recovery_score = random.randint(15, 33)
            hrv = base_hrv * random.uniform(0.6, 0.8)
            rhr = base_rhr * random.uniform(1.15, 1.3)
            sleep_perf = random.randint(55, 75)
            calories = random.uniform(2800, 3500)
        elif is_recovery_day:
            strain = random.uniform(4.0, 7.5)
            recovery_score = random.randint(82, 98)
            hrv = base_hrv * random.uniform(1.2, 1.4)
            rhr = base_rhr * random.uniform(0.85, 0.95)
            sleep_perf = random.randint(90, 100)
            calories = random.uniform(1700, 2000)
        else:
            strain = random.uniform(10.0, 15.0)
            recovery_score = random.randint(45, 80)
            hrv = base_hrv * random.uniform(0.9, 1.15)
            rhr = base_rhr * random.uniform(0.95, 1.05)
            sleep_perf = random.randint(75, 92)
            calories = random.uniform(2100, 2600)

        # Insert Cycle
        avg_hr = int(random.uniform(70, 85))
        max_hr = int(random.uniform(160, 188))
        
        cursor.execute('''
        INSERT INTO cycles (
            id, user_id, created_at, updated_at, start_time, end_time, 
            timezone_offset, score_state, strain, average_heart_rate, 
            max_heart_rate, kilocalories
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cycle_id, user_id, 
            day_date.isoformat() + "Z", day_date.isoformat() + "Z",
            cycle_start.isoformat() + "Z", cycle_end.isoformat() + "Z",
            "-05:00", "SCORED", strain, avg_hr, max_hr, calories
        ))

        # Insert Recovery
        spo2 = random.uniform(96.5, 99.5)
        skin_temp = random.uniform(-0.4, 0.5)
        cursor.execute('''
        INSERT INTO recovery (
            cycle_id, sleep_id, user_id, created_at, updated_at, score_state,
            user_calibrating, recovery_score, resting_heart_rate, hrv_rmssd,
            spo2, skin_temp_celsius
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cycle_id, sleep_id, user_id, 
            day_date.isoformat() + "Z", day_date.isoformat() + "Z",
            "SCORED", 0, recovery_score, int(rhr), hrv, spo2, skin_temp
        ))

        # Insert Sleep
        sleep_duration_milli = int((sleep_end - sleep_start).total_seconds() * 1000)
        deep_sleep_milli = int(sleep_duration_milli * random.uniform(0.18, 0.25))
        rem_sleep_milli = int(sleep_duration_milli * random.uniform(0.20, 0.28))
        wake_milli = int(sleep_duration_milli * random.uniform(0.05, 0.10))
        light_sleep_milli = sleep_duration_milli - (deep_sleep_milli + rem_sleep_milli + wake_milli)
        
        cursor.execute('''
        INSERT INTO sleeps (
            id, user_id, created_at, updated_at, start_time, end_time,
            timezone_offset, nap, score_state, sleep_performance_percentage,
            sleep_consistency_percentage, respiratory_rate, deep_sleep_milli,
            light_sleep_milli, rem_sleep_milli, wake_milli, disturbance_count,
            sleep_cycle_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sleep_id, user_id, 
            day_date.isoformat() + "Z", day_date.isoformat() + "Z",
            sleep_start.isoformat() + "Z", sleep_end.isoformat() + "Z",
            "-05:00", 0, "SCORED", sleep_perf,
            random.randint(70, 98), random.uniform(13.8, 16.2),
            deep_sleep_milli, light_sleep_milli, rem_sleep_milli, wake_milli,
            random.randint(4, 15), random.randint(3, 6)
        ))

        # Insert Workouts (on about 65% of the days)
        if random.random() < 0.65:
            sport_id = random.choice(sports)
            workout_start = day_date.replace(hour=random.randint(7, 18), minute=random.randint(0, 50))
            workout_duration = timedelta(minutes=random.randint(30, 90))
            workout_end = workout_start + workout_duration
            
            w_strain = random.uniform(6.0, 16.0)
            w_avg_hr = int(random.uniform(125, 155))
            w_max_hr = int(random.uniform(160, 192))
            w_calories = w_strain * 45.0 + random.randint(50, 150)
            dist = random.uniform(3000, 10000) if sport_id == 0 else 0.0 # Only runs have distance here

            cursor.execute('''
            INSERT INTO workouts (
                id, user_id, created_at, updated_at, start_time, end_time,
                timezone_offset, sport_id, score_state, strain, average_heart_rate,
                max_heart_rate, kilocalories, distance_meter
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                workout_id, user_id, 
                day_date.isoformat() + "Z", day_date.isoformat() + "Z",
                workout_start.isoformat() + "Z", workout_end.isoformat() + "Z",
                "-05:00", sport_id, "SCORED", w_strain, w_avg_hr, w_max_hr,
                w_calories, dist
            ))

    conn.commit()
    conn.close()
    print("[+] Database successfully seeded with 30 days of high-fidelity WHOOP mock data!")

if __name__ == "__main__":
    seed_database()
