import os
import sqlite3
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

# Import project files
import db

load_dotenv()

PORT = int(os.getenv("PORT", 8000))
API_KEY = os.getenv("API_KEY")
WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')

app = Flask("WHOOP-Dashboard-Server", static_folder=WEB_DIR)

# Helper to execute a query and return rows as dictionary
def query_db(query, args=(), one=False):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = cursor.fetchall()
    conn.close()
    
    # Convert sqlite3.Row objects to dictionaries
    results = [dict(row) for row in rv]
    return (results[0] if results else None) if one else results

@app.route('/')
def index():
    return send_from_directory(WEB_DIR, 'index.html')

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory(WEB_DIR, path)

@app.route('/api/profile')
def get_profile():
    # Return user profile (only one record)
    profile = query_db("SELECT * FROM profile LIMIT 1", one=True)
    if profile:
        return jsonify(profile)
    # Default mock/anonymous profile
    return jsonify({
        "first_name": "WHOOP",
        "last_name": "User",
        "email": "user@whoop.com",
        "height_meter": 1.8,
        "weight_kg": 80.0,
        "max_heart_rate": 190
    })

@app.route('/api/recovery')
def get_recovery():
    days = request.args.get('days', type=int)
    query = """
        SELECT r.*, c.start_time as date
        FROM recovery r
        LEFT JOIN cycles c ON r.cycle_id = c.id
    """
    args = []
    
    if days:
        query += " WHERE r.created_at >= datetime('now', ?)"
        args.append(f"-{days} days")
        
    query += " ORDER BY r.created_at ASC"
    
    records = query_db(query, args)
    return jsonify(records)

@app.route('/api/sleeps')
def get_sleeps():
    days = request.args.get('days', type=int)
    query = "SELECT * FROM sleeps"
    args = []
    
    if days:
        query += " WHERE created_at >= datetime('now', ?)"
        args.append(f"-{days} days")
        
    query += " ORDER BY created_at ASC"
    
    records = query_db(query, args)
    return jsonify(records)

@app.route('/api/cycles')
def get_cycles():
    days = request.args.get('days', type=int)
    query = "SELECT * FROM cycles"
    args = []
    
    if days:
        query += " WHERE created_at >= datetime('now', ?)"
        args.append(f"-{days} days")
        
    query += " ORDER BY created_at ASC"
    
    records = query_db(query, args)
    return jsonify(records)

@app.route('/api/workouts')
def get_workouts():
    days = request.args.get('days', type=int)
    query = "SELECT * FROM workouts"
    args = []
    
    if days:
        query += " WHERE created_at >= datetime('now', ?)"
        args.append(f"-{days} days")
        
    query += " ORDER BY created_at ASC"
    
    records = query_db(query, args)
    return jsonify(records)

@app.route('/api/summary')
def get_summary():
    days = request.args.get('days', type=int, default=30)
    days_str = f"-{days} days"

    # Aggregates
    recovery = query_db("""
        SELECT 
            AVG(recovery_score) as avg_recovery, 
            AVG(resting_heart_rate) as avg_rhr, 
            AVG(hrv_rmssd) as avg_hrv
        FROM recovery 
        WHERE created_at >= datetime('now', ?)
    """, (days_str,), one=True) or {}

    sleep = query_db("""
        SELECT 
            AVG(sleep_performance_percentage) as avg_sleep_perf,
            AVG(sleep_consistency_percentage) as avg_sleep_cons,
            AVG((strftime('%s', end_time) - strftime('%s', start_time)) / 3600.0) as avg_sleep_hours
        FROM sleeps
        WHERE created_at >= datetime('now', ?) AND nap = 0
    """, (days_str,), one=True) or {}

    cycle = query_db("""
        SELECT 
            AVG(strain) as avg_strain,
            AVG(kilocalories) as avg_calories
        FROM cycles
        WHERE created_at >= datetime('now', ?)
    """, (days_str,), one=True) or {}

    workouts_count = query_db("""
        SELECT COUNT(*) as count 
        FROM workouts 
        WHERE created_at >= datetime('now', ?)
    """, (days_str,), one=True) or {}

    return jsonify({
        "timeframe_days": days,
        "avg_recovery": round(recovery.get('avg_recovery') or 0, 1),
        "avg_rhr": round(recovery.get('avg_rhr') or 0, 1),
        "avg_hrv": round(recovery.get('avg_hrv') or 0, 1),
        "avg_sleep_performance": round(sleep.get('avg_sleep_perf') or 0, 1),
        "avg_sleep_consistency": round(sleep.get('avg_sleep_cons') or 0, 1),
        "avg_sleep_hours": round(sleep.get('avg_sleep_hours') or 0, 2),
        "avg_strain": round(cycle.get('avg_strain') or 0, 1),
        "avg_calories": round(cycle.get('avg_calories') or 0, 1),
        "workouts_count": workouts_count.get('count') or 0
    })

@app.route('/api/sync', methods=['POST'])
def trigger_sync():
    try:
        from fetch import run_pull
        run_pull()
        return jsonify({"status": "success", "message": "Synced successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            return jsonify({"error": "Unauthorized: API_KEY is not configured on the server"}), 401
            
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1].strip()
        
        if not token:
            token = request.headers.get("X-API-Key")
            
        if not token or token.strip() != API_KEY.strip():
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def compute_rolling_average(values, window):
    averages = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_data = [v for v in values[start:i + 1] if v is not None]
        if not window_data:
            averages.append(None)
        else:
            averages.append(round(sum(window_data) / len(window_data), 2))
    return averages

@app.route('/api/v1/metrics')
@require_api_key
def get_public_metrics():
    # Allow filtering by 'days' parameter, default to all history
    days = request.args.get('days', type=int)
    
    # Fetch recovery
    recovery_rows = query_db("""
        SELECT r.recovery_score, c.start_time as date
        FROM recovery r
        LEFT JOIN cycles c ON r.cycle_id = c.id
        WHERE c.start_time IS NOT NULL
        ORDER BY c.start_time ASC
    """)
    
    # Fetch strain
    strain_rows = query_db("""
        SELECT strain, start_time as date
        FROM cycles
        WHERE start_time IS NOT NULL
        ORDER BY start_time ASC
    """)
    
    # Fetch sleep
    sleep_rows = query_db("""
        SELECT s.sleep_performance_percent, c.start_time as date
        FROM sleeps s
        LEFT JOIN cycles c ON s.cycle_id = c.id
        WHERE c.start_time IS NOT NULL
        ORDER BY c.start_time ASC
    """)
    
    def format_series(rows, val_key):
        dates = [row['date'][:10] if row['date'] else None for row in rows]
        values = [row[val_key] for row in rows]
        
        avg_3d = compute_rolling_average(values, 3)
        avg_7d = compute_rolling_average(values, 7)
        avg_30d = compute_rolling_average(values, 30)
        
        series = []
        for i in range(len(rows)):
            if not dates[i]:
                continue
            series.append({
                "date": dates[i],
                "value": values[i],
                "avg_3d": avg_3d[i],
                "avg_7d": avg_7d[i],
                "avg_30d": avg_30d[i]
            })
            
        if days and len(series) > days:
            series = series[-days:]
        return series

    return jsonify({
        "recovery": format_series(recovery_rows, 'recovery_score'),
        "strain": format_series(strain_rows, 'strain'),
        "sleep_performance": format_series(sleep_rows, 'sleep_performance_percent')
    })

def daily_sync_loop():
    import time
    # Sleep 30s initially to let the server startup fully
    time.sleep(30)
    while True:
        try:
            print("[*] Running scheduled daily sync...")
            from fetch import run_pull
            run_pull()
            print("[+] Scheduled daily sync completed successfully.")
        except Exception as e:
            print(f"[-] Scheduled sync error: {e}")
        # Sleep for 24 hours
        time.sleep(86400)

def main():
    # Make sure DB exists
    db.init_db()
    
    # Start background daily sync thread (prevent double-start in Flask debug mode)
    import threading
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        threading.Thread(target=daily_sync_loop, daemon=True).start()
        print("[*] Started background daily sync thread.")
        
    print(f"[*] Starting local server on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

if __name__ == "__main__":
    main()
