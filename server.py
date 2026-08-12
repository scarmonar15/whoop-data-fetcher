import os
import sqlite3
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

# Import project files
import db

load_dotenv()

PORT = int(os.getenv("PORT", 8000))
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

def main():
    # Make sure DB exists
    db.init_db()
    print(f"[*] Starting local server on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

if __name__ == "__main__":
    main()
