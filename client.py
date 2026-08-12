import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
BASE_URL = "https://api.prod.whoop.com"
TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")

class WhoopClient:
    def __init__(self, tokens_path=TOKENS_FILE):
        self.tokens_path = tokens_path
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.tokens = None
        self._load_tokens()

    def _load_tokens(self):
        if os.path.exists(self.tokens_path):
            try:
                with open(self.tokens_path, "r") as f:
                    self.tokens = json.load(f)
            except Exception as e:
                print(f"[-] Error loading tokens: {e}")
                self.tokens = None
        else:
            self.tokens = None

    def _save_tokens(self, tokens):
        self.tokens = tokens
        try:
            with open(self.tokens_path, "w") as f:
                json.dump(self.tokens, f, indent=4)
        except Exception as e:
            print(f"[-] Error saving tokens: {e}")

    def is_authorized(self):
        return self.tokens is not None and "access_token" in self.tokens

    def _ensure_valid_token(self):
        if not self.is_authorized():
            raise Exception("Client is not authorized. Please run the authorization flow first.")

        created_at = self.tokens.get("created_at", 0)
        expires_in = self.tokens.get("expires_in", 3600)
        now = int(time.time())

        # Refresh if token has expired or is about to expire within 5 minutes (300 seconds)
        if now >= (created_at + expires_in - 300):
            print("[*] Access token expired or close to expiry. Refreshing...")
            self._refresh_token()

    def _refresh_token(self):
        refresh_token = self.tokens.get("refresh_token")
        if not refresh_token:
            raise Exception("No refresh token found. Re-authorization required.")

        url = f"{BASE_URL}/oauth/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(url, data=data)
        if response.status_code == 200:
            token_json = response.json()
            new_tokens = {
                "access_token": token_json.get("access_token"),
                "refresh_token": token_json.get("refresh_token"),
                "expires_in": token_json.get("expires_in"),
                "created_at": int(time.time())
            }
            self._save_tokens(new_tokens)
            print("[+] Access token refreshed successfully.")
        else:
            err_msg = response.json().get("error_description", response.text)
            raise Exception(f"Failed to refresh token: {err_msg}")

    def _get_headers(self):
        self._ensure_valid_token()
        return {
            "Authorization": f"Bearer {self.tokens['access_token']}",
            "Content-Type": "application/json"
        }

    def _fetch_all_pages(self, endpoint, params=None):
        """Helper to exhaustively fetch all pages from a paginated WHOOP endpoint."""
        url = f"{BASE_URL}{endpoint}"
        if params is None:
            params = {}
        
        headers = self._get_headers()
        all_records = []
        next_token = None

        while True:
            query_params = params.copy()
            if next_token:
                query_params["nextToken"] = next_token

            # WHOOP API returns 400 or other errors sometimes if query params are empty.
            # We filter out None values.
            query_params = {k: v for k, v in query_params.items() if v is not None}

            response = requests.get(url, headers=headers, params=query_params)
            
            if response.status_code != 200:
                print(f"[-] API Error on {endpoint}: {response.status_code} - {response.text}")
                break

            data = response.json()
            records = data.get("records", [])
            all_records.extend(records)

            next_token = data.get("next_token")
            if not next_token:
                break
                
        return all_records

    def get_profile(self):
        """Fetches basic profile and body measurements, then combines them."""
        headers = self._get_headers()
        
        # 1. Fetch basic profile
        basic_url = f"{BASE_URL}/v2/user/profile/basic"
        basic_resp = requests.get(basic_url, headers=headers)
        if basic_resp.status_code != 200:
            raise Exception(f"Failed to fetch basic profile: {basic_resp.text}")
        basic_data = basic_resp.json()

        # 2. Fetch body measurements
        body_url = f"{BASE_URL}/v2/user/profile/body"
        body_resp = requests.get(body_url, headers=headers)
        if body_resp.status_code != 200:
            raise Exception(f"Failed to fetch body measurements: {body_resp.text}")
        body_data = body_resp.json()

        return {
            "user_id": str(basic_data.get("user_id")),
            "first_name": basic_data.get("first_name"),
            "last_name": basic_data.get("last_name"),
            "email": basic_data.get("email"),
            "height_meter": body_data.get("height_meter"),
            "weight_kg": body_data.get("weight_kg"),
            "max_heart_rate": body_data.get("max_heart_rate")
        }

    def get_cycles(self, start_date=None, end_date=None, limit=25):
        """Fetches physiological cycles."""
        params = {"start": start_date, "end": end_date, "limit": limit}
        return self._fetch_all_pages("/v2/cycle", params)

    def get_recovery(self, start_date=None, end_date=None, limit=25):
        """Fetches daily recoveries."""
        params = {"start": start_date, "end": end_date, "limit": limit}
        return self._fetch_all_pages("/v2/recovery", params)

    def get_sleeps(self, start_date=None, end_date=None, limit=25):
        """Fetches sleep data."""
        params = {"start": start_date, "end": end_date, "limit": limit}
        return self._fetch_all_pages("/v2/activity/sleep", params)

    def get_workouts(self, start_date=None, end_date=None, limit=25):
        """Fetches workout/activities data."""
        params = {"start": start_date, "end": end_date, "limit": limit}
        return self._fetch_all_pages("/v2/activity/workout", params)
