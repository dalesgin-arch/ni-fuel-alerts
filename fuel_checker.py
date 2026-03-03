import requests
import json
from datetime import datetime
import os

# -----------------------------
# CONFIG
# -----------------------------
# API_URL = "https://www.consumercouncil.org.uk/fuel-price-checker"   # I will fill this once you choose the source
API_URL = "https://www.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices?batch-number=1"
FUEL_TYPE = "diesel"                # or "petrol"
HISTORY_FILE = "fuel_history.json"

PUSHOVER_KEY = os.getenv("PUSHOVER_KEY")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")

print("Key loaded:", PUSHOVER_KEY is not None)
print("User loaded:", PUSHOVER_USER_KEY is not None)


# -----------------------------
# Fetch fuel price
# -----------------------------
def get_token():
    token_url = "https://www.fuel-finder.service.gov.uk/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET")
    }
    r = requests.post(token_url, data=payload)
    r.raise_for_status()
    return r.json()["access_token"]
)

def fetch_price():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(API_URL, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    # Extract the average diesel price across all stations
    prices = []

    for station in data.get("stations", []):
        for fuel in station.get("fuels", []):
            if fuel.get("type") == FUEL_TYPE:
                prices.append(float(fuel.get("price")))

    if not prices:
        raise ValueError("No prices found for fuel type: " + FUEL_TYPE)

    return sum(prices) / len(prices)

def fetch_cheapest_prices():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(API_URL, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    # Track cheapest prices
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
        "priority": 0
    }

    r = requests.post("https://api.pushover.net/1/messages.json", data=payload)
    print("Pushover status:", r.status_code)

# -----------------------------
# Main logic
# -----------------------------
def main():
    price = fetch_price()
    now = datetime.utcnow().isoformat()

    print(f"Fetched price: {price}")

    history = load_history()
    history.append({"time": now, "price": price})
    save_history(history)

    # Compare to previous entry
    if len(history) >= 2:
        old_price = history[-2]["price"]
        if price < old_price:
            diff = round(old_price - price, 2)
            send_pushover(f"{FUEL_TYPE.capitalize()} dropped by {diff}p to {price}p")
        else:
            print("No price drop detected.")
    else:
        print("Not enough history to compare.")

if __name__ == "__main__":
    main()
