import requests
import math
import json
import os

# Carrickfergus coordinates
HOME_LAT = 54.715
HOME_LON = -5.805

API_URL = "https://www.fuel-finder.service.gov.uk/api/v1/pfs/fuel-prices?batch-number=1"

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

    # Include brand in the formatted output
    if brand:
        return f"{brand} {name}, {address}, {postcode}".strip(", ")
    else:
        return f"{name}, {address}, {postcode}".strip(", ")

def should_ignore_station(station):
    brand = station.get("brand", "").lower()
    postcode = station.get("postcode", "").upper()

    # Ignore Sainsbury's Carrickfergus (postcode BT38)
    if "sainsbury" in brand and postcode.startswith("BT38"):
        return True

    return False

def find_cheapest(stations, fuel_type):
    cheapest = None
    for s in stations:

        # Skip Sainsbury's Carrickfergus
        if should_ignore_station(s):
            continue

        prices = s.get("prices", {})
        if fuel_type not in prices:
            continue

        price = prices[fuel_type]
        lat = s["location"]["latitude"]
        lon = s["location"]["longitude"]

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

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FuelChecker/1.0; +https://github.com)"
    }

    response = requests.get(API_URL, headers=headers)

    try:
        data = response.json()
    except ValueError:
        print("ERROR: API did not return JSON")
        print("Status:", response.status_code)
        print("Body:", response.text[:200])
        return

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

    if new_price != old_price:
            trimmed = trim_station(station, fuel, distance) 
                alerts.append( 
                        f"{fuel.capitalize()}: {new_price:.1f}p at {station_text} ({distance} miles)\n" 
                        f"{json.dumps(trimmed, indent=2)}" 
                    ) # Still update history so change alerts work in future if you want them history[fuel] = new_price
            )

        history[fuel] = new_price

    save_history(history)

    if alerts:
        message = "\n".join(alerts)
        send_pushover(
            message,
            os.getenv("PUSHOVER_KEY"),
            os.getenv("PUSHOVER_USER_KEY")
        )
        
    if not alerts: alerts.append("No price changes today.")

if __name__ == "__main__":
    main()

