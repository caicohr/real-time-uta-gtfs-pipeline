# GTFS Realtime Data Discovery & Description

**Project:** CS6830 Fundamentals of Data Engineering - Final Project  
**Module:** Week 2 - Data Ingestion & Streaming  
**Author** Jerico Radin

-----

## 1\. GTFS Realtime Specifications Overview

### 1.1 What is GTFS Realtime?

GTFS Realtime (General Transit Feed Specification Realtime) is the industry-standard extension to static GTFS. While static GTFS defines the *scheduled* operations (stops, routes, timetables) in CSV format, GTFS Realtime provides a dynamic feed of **instantaneous updates**.

This specification allows transit agencies (like the MBTA, MTA, or UTA) to push updates to consumers (Google Maps, Citymapper, or your data pipeline) regarding:

  * **Trip Updates:** Delays, cancellations, and changed routes.
  * **Service Alerts:** Stop moves or unforeseen events affecting a station.
  * **Vehicle Positions:** GPS location and congestion levels of specific vehicles.

### 1.2 The Protocol Buffer Format

Unlike most modern web APIs that use JSON or XML, GTFS Realtime uses **Protocol Buffers (Protobuf)**.

  * **Binary Serialization:** The data is transmitted as a binary stream, not text.
  * **Efficiency:** It is significantly smaller (smaller payload size) and faster to parse than JSON, which is critical for feeds that may contain thousands of vehicle updates every few seconds.
  * **Strict Schema:** The data must be decoded against a `.proto` descriptor file. This ensures type safety but requires a specific decoding step in the ingestion pipeline.

-----

## 2\. Data Description & Schema

The GTFS Realtime schema is hierarchical. The root element is always a `FeedMessage`, which contains metadata and a list of entities.

### 2.1 Root Hierarchy

Every poll to the API returns a single `FeedMessage` object.

| Field | Type | Description |
| :--- | :--- | :--- |
| **`header`** | `FeedHeader` | Metadata about the feed itself (version, timestamp). |
| **`entity`** | `List<FeedEntity>` | A repeated list of updates. This is the core payload. |

### 2.2 FeedHeader Schema

The header is critical for data engineering tasks, specifically for determining data freshness and preventing the processing of stale data.

  * **`gtfs_realtime_version`** *(string, required)*: The version of the specification (e.g., "2.0").
  * **`incrementality`** *(enum)*: Usually `FULL_DATASET`, meaning the current payload replaces all previous state.
  * **`timestamp`** *(uint64, required)*: POSIX time (seconds since epoch) when the feed was generated.
      * *Engineering Note:* Calculate `Data Latency = Current Time - Header Timestamp` to monitor feed health.

### 2.3 FeedEntity Schema

Each `FeedEntity` represents a single update. It acts as a wrapper that contains **one** of the three specific update types.

  * **`id`** *(string, required)*: Unique identifier for the entity.
  * **`is_deleted`** *(bool)*: Indicates if the entity should be removed from the consumer's view.
  * **`trip_update`**: (Optional) Fields related to arrival/departure times.
  * **`vehicle`**: (Optional) Fields related to GPS positioning.
  * **`alert`**: (Optional) Fields related to text-based service alerts.

### 2.4 Entity Payloads

Depending on the endpoint you poll, the entity will contain one of the following structures:

#### A. VehiclePosition

Used for tracking fleet movement on a map.

  * **`trip`**: Links the vehicle to a specific scheduled trip (referenced by `trip_id`).
  * **`position`**:
      * `latitude` / `longitude` (float): WGS-84 coordinates.
      * `bearing` (float): Direction the vehicle is facing.
      * `speed` (float): Momentary speed in meters/second.
  * **`current_status`**: Enum (`INCOMING_AT`, `STOPPED_AT`, `IN_TRANSIT_TO`).
  * **`timestamp`**: Time when the specific GPS reading was taken.

#### B. TripUpdate

Used for predicting arrivals and delays.

  * **`trip`**: Identifier for the trip being updated.
  * **`stop_time_update`** (List): A sequence of updates for future stops.
      * `stop_sequence`: The order of the stop.
      * `arrival` / `departure`:
          * `delay`: Integer (seconds). Positive = Late, Negative = Early.
          * `time`: Absolute POSIX time for the prediction.

#### C. Alert

Used for human-readable notifications.

  * **`active_period`**: Start and end times for the alert.
  * **`informed_entity`**: Who is affected? (Specific route, stop, or entire agency).
  * **`cause`**: Enum (`STRIKE`, `MAINTENANCE`, `WEATHER`, etc.).
  * **`effect`**: Enum (`NO_SERVICE`, `SIGNIFICANT_DELAYS`, `DETOUR`, etc.).
  * **`header_text`**: The headline of the alert (multilingual).

-----

## 3\. Data Discovery Report

**Data Discovery Lead:** Chase Powers  
*Covers: Realtime Feed Verification + Protobuf Decoding + DuckDB Inspection*

### 3.1 Tasks

Unlike the Static Schedule (CSV), the Realtime feed presents a unique challenge: **It is a binary stream.**

  - **Locate URL:** Identify the specific endpoint for Vehicle Positions.
  - **The Binary Challenge:** Verify that the raw file cannot be read by standard text editors or loaded directly into Excel/SQL.
  - **The Solution (Translation Layer):** Develop a Python script to fetch the Protobuf and convert it to JSON.
  - **Inspection:** Load the converted JSON into DuckDB to inspect the nested schema.
  - **Reproducibility:** Containerize the fetch-decode-query workflow using Docker.

### 3.2 Data Source Verification

  - **Target URL:** `https://cdn.mbta.com/realtime/VehiclePositions.pb` (Example Agency)
  - **Description:** Snapshot of current vehicle locations, speeds, and congestion status.
  - **Format:** Protocol Buffers (Binary).
  - **Update Frequency:** \~30 seconds.

### 3.3 Data Load and Inspection Strategy

Because DuckDB cannot natively query raw `.pb` files without a compiled schema, we implemented a **"Fetch-Decode-Query"** pipeline.

1.  **Fetch & Decode:** When the container starts, a Python script fetches the Protobuf data and converts it to JSON.
2.  **Interactive Querying:** The container then opens an interactive DuckDB shell, allowing us to run SQL directly against the generated JSON.

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

**Infrastructure Lead:** Jerico Radin  
*Covers: Containerized Decoding & Inspection Environment*

To ensure organization, we separate the realtime data dumps from the static CSVs by programmatically creating a `GTFS_realtime` directory.

### 4.1 Directory Structure

The Python script is located in `scripts/`, and the data will be output to `data/GTFS_realtime/`.

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

This script fetches the data and ensures the `GTFS_realtime` directory exists before saving.

```python
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
```

### 4.3 The Dockerfile (`Dockerfile.realtime`)

We use a **Python base image** to ensure we have a proper shell environment. We then programmatically download the **DuckDB CLI binary** that matches the user's computer architecture (Apple Silicon vs. Intel) to enable the interactive SQL session.

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

### 4.4 Build & Run Instructions

Run the container mounting the root `data` folder. The script will create the subfolder for you.

```bash
# Build
docker build -f Dockerfile.realtime -t gtfs-realtime .

# Run (Mac/Linux) - Note the use of -it for interactive mode
docker run --rm -it -v "$(pwd)/data":/data gtfs-realtime

# Run (Windows PowerShell)
docker run --rm -it -v "${PWD}/data":/data gtfs-realtime
```

### 4.5 Verification Output

Upon running the container, you will see the Python script execute, followed by the DuckDB prompt `D`. You can now verify the data:

```sql
D SELECT count(*) FROM read_json_auto('/data/GTFS_realtime/realtime_dump.json');
```

-----

## 5\. References & Further Reading

For a deeper dive into the specific byte-level requirements of the protocol or to troubleshoot validation issues, refer to the following official documentation.

### 5.1 Official Specifications

  * **[GTFS Realtime Overview](https://developers.google.com/transit/gtfs-realtime)** The primary entry point for the specification. It covers the high-level architecture of Protocol Buffers and the relationship between the Static and Realtime feeds.

  * **[GTFS Realtime Validation Errors & Warnings](https://developers.google.com/transit/gtfs-realtime/guides/realtime-errors-warnings)** A critical resource for debugging. It defines standard error codes you might see during ingestion, such as:

      * `TIMESTAMP_FUTURE`: The feed header time is in the future (check server clock).
      * `TRIP_UPDATE_WITHOUT_STOP_TIME_UPDATE`: A trip update exists but has no prediction data.
      * `NO_VEHICLE_POSITION`: A vehicle is referenced but has no GPS data.

### 5.2 Community Standards

  * **[GTFS Realtime Best Practices](https://gtfs.org/realtime/best-practices/)** Beyond the technical schema, this guide describes the *standard of care* expected by data consumers (e.g., "Feeds should be refreshed at least every 30 seconds" and "Do not output empty entities").

  * **[Protocol Buffers Language Guide (proto3)](https://protobuf.dev/programming-guides/proto3/)** The technical documentation for the `.proto` file format itself, useful if you need to modify the data structures or generate bindings for a language other than Python.