# UTA GTFS Realtime Data Polling & Streaming Pipeline

**Author:** Chase Powers – Polling & Lambda Deployment Lead  
**Course:** CS6830 – Fundamentals of Data Engineering (Fall 2025)

---

## Overview

This document explains the implementation and deployment of the complete GTFS Realtime polling and streaming pipeline for the Utah Transit Authority (UTA). This integrated system retrieves live vehicle location data from the UTA GTFS endpoint, processes it into clean JSON format, and immediately streams it into Amazon Kinesis Data Streams for downstream real-time analytics.

The complete pipeline performs the following functions:

- **Polls** the UTA GTFS Realtime Vehicle Positions API every minute
- **Decodes** the binary Protocol Buffers feed
- **Extracts** key fields for each vehicle (id, route, position, timestamps)
- **Formats** the data into clean JSON dictionaries
- **Streams** all records into Amazon Kinesis Data Streams for downstream consumption
- **Runs automatically** every 1 minute using AWS Lambda and EventBridge

This component completes both **Part 3 (Polling)** and **Part 4 (Streaming)** of the project pipeline as a unified, production-ready system that continuously feeds fresh vehicle data into the data lake.

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
### Requirements File

The deployment process requires a `requirements.txt` file in the project root.  
This file must list the Python dependencies used by the Lambda function:

requests
protobuf
gtfs-realtime-bindings

These dependencies are installed into the deployment package during the build step:

pip install -r requirements.txt -t lambda_package/

Note: AWS Lambda includes `boto3` by default, so it does **not** need to be added to the requirements file.

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

This integrated component fulfills both **Part 3 (Polling)** and **Part 4 (Streaming)** by:

- **Part 3:** Successfully retrieving live vehicle data every minute, decoding the Protobuf format, and extracting key fields
- **Part 4:** Immediately converting decoded records into JSON and streaming them into Kinesis in batches
- Running the entire pipeline automatically without manual intervention
- Providing a continuous, low-latency feed of fresh vehicle positions to downstream consumers

The same Lambda function handles both responsibilities in a single execution, ensuring that fresh data moves from the UTA API to Kinesis with minimal delay each minute.

---

## Summary

The UTA GTFS Realtime Pipeline:

- Uses Python and Protobuf to decode realtime transit data from the UTA GTFS endpoint
- Retrieves live vehicle positions and extracts key fields every minute
- Formats data into clean JSON dictionaries ready for streaming
- Runs locally for testing or in AWS Lambda for production
- Executes automatically every 1 minute via EventBridge scheduling
- Streams all decoded records directly into Amazon Kinesis Data Streams
- Provides downstream consumers with fresh, validated vehicle position updates

This establishes a complete, fully-automated real-time ingestion pipeline that continuously updates the data lake with fresh vehicle positions. The same Lambda function that polls the GTFS feed also handles all streaming to Kinesis, ensuring a seamless, low-latency flow of data from source to consumption.

---

# Streaming GTFS Realtime Data to Amazon Kinesis Data Streams
---

## Streaming Architecture

1. **EventBridge** triggers the Lambda function every 1 minute.  
2. The Lambda executes `fetch_realtime_data()` to retrieve and decode the GTFS feed.  
3. The decoded entities are converted into clean JSON dictionaries.  
4. The Lambda batches the records and sends them to Kinesis using `put_records`.  
5. Downstream consumers read JSON from the stream and check correctness and freshness.

This satisfies the requirement:  
**“Your code should put the decoded data into a nice form (JSON) and send it to a streaming service.”**

---

## Kinesis Data Stream Used

Records are sent to the **`uta_Gtfs_kinesis_stream`** stream: 

Each record includes:

- JSON-encoded GTFS entity data  
- A partition key based on the vehicle `id`  
- Timestamps enabling freshness validation  

Example JSON Kinesis record:

```json
{
  "id": "1234",
  "trip_id": "820145",
  "route_id": "455",
  "latitude": 40.31,
  "longitude": -111.70,
  "vehicle_timestamp": 1712351525,
  "source_timestamp": 1712351500
}
```

## Streaming Implementation

The streaming functionality is implemented in `poll_lambda.py` using the following function:

### `send_to_kinesis(stream_name, data_list)`

This function:

- Converts each GTFS entity dictionary to a JSON string  
- Encodes JSON into UTF-8 bytes  
- Uses the entity `id` as the partition key  
- Sends all records using the efficient `put_records` batch API  
- Logs failures and Kinesis responses to CloudWatch  

Batching improves throughput and ensures all entities are transmitted each minute.

---

## Testing the Streaming Component

To meet the requirement:  
**“Ensure that you can receive and decode the data from Amazon Kinesis. Check correctness and freshness.”**

###  1. Validate in CloudWatch Logs

Lambda logs will show:

- A tabular print of decoded GTFS data  
- The results of the Kinesis batch send  
- Any failed records or API errors  

###  2. Validate in the Kinesis Console

1. Go to **Amazon Kinesis → Data Streams**  
2. Open `uta_Gtfs_kinesis_stream`  
3. Use **Data Viewer** to inspect incoming records  

You should see new JSON records every minute.

###  3. Freshness Verification Using Timestamps

Each record contains:

- `vehicle_timestamp` — time vehicle GPS was recorded  
- `source_timestamp` — GTFS feed timestamp  

Consumers can confirm:

- Records are recent  
- Data advances each minute  
- No stale or lagging updates  

---

## Role in the Overall Pipeline

This streaming component completes Part 4 by:

- Sending structured JSON GTFS data into Kinesis  
- Enabling real-time downstream analytics  
- Ensuring freshness validation through timestamps  
- Operating automatically without manual intervention  

This completes the real-time polling + streaming ingestion stage of the pipeline.