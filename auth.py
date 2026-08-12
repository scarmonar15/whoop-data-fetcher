import os
import json
import secrets
import string
import time
import requests
import threading
from urllib.parse import urlencode, urlparse
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI", "http://localhost:5000/callback")
TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")

app = Flask("WHOOP-OAuth-Server")
auth_state = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>WHOOP Auth Success</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #0c0f17;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 400px;
        }
        h1 {
            color: #ff3b30;
            margin-bottom: 10px;
        }
        p {
            color: #a0aec0;
            line-height: 1.5;
        }
        .icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">⚡</div>
        <h1>Authentication Successful!</h1>
        <p>WHOOP API credentials have been successfully retrieved and stored in <code>tokens.json</code>.</p>
        <p>You can close this tab and return to the terminal.</p>
    </div>
</body>
</html>
"""

ERROR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>WHOOP Auth Error</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #0c0f17;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 400px;
        }
        h1 {
            color: #ff3b30;
            margin-bottom: 10px;
        }
        p {
            color: #e53e3e;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>Authentication Failed</h1>
        <p>{{ error_message }}</p>
        <p>Please check your console and try again.</p>
    </div>
</body>
</html>
"""

def save_tokens(token_response):
    payload = {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "expires_in": token_response.get("expires_in"),
        "created_at": int(time.time())
    }
    with open(TOKENS_FILE, "w") as f:
        json.dump(payload, f, indent=4)
    print(f"[+] Saved tokens to {TOKENS_FILE}")

def shutdown_server():
    time.sleep(2)
    print("[*] Shutting down authorization server...")
    os._exit(0)

@app.route('/callback')
def callback():
    global auth_state
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        return render_template_string(ERROR_HTML, error_message=f"API Error: {error}")

    if not code:
        return render_template_string(ERROR_HTML, error_message="No authorization code received.")

    if state != auth_state:
        return render_template_string(ERROR_HTML, error_message="State mismatch (security check failed).")

    # Exchange authorization code for token
    token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI
    }

    try:
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_json = response.json()
            save_tokens(token_json)
            # Start shutdown thread
            threading.Thread(target=shutdown_server).start()
            return SUCCESS_HTML
        else:
            err_msg = response.json().get("error_description", response.text)
            return render_template_string(ERROR_HTML, error_message=f"Token Exchange Error: {err_msg}")
    except Exception as e:
        return render_template_string(ERROR_HTML, error_message=f"Exception: {str(e)}")

def check_credentials():
    if not CLIENT_ID or not CLIENT_SECRET or CLIENT_ID == "your_client_id_here" or CLIENT_SECRET == "your_client_secret_here":
        print("[-] Error: WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET are not set in your .env file.")
        print("    Please create a developer app on https://developer-dashboard.whoop.com/")
        print("    and add your credentials to the .env file.")
        return False
    return True

def get_auth_url():
    scopes = [
        "offline",
        "read:profile",
        "read:body_measurement",
        "read:cycles",
        "read:recovery",
        "read:sleep",
        "read:workout"
    ]
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": auth_state
    }
    return f"https://api.prod.whoop.com/oauth/oauth2/auth?{urlencode(params)}"

def start_server():
    if not check_credentials():
        return

    parsed_url = urlparse(REDIRECT_URI)
    hostname = parsed_url.hostname or "localhost"
    port = parsed_url.port or 5000

    auth_url = get_auth_url()
    print("\n" + "="*80)
    print("WHOOP OAUTH AUTHORIZATION".center(80))
    print("="*80)
    print("\n1. Copy and paste the following URL into your browser to log in:")
    print(f"\n{auth_url}\n")
    print(f"2. Log in with your WHOOP credentials and authorize the application.")
    print(f"3. The browser will redirect you to your redirect URI, and tokens will be saved.")
    print("="*80 + "\n")
    print(f"[*] Starting local server on {hostname}:{port} to listen for callback...")
    
    # Run Flask server
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    start_server()
