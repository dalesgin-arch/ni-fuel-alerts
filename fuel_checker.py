import traceback
import requests
import math
import json
import os

# Carrickfergus coordinates
HOME_LAT = 54.715
HOME_LON = -5.805

API_URL = "https://www.fuelprices.gov.uk/api/feeds/latest"

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


def trim_station(station, fuel, distance):
    return {
        "brand": station.get("brand"),
        "name": station.get("name"),
        "postcode": station.get("postcode"),
        "distance_miles": distance,
        "price": station.get("prices", {}).get(fuel),
        "lat": station.get("location", {}).get("latitude"),
        "lon": station.get("location", {}).get("longitude"),
    }


def format_station(station):
    brand = station.get("brand", "")
    name = station.get("name", "Unknown station")
    address = station.get("address", "")
    postcode = station.get("postcode", "")

    if brand:
        return f"{brand} {name}, {address}, {postcode}".strip(", ")
    else:
        return f"{name}, {address}, {postcode}".strip(", ")


def should_ignore_station(station):
    brand = station.get("brand", "").lower()
    postcode = station.get("postcode", "").upper()

    if "sainsbury" in brand and postcode.startswith("BT38"):
        return True

    return False


def find_cheapest(stations, fuel_type):
    cheapest = None

    for s in stations:
        if should_ignore_station(s):
            continue

        prices = s.get("prices", {})
        if fuel_type not in prices:
            continue

        price = prices[fuel_type]

        loc = s.get("location", {})
        lat = loc.get("latitude")
        lon = loc.get("longitude")

        if lat is None or lon is None:
            continue

        dist = haversine(HOME_LAT, HOME_LON, lat, lon)

        if dist <= 8:
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
    history = load_history()

    # FULL browser headers (required to avoid 403)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en;q=0.9",
        "Referer": "https://www.fuel-finder.service.gov.uk/",
        "Origin": "https://www.fuel-finder.service.gov.uk",
        "Connection": "keep-alive"
    }

    response = requests.get(API_URL, headers=headers)

    try:
        data = response.json()
    except ValueError:
        print("ERROR: API did not return JSON")
        print("Status:", response.status_code)
        print("Headers:", response.headers)
        print("Body:", response.text[:500])
        raise SystemExit(1)

    stations = data.get("stations", [])

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
        arrow = get_arrow(old_price, new_price)

        trimmed = trim_station(station, fuel, distance)
        alerts.append(
            f"{fuel.capitalize()}: {new_price:.1f}p at {station_text} ({distance} miles)\n"
            f"{json.dumps(trimmed, indent=2)}"
        )

        history[fuel] = new_price

    save_history(history)

    if not alerts:
        alerts.append("No price changes today.")

    message = "\n\n".join(alerts)
    print("DEBUG TOKEN:", os.getenv("PUSHOVER_KEY"))
    print("DEBUG USER:", os.getenv("PUSHOVER_USER_KEY")
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()