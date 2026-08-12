import sys
import os
import argparse
from datetime import datetime, timedelta

# Import project files
import db
from client import WhoopClient
from auth import start_server

def run_auth():
    print("[*] Starting authentication process...")
    start_server()

def run_pull(days_fallback=30):
    # Initialize database
    db.init_db()

    client = WhoopClient()
    if not client.is_authorized():
        raise RuntimeError("WHOOP client is not authorized. Please run the authorization flow first: python fetch.py auth")

    print("[*] Connecting to WHOOP API...")

    # 1. Fetch and save user profile
    try:
        print("[*] Fetching user profile...")
        profile = client.get_profile()
        db.save_profile(profile)
        print(f"[+] Saved profile for {profile['first_name']} {profile['last_name']}")
    except Exception as e:
        print(f"[-] Error fetching profile: {e}")

    # Helper for calculating start dates
    fallback_start = (datetime.utcnow() - timedelta(days=days_fallback)).isoformat() + "Z"

    # Helper function for syncing an endpoint
    def sync_data(name, db_table, fetch_func, save_func):
        latest_updated = db.get_latest_updated_at(db_table)
        
        # WHOOP API v2 uses ISO-8601 timestamps (Z)
        # If we have a latest timestamp, we fetch from that timestamp onwards.
        start_date = latest_updated if latest_updated else fallback_start
        print(f"[*] Syncing {name} starting from {start_date}...")
        
        try:
            records = fetch_func(start_date=start_date)
            if records:
                save_func(records)
                print(f"[+] Synced {len(records)} new/updated {name} records.")
            else:
                print(f"[~] No new {name} records found.")
        except Exception as e:
            print(f"[-] Error syncing {name}: {e}")

    # 2. Sync Cycles
    sync_data("cycles", "cycles", client.get_cycles, db.save_cycles)

    # 3. Sync Recovery
    sync_data("recovery", "recovery", client.get_recovery, db.save_recovery)

    # 4. Sync Sleeps
    sync_data("sleeps", "sleeps", client.get_sleeps, db.save_sleeps)

    # 5. Sync Workouts
    sync_data("workouts", "workouts", client.get_workouts, db.save_workouts)

    print("[+] Sync complete!")

def main():
    parser = argparse.ArgumentParser(description="WHOOP API Data Fetcher")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Auth subcommand
    subparsers.add_parser("auth", help="Authenticate with the WHOOP API (launches local callback server)")

    # Pull subcommand
    pull_parser = subparsers.add_parser("pull", help="Fetch new data from the WHOOP API and save to SQLite")
    pull_parser.add_argument("--days", type=int, default=30, help="Number of fallback days to pull if database is empty (default: 30)")

    args = parser.parse_args()

    if args.command == "auth":
        run_auth()
    elif args.command == "pull":
        try:
            run_pull(args.days)
        except Exception as e:
            print(f"[-] {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
