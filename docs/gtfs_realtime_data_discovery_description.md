# GTFS Realtime Data Discovery & Description

**Project:** CS6830 Fundamentals of Data Engineering - Final Project  
**Module:** Week 2 - Data Ingestion (Discovery Phase)  
**Target Agency:** Utah Transit Authority (UTA) via Transitland  
**Author** Jerico Radin

-----

## 1\. GTFS Realtime Specifications Overview

### 1.1 What is GTFS Realtime?

GTFS Realtime (General Transit Feed Specification Realtime) is the industry-standard extension to static GTFS. While static GTFS defines the *scheduled* operations (stops, routes, timetables) in CSV format, GTFS Realtime provides a dynamic feed of **instantaneous updates**.

This specification allows transit agencies like **UTA** to push updates to consumers regarding:

  * **Trip Updates:** Delays, cancellations, and changed routes.
  * **Service Alerts:** Stop moves or unforeseen events affecting a station.
  * **Vehicle Positions:** GPS location and congestion levels of specific vehicles.

### 1.2 The Protocol Buffer Format

Unlike most modern web APIs that use JSON or XML, GTFS Realtime uses **Protocol Buffers (Protobuf)**.

  * **Binary Serialization:** The data is transmitted as a binary stream, not text.
  * **Efficiency:** It is significantly smaller (smaller payload size) and faster to parse than JSON, which is critical for feeds that may contain thousands of vehicle updates every few seconds.
  * **Strict Schema:** The data must be decoded against a `.proto` descriptor file.

-----

## 2\. Data Description & Schema (Data Dictionary)

The GTFS Realtime schema is hierarchical. The root element is always a `FeedMessage`, which contains metadata and a list of entities. The "Tables" below represent the nested message objects defined in the standard `gtfs-realtime.proto` schema.

### 2.1 FeedMessage (Root)

The top-level container returned by every HTTP poll.

| Field | Type | Description |
| :--- | :--- | :--- |
| `header` | `FeedHeader` | Metadata about the feed (version, timestamp). |
| `entity` | `list<FeedEntity>` | A repeated list of updates. This is the core payload. |

### 2.2 FeedHeader

Metadata describing the validity and freshness of the data payload.

| Field | Type | Description |
| :--- | :--- | :--- |
| `gtfs_realtime_version` | `string` | Version of the spec (e.g., "2.0"). |
| `timestamp` | `uint64` | POSIX time (seconds since epoch) of data generation. **Critical for latency checks.** |

### 2.3 FeedEntity

A wrapper that holds exactly **one** specific type of update.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `string` | Unique identifier for this entity. |
| `is_deleted` | `bool` | If true, the client should remove this entity from their view. |
| `vehicle` | `VehiclePosition` | (Optional) GPS location of a vehicle. |
| `trip_update` | `TripUpdate` | (Optional) Real-time arrival/departure prediction. |

### 2.4 VehiclePosition

Represents the physical location and status of a transit vehicle.

| Field | Type | Description |
| :--- | :--- | :--- |
| `trip` | `TripDescriptor` | The trip this vehicle is currently serving. |
| `vehicle` | `VehicleDescriptor` | Physical identifier of the bus/train (e.g., Bus \#405). |
| `position` | `Position` | Lat/Lon/Bearing/Speed data. |
| `current_stop_sequence` | `int32` | The stop sequence index the vehicle is currently at. |
| `current_status` | `enum` | `INCOMING_AT`, `STOPPED_AT`, or `IN_TRANSIT_TO`. |
| `timestamp` | `uint64` | Time when the GPS reading was taken. |

### 2.5 Cross-Reference: Realtime to Schedule

This section defines how the Realtime objects link to the Static CSV files (Foreign Keys).

| Realtime Object Field | Static CSV Table | Static CSV Column | Relationship Meaning |
| :--- | :--- | :--- | :--- |
| `TripUpdate.trip.trip_id` | `trips.txt` | `trip_id` | Links a live update to a scheduled trip. |
| `VehiclePosition.trip.route_id` | `routes.txt` | `route_id` | Links a live update to a specific route. |

-----

## 3\. Data Discovery Report

*Covers: Transitland API, Realtime Feed Verification, and Inspection*

### 3.1 Tasks

To ensure reliable access to the UTA data stream, we utilize **Transitland**, an open data aggregator.

  - **Identify Source:** Locate the UTA feed within the Transitland Registry (`f-9x0-uta~rt`).
  - **Authentication:** Obtain a Transitland API Key.
  - **Pipeline:** Fetch the raw Protobuf (`.pb`) file from Transitland, decode it, and load it into DuckDB for analysis.

### 3.2 Data Source Verification

  - **Aggregator:** Transitland
  - **Source Agency:** Utah Transit Authority (UTA)
  - **Feed ID:** `f-9x0-uta~rt`
  - **Endpoint:** `https://transit.land/api/v2/rest/feeds/f-9x0-uta~rt/download_latest_rt/vehicle_positions.pb`
  - **Format:** Protocol Buffers (Binary).
  - **Authentication:** API Key required via query parameter (`?apikey=...`).

#### 3.2.1 Obtaining a Transitland API Key

1.  Sign up for a free account at **[Transitland](https://www.transit.land/documentation)**.
2.  Navigate to your account settings to generate a v2 API Token.
3.  This key allows access to the "Download Latest Realtime" endpoints.

### 3.3 Data Load and Inspection Strategy

We implemented a **"Fetch-Decode-Query"** pipeline using Docker.

1.  **Fetch & Decode:** When the container starts, a Python script fetches the authenticated Protobuf data from Transitland and converts it to JSON.
2.  **Interactive Querying:** The container then opens an interactive DuckDB shell.

#### DuckDB Inspection Queries

Once the container drops you into the `D` prompt, copy and paste the following block to load and verify the data.

```sql
-- 1. Load the JSON file generated by the decoder
CREATE TABLE raw_feed AS 
SELECT * FROM read_json_auto('/data/GTFS_realtime/realtime_dump.json');

-- 2. Check Data Freshness (Header Timestamp)
-- We cast to ::BIGINT because JSON integers are inferred as strings
SELECT 
    header.timestamp AS unix_time,
    to_timestamp(header.timestamp::BIGINT) AS human_readable_time,
    (epoch(now()) - header.timestamp::BIGINT) AS data_age_seconds
FROM raw_feed;

-- 3. Flatten the Entities
-- The 'entity' column is a nested LIST. We UNNEST it to create rows.
CREATE VIEW vehicles AS
SELECT unnest(entity) as data FROM raw_feed;

-- 4. Inspect Specific Vehicle Attributes
-- Note: Protobuf JSON conversion uses camelCase (e.g., currentStatus)
SELECT 
    data.id AS entity_id,
    data.vehicle.vehicle.id AS vehicle_id,
    data.vehicle.position.latitude AS lat,
    data.vehicle.position.longitude AS lon,
    data.vehicle.currentStatus AS status
FROM vehicles
LIMIT 10;
```

-----

## 4\. Docker Reproduction Instructions

*Covers: Containerized Decoding & Inspection Environment*

To ensure reproducibility and security, we containerized the discovery process. We **do not** hardcode the API key; it is passed as an Environment Variable.

### 4.1 Directory Structure

```text
project-root/
├── Dockerfile              <-- Existing (for Static Schedule CSVs)
├── Dockerfile.realtime     <-- NEW (for Realtime Protobuf decoding)
├── scripts/
│   └── gtfs_realtime_decoder.py
├── data/
│   ├── GTFS/               <-- Static CSVs (gitignored)
│   └── GTFS_realtime/      <-- Auto-created by the script (gitignored)
```

### 4.2 The Decoder Script (`scripts/gtfs_realtime_decoder.py`)

This script reads the `TRANSITLAND_API_KEY` from the environment, fetches the binary data, and decodes it. If no key is present, it falls back to the MBTA (Boston) feed for testing purposes.

```python
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
```

### 4.3 The Dockerfile (`Dockerfile.realtime`)

We use a **Python base image** and manually install the correct **DuckDB CLI binary** for the user's architecture (Mac/Intel) to enable the interactive shell.

```dockerfile
FROM python:3.9-slim

# 1. Install System Tools (wget/unzip) and Python Libraries
RUN apt-get update && apt-get install -y wget unzip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir requests gtfs-realtime-bindings protobuf

# 2. Install DuckDB CLI (Architecture Aware)
# Detects if machine is ARM64 (Mac) or AMD64 (Intel) and fetches the right zip
RUN set -e; \
    ARCH=$(uname -m); \
    if [ "$ARCH" = "aarch64" ]; then \
        URL="https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-aarch64.zip"; \
    else \
        URL="https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-amd64.zip"; \
    fi; \
    wget "$URL" -O duckdb.zip && unzip duckdb.zip \
    && mv duckdb /usr/local/bin/ && chmod +x /usr/local/bin/duckdb \
    && rm duckdb.zip

WORKDIR /app
COPY scripts/gtfs_realtime_decoder.py .
RUN mkdir /data

# 3. Pipeline: Decode -> Open Interactive Shell
CMD /bin/bash -c "python gtfs_realtime_decoder.py && echo '\n✅ Ready. Paste SQL now.\n' && duckdb"
```

### 4.4 Execution

To run the container, pass your Transitland API key using the `-e` flag. If you want to test with MBTA (Boston) without a key, you can omit the `-e` flag.

**Mac/Linux:**

```bash
docker build -f Dockerfile.realtime -t gtfs-realtime .

# Option A: Use UTA (Requires Key)
docker run --rm -it \
  -v "$(pwd)/data":/data \
  -e TRANSITLAND_API_KEY="PASTE_YOUR_KEY_HERE" \
  gtfs-realtime

# Option B: Use MBTA (No Key - For Testing)
docker run --rm -it -v "$(pwd)/data":/data gtfs-realtime
```

**Windows (PowerShell):**

```powershell
docker run --rm -it `
  -v "${PWD}/data":/data `
  -e TRANSITLAND_API_KEY="PASTE_YOUR_KEY_HERE" `
  gtfs-realtime
```

-----

## 5\. References

  * **[Transitland API Documentation](https://www.transit.land/documentation)** - Official API reference and key signup.
  * **[GTFS Realtime Overview](https://developers.google.com/transit/gtfs-realtime)** - Protocol specification.
  * **[GTFS Realtime Best Practices](https://gtfs.org/realtime/best-practices/)** - Community standards for data feed quality.