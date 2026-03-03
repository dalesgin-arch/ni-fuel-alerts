import requests
import json
import os
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
API_URL = "https://www.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices?batch-number=1"
HISTORY_FILE = "fuel_history.json"

# Carrickfergus town centre coordinates
CARRICK_LAT = 54.715
CARRICK_LON = -5.805
MAX_DISTANCE_MILES = 8

# Secrets from GitHub Actions
PUSHOVER_KEY = os.getenv("PUSHOVER_KEY")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

print("Pushover key loaded:", PUSHOVER_KEY is not None)
print("Pushover user loaded:", PUSHOVER_USER_KEY is not None)
print("Client ID loaded:", CLIENT_ID is not None)
print("Client Secret loaded:", CLIENT_SECRET is not None)


# -----------------------------
# OAuth2 Token
# -----------------------------
def get_token():
    url = "https://www.fuel-finder.service.gov.uk/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    return r.json()["access_token"]


# -----------------------------
# Distance calculation (miles)
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # miles
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# -----------------------------
# Fetch cheapest prices for diesel, petrol, super unleaded
# -----------------------------
def fetch_cheapest_prices():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(API_URL, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    cheapest = {
        "diesel": None,
        "petrol": None,
        "superunleaded": None
    }

    for station in data.get("stations", []):
        addr = station.get("address", {})
        postcode = addr.get("postcode", "")

        # Northern Ireland only
        if not postcode.startswith("BT"):
            continue

        lat = station.get("latitude")
        lon = station.get("longitude")
        if lat is None or lon is None:
            continue

        # Distance filter
        dist = haversine(CARRICK_LAT, CARRICK_LON, lat, lon)
        if dist > MAX_DISTANCE_MILES:
            continue

        # Extract fuel prices
        for fuel in station.get("fuels", []):
            ftype = fuel.get("type", "").lower()
            price = fuel.get("price")

            if price is None:
                continue

            if ftype in cheapest:
                price = float(price)
                if cheapest[ftype] is None or price < cheapest[ftype]:
                    cheapest[ftype] = price

    return cheapest


# -----------------------------
# Load history
# -----------------------------
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


# -----------------------------
# Save history
# -----------------------------
def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# -----------------------------
# Send Pushover alert
# -----------------------------
def send_pushover(message):
    if not PUSHOVER_KEY or not PUSHOVER_USER_KEY:
        print("Pushover not configured.")
        return

    payload = {
        "token": PUSHOVER_KEY,
        "user": PUSHOVER_USER_KEY,
        "message": message,
        "title": "Fuel Price Alert",
        "priority
