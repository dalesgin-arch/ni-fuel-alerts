import requests
import math
import json
import os

# Carrickfergus coordinates
HOME_LAT = 54.715
HOME_LON = -5.805

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def load_history():
    if not os.path.exists("fuel_history.json"):
        return {}
    with open("fuel_history.json", "r") as f:
        return json.load(f)

def save_history(history):
    with open("fuel_history.json", "w") as f:
        json.dump(history, f, indent=2)

def get_arrow(old, new):
    if new < old:
        return "⬇️"
    elif new > old:
        return "⬆️"
    else:
        return "➡️"

def format_station(station):
    name = station.get("station_name", "Unknown station")
    address = station.get("address", "")
    postcode = station.get("postcode", "")
    return f"{name}, {address}, {postcode}".strip(", ")

def find_cheapest(stations, fuel_type):
    cheapest = None
    for s in stations:
        if fuel_type not in s["prices"]:
            continue
        price = s["prices"][fuel_type]
        dist = haversine(HOME_LAT, HOME_LON, s["latitude"], s["longitude"])
        if dist <= 8:  # within 8 miles
            if cheapest is None or price < cheapest["price"]:
                cheapest = {
                    "price": price,
                    "station": s,
                    "distance": round(dist, 1)
                }
    return cheapest

def send_pushover(message, token, user):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": token,
            "user": user,
            "message": message,
            "title": "Fuel Price Alert",
            "priority": 0
        }
    )

def main():
    # Load previous prices
    history = load_history()

    # Fetch latest data
    response = requests.get("YOUR_FUEL_API_URL_HERE")
    stations = response.json()["stations"]

    fuels = ["diesel", "petrol", "super"]
    alerts = []

    for fuel in fuels:
        cheapest = find_cheapest(stations, fuel)
        if not cheapest:
            continue

        new_price = cheapest["price"]
        station = cheapest["station"]
        distance = cheapest["distance"]
        station_text = format_station(station)

        old_price = history.get(fuel, new_price)
        arrow = get_arrow(old_price
