import requests
import traceback
import os
import json

STATION = "Carrickfergus"
TRAIN_URL = f"https://api.translink.co.uk/NIrail/StationBoard?station={STATION}"

def send_pushover(message, token, user):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": token,
            "user": user,
            "message": message,
            "title": "Carrickfergus Train Update",
            "priority": 0
        }
    )

def get_train_data():
    try:
        data = requests.get(TRAIN_URL).json()
    except Exception:
        return "Train data unavailable."

    out = [f"Live trains for {STATION}:\n"]

    # Departures
    out.append("Departures:")
    for d in data.get("departures", []):
        out.append(
            f"{d['time']} → {d['destination']} | "
            f"Platform {d.get('platform', '—')} | {d['status']}"
        )

    # Arrivals
    out.append("\nArrivals:")
    for a in data.get("arrivals", []):
        out.append(
            f"{a['time']} ← {a['origin']} | "
            f"Platform {a.get('platform', '—')} | {a['status']}"
        )

    return "\n".join(out)

def main():
    try:
        train_section = get_train_data()

        message = train_section

        print("DEBUG TOKEN:", os.getenv("PUSHOVER_KEY"))
        print("DEBUG USER:", os.getenv("PUSHOVER_USER_KEY"))
        print("DEBUG MESSAGE:", message)

        send_pushover(
            message,
            os.getenv("PUSHOVER_KEY"),
            os.getenv("PUSHOVER_USER_KEY")
        )

    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()

if __name__ == "__main__":
    main()
