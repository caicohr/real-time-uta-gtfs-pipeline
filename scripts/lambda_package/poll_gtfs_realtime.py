# Import the libraries we need:
# - requests: fetches data from the UTA API over HTTP
# - gtfs_realtime_pb2: decodes the Protobuf binary data into readable fields
# - json: formats the output nicely
import requests
from google.transit import gtfs_realtime_pb2
import json

# URL for UTA's real-time Vehicle Positions (binary Protobuf feed)
GTFS_RT_URL = "https://apps.rideuta.com/tms/gtfs/Vehicle"


def fetch_realtime_data():
    """
    Fetches the real-time GTFS data from UTA,
    decodes the Protobuf message, and extracts useful fields
    into a clean JSON-ready structure.
    """

    # Create an empty FeedMessage object (the standard GTFS RT container)
    feed = gtfs_realtime_pb2.FeedMessage()

    # Send HTTP GET request to the UTA feed
    response = requests.get(GTFS_RT_URL)

    # If the response wasn't successful (status != 200), stop and report it
    if response.status_code != 200:
        raise Exception(f"Request failed with status {response.status_code}")

    # Decode the binary Protobuf data into the FeedMessage object
    feed.ParseFromString(response.content)

    # Print the feed timestamp so we know how "fresh" the data is
    print("Feed timestamp:", feed.header.timestamp)

    # This list will store the cleaned-up vehicle records we extract
    entity_list = []

    # Loop through each entity (vehicle update) in the feed
    for entity in feed.entity:

        # Extract useful vehicle info into a Python dictionary
        entity_list.append({
            "id": entity.id,                                    # Unique entity ID
            "trip_id": entity.vehicle.trip.trip_id,             # What trip the vehicle is serving
            "route_id": entity.vehicle.trip.route_id,           # Route number (e.g., Bus 470)
            "latitude": entity.vehicle.position.latitude,        # GPS latitude
            "longitude": entity.vehicle.position.longitude,      # GPS longitude
            "vehicle_timestamp": entity.vehicle.timestamp,       # Time the GPS reading was taken
            "source_timestamp": feed.header.timestamp            # ✅ Timestamp of entire feed
        })

    # Return the cleaned JSON-ready list (no Protobuf objects)
    return entity_list


# Only runs when executing locally (NOT in Lambda)
if __name__ == "__main__":
    data = fetch_realtime_data()
    # Pretty-print JSON output so it's easy to read
    print(json.dumps(data, indent=2))