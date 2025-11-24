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
 - Runs automatically every 1 minute using AWS Lambda and EventBridge

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
├── requirements.txt
└── …
```

Note: Dependencies are not committed to source control. See "Managing Dependencies (Not Stored in Repo)" below.

## File Responsibilities

`poll_gtfs_realtime.py`
- Fetches realtime data from the UTA GTFS endpoint
- Decodes the Protobuf feed
- Extracts vehicle fields
- Returns JSON-ready dictionaries

`poll_lambda.py`
- Wraps the polling code in an AWS Lambda handler
- Returns the data in the required Lambda response format
- Serves as the deployed entrypoint executed every 1 minute

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

### Packages Required for Lambda

The polling Lambda requires the following Python packages to run in the Lambda execution environment:

- `requests`
- `protobuf`
- `gtfs-realtime-bindings`

These packages must be included in the deployment package (or provided via a Lambda layer) so the function can import them at runtime.

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
 - Required dependencies (or Lambda layer). Dependencies are not committed to source control; install them during deployment or use a Lambda layer.

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

## Managing Dependencies (Not Stored in Repo)

- Dependencies are declared in `requirements.txt` and installed at deployment time.
- The repository includes only the application code: `poll_gtfs_realtime.py` and `poll_lambda.py`.
- Dependency installation occurs during packaging or in the CI/CD deployment step; dependency directories (such as `lambda_package/`) are not committed to source control.

---

## Building the Lambda Deployment Package

Follow these steps to build a deployment package locally (or replicate in CI/CD):

1. Create a packaging directory:

```bash
mkdir -p lambda_package
```

2. Install dependencies into the folder:

```bash
pip install -r requirements.txt -t lambda_package/
```

3. Copy the application files into `lambda_package/`:

```bash
cp scripts/poll_gtfs_realtime.py scripts/poll_lambda.py lambda_package/
```

4. Zip the folder for Lambda deployment:

```bash
cd lambda_package
zip -r ../lambda_package.zip .
cd ..
```

Deploy `lambda_package.zip` to Lambda or upload the contents to an S3 bucket and create a new Lambda version.

**Recommended .gitignore entries**

Add the following to `.gitignore` to avoid committing build artifacts and virtual environments:

```
lambda_package/
venv/
*.zip
```

---

## Installing Dependencies for Lambda

If you prefer to build the Lambda deployment package without using a `requirements.txt` file, follow these steps to install the necessary packages directly into the package directory and create the deployment zip.

1. Create a packaging directory:

```bash
mkdir -p lambda_package
```

2. Copy the application files into `lambda_package/`:

```bash
cp scripts/poll_gtfs_realtime.py scripts/poll_lambda.py lambda_package/
```

3. Install the required packages directly into the package folder:

```bash
pip install requests protobuf gtfs-realtime-bindings -t lambda_package/
```

4. Zip the folder for Lambda deployment:

```bash
cd lambda_package
zip -r ../lambda_package.zip .
cd ..
```

5. Upload `lambda_package.zip` to AWS Lambda and set the handler to `poll_lambda.lambda_handler`.

Notes:

- Do not commit `lambda_package/` or the `lambda_package.zip` file to source control. Only the scripts (`poll_gtfs_realtime.py` and `poll_lambda.py`) should remain in the repository.
- Users are expected to build the deployment package themselves by following these instructions (or build it in CI/CD). This keeps dependencies out of the repo and avoids large binary artifacts in source control.

---

## Scheduling with EventBridge (1-Minute Polling)

The Lambda function runs every 1 minute. Note that EventBridge does not support sub-minute schedules (for example, 30-second intervals).

Key scheduling details:

- The Lambda function runs every 1 minute
- The schedule expression is `rate(1 minute)`
- EventBridge does not support 30-second schedules

**Schedule Expression:**

```
rate(1 minute)
```

**Target:**

The deployed Lambda function

Once configured:

- Lambda runs automatically
- Fresh vehicle data is retrieved every 1 minute
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

