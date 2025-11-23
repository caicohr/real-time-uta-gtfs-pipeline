import requests
import json
import sys
import os
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict

# --- CONFIGURATION ---
# Professor's URL (Public endpoint, no API key needed)
URL = "https://apps.rideuta.com/tms/gtfs/Vehicle"

OUTPUT_DIR = "/data/GTFS_realtime"
OUTPUT_FILE = f"{OUTPUT_DIR}/realtime_dump.json"

def fetch_and_decode():
    print(f"1. Fetching binary data from {URL}...")
    
    # We must use a User-Agent header to mimic a web browser, 
    # otherwise the server might block the script.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(URL, headers=headers, timeout=30)
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

    # --- SCHEMA SAFETY PATCH ---
    # If the feed is empty (0 vehicles), we force the 'entity' key to exist
    # so DuckDB doesn't crash during schema inference.
    if "entity" not in data_dict:
        print("[WARNING] Feed is empty. Creating empty 'entity' list to maintain schema.")
        data_dict["entity"] = []

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"4. Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data_dict, f)
    
    print("Success.")

if __name__ == "__main__":
    fetch_and_decode()