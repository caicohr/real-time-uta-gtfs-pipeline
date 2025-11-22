import requests
import json
import sys
import os
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict

URL = "https://cdn.mbta.com/realtime/VehiclePositions.pb"
# Output to a specific subfolder
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
    feed.ParseFromString(response.content)

    print("3. Converting to JSON...")
    data_dict = MessageToDict(feed)

    # Ensure subdirectory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"4. Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data_dict, f)
    
    print("Success.")

if __name__ == "__main__":
    fetch_and_decode()