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

PUSHOVER_TOKEN = os.getenv("a3f4951ecyszhfh81w4wmd9cott5hg")
PUSHOVER_USER = os.getenv("uw8ivdux94t27c1bowuro8hr4ueiny")

# -----------------------------
# Fetch fuel price
# -----------------------------
def fetch_price():
    r = requests.get(API_URL, timeout=10)
    r.raise_for_status()
    data = r.json()

    # Adjust this depending on the API structure
    price = data[FUEL_TYPE]["price"]
    return float(price)

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
    if not PUSHOVER_TOKEN or not PUSHOVER_USER:
        print("Pushover not configured.")
        return

    payload = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
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
