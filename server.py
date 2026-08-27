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

# Ensure database and tables exist at startup
db.init_db()

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

@app.route('/screen')
def serve_screen():
    return send_from_directory(WEB_DIR, 'screen.html')

@app.route('/api/weather')
def get_weather():
    try:
        import requests
        # Coordinates for Rionegro, Colombia
        url = "https://api.open-meteo.com/v1/forecast?latitude=6.1552&longitude=-75.3738&current_weather=true&timezone=auto"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return jsonify(data.get("current_weather", {}))
        return jsonify({"error": "Failed to fetch weather"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/habits', methods=['GET'])
def get_habits_endpoint():
    date_str = request.args.get('date')
    if not date_str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
    habits = db.get_habits(date_str)
    return jsonify(habits)

@app.route('/api/habits/toggle', methods=['POST'])
def toggle_habit_endpoint():
    try:
        data = request.json or {}
        date_str = data.get('date')
        habit_id = data.get('habit_id')
        if not date_str or not habit_id:
            return jsonify({"error": "Missing date or habit_id"}), 400
        
        completed = db.toggle_habit(date_str, habit_id)
        return jsonify({"status": "success", "habit_id": habit_id, "completed": completed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/water', methods=['GET'])
def get_water_endpoint():
    date_str = request.args.get('date')
    if not date_str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
    amount = db.get_water(date_str)
    return jsonify({"amount_ml": amount})

@app.route('/api/water/increment', methods=['POST'])
def increment_water_endpoint():
    try:
        data = request.json or {}
        date_str = data.get('date')
        increment_ml = data.get('increment_ml', 250)
        if not date_str:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        amount = db.increment_water(date_str, increment_ml)
        return jsonify({"status": "success", "amount_ml": amount})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/habits/history', methods=['GET'])
def get_habits_history_endpoint():
    date_str = request.args.get('date')
    days = request.args.get('days', type=int, default=7)
    if not date_str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
    history = db.get_habit_history(date_str, days)
    return jsonify(history)

def fetch_calendar_events():
    urls_str = os.getenv("GOOGLE_CALENDAR_URL")
    if not urls_str:
        print("[*] GOOGLE_CALENDAR_URL not configured. Returning empty agenda.")
        return []
    
    urls = [url.strip() for url in urls_str.split(",") if url.strip()]
    if not urls:
        return []
        
    try:
        import requests
        from icalendar import Calendar
        from datetime import datetime, date
        import pytz
        
        local_tz = pytz.timezone("America/Bogota")
        now_local = datetime.now(local_tz)
        today_start = local_tz.localize(datetime(now_local.year, now_local.month, now_local.day, 0, 0, 0))
        today_end = local_tz.localize(datetime(now_local.year, now_local.month, now_local.day, 23, 59, 59))
        
        all_events = []
        for url in urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code != 200:
                    print(f"[-] Failed to fetch iCal feed {url}: {resp.status_code}")
                    continue
                    
                cal = Calendar.from_ical(resp.content)
                
                for component in cal.walk('vevent'):
                    if component.name != "VEVENT":
                        continue
                        
                    dtstart = component.get('dtstart')
                    dtend = component.get('dtend')
                    summary = component.get('summary')
                    
                    if not dtstart or not summary:
                        continue
                        
                    start_val = dtstart.dt
                    end_val = dtend.dt if dtend else start_val
                    
                    is_all_day = False
                    if isinstance(start_val, date) and not isinstance(start_val, datetime):
                        is_all_day = True
                        start_dt = local_tz.localize(datetime(start_val.year, start_val.month, start_val.day, 0, 0, 0))
                        end_dt = local_tz.localize(datetime(end_val.year, end_val.month, end_val.day, 23, 59, 59))
                    else:
                        if start_val.tzinfo is None:
                            start_dt = pytz.utc.localize(start_val).astimezone(local_tz)
                            end_dt = pytz.utc.localize(end_val).astimezone(local_tz)
                        else:
                            start_dt = start_val.astimezone(local_tz)
                            end_dt = end_val.astimezone(local_tz)
                            
                    if (start_dt <= today_end and end_dt >= today_start):
                        time_str = "All Day" if is_all_day else start_dt.strftime("%I:%M %p")
                        all_events.append({
                            "start_time": start_dt.isoformat(),
                            "end_time": end_dt.isoformat(),
                            "time_str": time_str,
                            "title": str(summary),
                            "is_all_day": is_all_day
                        })
            except Exception as e:
                print(f"[-] Error fetching or parsing iCal feed {url}: {e}")
                
        all_events.sort(key=lambda e: e["start_time"])
        return all_events
    except Exception as e:
        print(f"[-] Error handling calendar fetch: {e}")
        return []

@app.route('/api/calendar', methods=['GET'])
def get_calendar_endpoint():
    events = fetch_calendar_events()
    return jsonify(events)

@app.route('/api/commutes', methods=['GET'])
def get_commutes():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # Fallback to mock data if API key is not configured
    if not api_key:
        print("[*] GOOGLE_MAPS_API_KEY not configured. Returning mock commutes.")
        return jsonify([
            { "name": "Mall Indiana", "desc": "Via Las Palmas", "time": "24 min", "status": "optimal", "color": "text-green" },
            { "name": "Reserva del Sur", "desc": "Local Route", "time": "18 min", "status": "minor delays", "color": "text-orange" },
            { "name": "Mall Llanogrande", "desc": "Via Llanogrande", "time": "11 min", "status": "smooth", "color": "text-green" }
        ])
        
    try:
        import requests
        origin = os.getenv("COMMUTE_ORIGIN", "Edificio Cambulo, Rionegro, Antioquia, Colombia")
        destinations = [
            "Mall Indiana, Envigado, Antioquia, Colombia",
            "Reserva del Sur, Itagui, Antioquia, Colombia",
            "Mall Llanogrande, Rionegro, Antioquia, Colombia"
        ]
        dest_names = ["Mall Indiana", "Reserva del Sur", "Mall Llanogrande"]
        dest_descs = ["Via Las Palmas", "Local Route", "Via Llanogrande"]
        
        dest_str = "|".join(destinations)
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origin,
            "destinations": dest_str,
            "departure_time": "now",
            "key": api_key
        }
        
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            raise Exception(f"Google Maps API error: {resp.status_code}")
            
        data = resp.json()
        if data.get("status") != "OK":
            raise Exception(f"Google Maps API status: {data.get('status')}")
            
        # Parse results
        results = []
        rows = data.get("rows", [])
        if not rows:
            raise Exception("No rows returned from Google Distance Matrix")
            
        elements = rows[0].get("elements", [])
        for i, elem in enumerate(elements):
            if elem.get("status") != "OK":
                results.append({
                    "name": dest_names[i],
                    "desc": dest_descs[i],
                    "time": "-- min",
                    "status": "unavailable",
                    "color": "text-orange"
                })
                continue
                
            duration_data = elem.get("duration_in_traffic") or elem.get("duration")
            standard_duration = elem.get("duration", {}).get("value", 0)
            traffic_duration = duration_data.get("value", 0)
            
            time_text = duration_data.get("text", "").replace("mins", "min").replace("min", "min")
            
            if standard_duration <= 0:
                ratio = 1.0
            else:
                ratio = traffic_duration / standard_duration
                
            if ratio <= 1.1:
                status = "optimal"
                color = "text-green"
            elif ratio <= 1.3:
                status = "minor delays"
                color = "text-orange"
            else:
                status = "heavy traffic"
                color = "text-pink"
                
            results.append({
                "name": dest_names[i],
                "desc": dest_descs[i],
                "time": time_text,
                "status": status,
                "color": color
            })
            
        return jsonify(results)
    except Exception as e:
        print(f"[-] Error fetching Google Maps Distance Matrix: {e}")
        return jsonify([
            { "name": "Mall Indiana (Fallback)", "desc": "Via Las Palmas", "time": "24 min", "status": "optimal", "color": "text-green" },
            { "name": "Reserva del Sur (Fallback)", "desc": "Local Route", "time": "18 min", "status": "minor delays", "color": "text-orange" },
            { "name": "Mall Llanogrande (Fallback)", "desc": "Via Llanogrande", "time": "11 min", "status": "smooth", "color": "text-green" }
        ])

@app.route('/api/linear', methods=['GET'])
def get_linear_priorities():
    api_key = os.getenv("LINEAR_API_KEY")
    
    # Fallback to mock data if API key is not configured
    if not api_key:
        print("[*] LINEAR_API_KEY not configured. Returning mock priorities.")
        return jsonify([
            { "key": "WHOOP-104", "title": "Configure persistent SQLite storage for dashboard analytics", "priority": "high" },
            { "key": "WHOOP-108", "title": "Optimize public metrics API endpoint averages calculation", "priority": "medium" },
            { "key": "WHOOP-111", "title": "Implement daily automated sync background job", "priority": "high" }
        ])
        
    try:
        import requests
        url = "https://api.linear.app/graphql"
        headers = {
            "Content-Type": "application/json",
            "Authorization": api_key
        }
        
        query = """
        query {
          viewer {
            assignedIssues(
              filter: { state: { type: { nin: ["completed", "canceled"] } } }
              orderBy: priority
              first: 3
            ) {
              nodes {
                identifier
                title
                priority
              }
            }
          }
        }
        """
        
        resp = requests.post(url, json={"query": query}, headers=headers, timeout=5)
        if resp.status_code != 200:
            raise Exception(f"Linear API error: {resp.status_code}")
            
        result_data = resp.json()
        if "errors" in result_data:
            raise Exception(f"Linear GraphQL errors: {result_data['errors']}")
            
        viewer = result_data.get("data", {}).get("viewer")
        if not viewer:
            raise Exception("No viewer returned (is your LINEAR_API_KEY valid?)")
            
        nodes = viewer.get("assignedIssues", {}).get("nodes", [])
        
        # Priority mapping: 1 -> urgent, 2 -> high, 3 -> medium, 4/0 -> low
        priority_map = {
            1: "urgent",
            2: "high",
            3: "medium",
            4: "low",
            0: "low"
        }
        
        priorities = []
        for node in nodes:
            priority_val = node.get("priority", 0)
            priority_label = priority_map.get(priority_val, "low")
            
            priorities.append({
                "key": node.get("identifier"),
                "title": node.get("title"),
                "priority": priority_label
            })
            
        return jsonify(priorities)
    except Exception as e:
        print(f"[-] Error fetching Linear priorities: {e}")
        return jsonify([
            { "key": "WHOOP-104 (Fallback)", "title": "Configure persistent SQLite storage for dashboard analytics", "priority": "high" },
            { "key": "WHOOP-108 (Fallback)", "title": "Optimize public metrics API endpoint averages calculation", "priority": "medium" },
            { "key": "WHOOP-111 (Fallback)", "title": "Implement daily automated sync background job", "priority": "high" }
        ])

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
        SELECT r.recovery_score, r.hrv_rmssd, c.start_time as date
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
        SELECT sleep_performance_percentage, start_time as date
        FROM sleeps
        WHERE start_time IS NOT NULL
        ORDER BY start_time ASC
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
        "sleep_performance": format_series(sleep_rows, 'sleep_performance_percentage'),
        "hrv": format_series(recovery_rows, 'hrv_rmssd')
    })

def periodic_sync_loop():
    import time
    # Sleep 30s initially to let the server startup fully
    time.sleep(30)
    while True:
        try:
            print("[*] Running scheduled periodic sync...")
            from fetch import run_pull
            run_pull()
            print("[+] Scheduled periodic sync completed successfully.")
        except Exception as e:
            print(f"[-] Scheduled sync error: {e}")
        # Sleep for 4 hours
        time.sleep(14400)

def main():
    # Make sure DB exists
    db.init_db()
    
    # Start background periodic sync thread (prevent double-start in Flask debug mode)
    import threading
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        threading.Thread(target=periodic_sync_loop, daemon=True).start()
        print("[*] Started background periodic sync thread.")
        
    print(f"[*] Starting local server on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)

if __name__ == "__main__":
    main()
