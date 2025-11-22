import requests
import json
import sys
import os
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict

# --- CONFIGURATION ---
# 1. Try to get the Transitland Key (for UTA)
API_KEY = os.environ.get('TRANSITLAND_API_KEY')

# 2. If no key is provided, fallback to MBTA (Boston) which is Open/Free
if not API_KEY:
    print("\n[NOTICE] No TRANSITLAND_API_KEY found. Switching to MBTA (Boston) for testing.")
    # MBTA Direct URL (No Key Required)
    URL = "https://cdn.mbta.com/realtime/VehiclePositions.pb"
else:
    print(f"\n[INFO] Using Transitland API Key for UTA...")
    # UTA via Transitland (Requires Key)
    URL = f"https://transit.land/api/v2/rest/feeds/f-9x0-uta~rt/download_latest_rt/vehicle_positions.pb?apikey={API_KEY}"

OUTPUT_DIR = "/data/GTFS_realtime"
OUTPUT_FILE = f"{OUTPUT_DIR}/realtime_dump.json"

def fetch_and_decode():
    print(f"1. Fetching binary data from {URL}...")
    try:
        response = requests.get(URL)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    print("2. Parsing Protobuf...")
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(response.content)
    except Exception as e:
        print(f"Error parsing protobuf: {e}")
        sys.exit(1)

    print(f"3. Converting {len(feed.entity)} entities to JSON...")
    data_dict = MessageToDict(feed)

    # --- SAFETY PATCH: Ensure 'entity' key exists ---
    # If the feed is empty (common at night), MessageToDict omits the key. 
    # We force it back so DuckDB doesn't crash.
    if "entity" not in data_dict:
        print("[WARNING] Feed is empty (0 vehicles). Forcing empty 'entity' list to fix DuckDB schema.")
        data_dict["entity"] = []

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"4. Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data_dict, f)
    
    print("Success.")

if __name__ == "__main__":
    fetch_and_decode()