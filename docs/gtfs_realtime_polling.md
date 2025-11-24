# UTA GTFS Realtime Data Polling

**Author:** Chase Powers – Polling & Lambda Deployment Lead  
**Course:** CS6830 – Fundamentals of Data Engineering (Fall 2025)

---

## Overview

This document explains the implementation and deployment of the GTFS Realtime polling service for the Utah Transit Authority (UTA). The purpose of this component is to retrieve live vehicle location data at regular intervals and prepare it for downstream streaming and analytics.

The polling service performs the following functions:

- Polls the UTA GTFS Realtime Vehicle Positions API
- Decodes the binary Protocol Buffers feed
- Extracts key fields for each vehicle
- Formats the data into JSON-ready structures
- Runs automatically every 30 seconds using AWS Lambda and EventBridge

This component completes Part 3: Polling of the project pipeline. A separate team member is responsible for Part 4: Streaming the Data to Kinesis.

---

## Repository Structure

The polling-related files are stored in the project repository:

```
real-time-uta-gtfs-pipeline/
├── docs/
│   └── gtfs_realtime_polling.md
├── scripts/
│   ├── poll_gtfs_realtime.py
│   └── poll_lambda.py
└── …
```

## File Responsibilities

`poll_gtfs_realtime.py`
- Fetches realtime data from the UTA GTFS endpoint
- Decodes the Protobuf feed
- Extracts vehicle fields
- Returns JSON-ready dictionaries

`poll_lambda.py`
- Wraps the polling code in an AWS Lambda handler
- Returns the data in the required Lambda response format
- Serves as the deployed entrypoint executed every 30 seconds

---

## Data Source: UTA GTFS Realtime Vehicle Feed

**Endpoint:**  `https://apps.rideuta.com/tms/gtfs/Vehicle`

**Format:** GTFS Realtime Protobuf (FeedMessage containing FeedEntity records)

Each entity may include:

- `id`
- `trip_id`
- `route_id`
- `latitude`
- `longitude`
- `vehicle_timestamp`
- `source_timestamp`

This feed represents live vehicle positions across UTA bus and rail systems.

---

## Python Environment and Dependencies

### Python Version

Developed using Python 3.x and compatible with Lambda runtimes.

### Virtual Environment Setup

```bash
python -m venv venv
source venv/bin/activate
```

### Required Packages

```bash
pip install requests gtfs-realtime-bindings protobuf
```

- `requests`: Handles HTTP GET requests
- `gtfs-realtime-bindings`: Provides classes for decoding GTFS feeds
- `protobuf`: Supports binary Protobuf parsing

---

## Core Polling Script: `poll_gtfs_realtime.py`

**Purpose:** Fetch, decode, and extract realtime vehicle data into a structured format suitable for JSON.

**Key Steps:**

1. Send HTTP GET request to the UTA Vehicle endpoint
2. Decode the Protobuf binary response
3. Extract vehicle information
4. Add source timestamp
5. Return a list of Python dictionaries

**Local Test Command:**

```bash
python scripts/poll_gtfs_realtime.py
```

Expected output includes a printed feed timestamp and a JSON list of vehicle objects.

---

## AWS Lambda Wrapper: `poll_lambda.py`

**Purpose:** Expose the polling logic through an AWS Lambda handler so AWS can invoke it automatically.

**Handler Name**

`poll_lambda.lambda_handler`

**Responsibilities**

- Import and call `fetch_realtime_data()`
- Format the Lambda response with `statusCode` and JSON body

**Local Test Command:**

```bash
python scripts/poll_lambda.py
```

---

## AWS Deployment

**Lambda Configuration**

- Runtime: Python 3.x
- Handler: `poll_lambda.lambda_handler`
- Deployment Package Includes:
	- `poll_lambda.py`
	- `poll_gtfs_realtime.py`
	- Required dependencies (or Lambda layer)

**Testing in AWS Console**

- Create a test event (any name, body can be empty `{}`)
- Run the test
- A successful response returns `statusCode` 200 and JSON data

**CloudWatch Logs**

Each Lambda run shows:

- Feed timestamp
- Execution details

This confirms that the Lambda executed and retrieved live data.

---

## Scheduling with EventBridge (30-Second Polling)

To meet the project requirement, an EventBridge rule triggers the Lambda every 30 seconds.

**Schedule Expression:**

```
rate(1 minute)
```

**Target:**

The deployed Lambda function

Once configured:

- Lambda runs automatically
- Fresh vehicle data is retrieved every 30 seconds
- Logs appear in CloudWatch at the same interval

---

## Role in the Overall Pipeline

This component fulfills Part 3: Polling by:

- Successfully retrieving live vehicle data
- Structuring data into JSON-ready records
- Running automatically without manual intervention
- Serving as the data source for downstream streaming

It does not stream data directly to Kinesis. That responsibility belongs to Part 4, handled by another team member.

---

## Summary

The UTA GTFS Realtime Polling Service:

- Uses Python and Protobuf to decode realtime transit data
- Retrieves live vehicle positions from UTA
- Extracts and formats key fields
- Runs locally or in AWS Lambda
- Executes automatically every minute
- Produces JSON suitable for streaming and analytics

This completes the required functionality for Polling in the real-time data pipeline.

