# **Parallel Pipeline Setup Guide (AWS CloudShell Method)**

**Project:** CS6830 Fundamentals of Data Engineering  
**Module:** Week 3 – Enhanced Polling & Dashboarding  
**Strategy:** Blue/Green Deployment (Parallel V2 Pipeline)  
**Author:** Jerico Radin

## **1. Overview**

To satisfy the Week 3 requirements (Speed tracking, Bearing, Map Visualization) without risking the integrity of the graded Week 2 pipeline, we established a **Parallel V2 Pipeline**.
We utilize **AWS CloudShell** to build and deploy the Lambda function. This ensures that all Python dependencies (protobuf, gtfs-realtime-bindings) are compiled in a native Linux environment, eliminating "it works on my machine" compatibility errors often seen when deploying from macOS/Windows.

### **Architecture Comparison**

| Component  | V1 Pipeline (Week 2 – Graded) | V2 Pipeline (Week 3 – Dev)        |
| :--------- | :---------------------------- | :-------------------------------- |
| **Lambda** | uta-gtfs-polling              | uta-polling-v2                    |
| **Stream** | uta_Gtfs_kinesis_stream       | uta_gtfs_kinesis_stream_v2        |
| **Logic**  | Basic Polling (ID, Lat, Lon)  | Enhanced Polling (Speed, Bearing) |
| **Status** | **PAUSED** (Trigger Disabled) | **ACTIVE** (1-min Trigger)        |

## **2. Infrastructure Setup**

### **Step 1: Create the V2 Kinesis Stream**

1. Log in to the AWS Console.
2. Navigate to **Kinesis Data Streams**.
3. Click **Create data stream**.
4. **Name:** `uta_gtfs_kinesis_stream_v2`
5. **Capacity Mode:** Provisioned (1 Shard).
6. Click **Create data stream**.

### **Step 2: Create the Placeholder Lambda**

1. Navigate to **AWS Lambda**.
2. Click **Create function**.
3. **Function name:** `uta-polling-v2`
4. **Runtime:** Python 3.14
5. **Architecture:** x86_64
6. Click **Create function**.

### **Step 3: Configure IAM Permissions (Critical)**

1. In the Lambda function overview, click the Configuration tab.
2. Select Permissions from the sidebar.
3. Click the Role name link (e.g., uta-polling-v2-role-xxxx) to open the IAM Console.
4. Click Add permissions -> Attach policies.
5. Search for AmazonKinesisFullAccess.
6. Check the box next to the policy and click Add permissions.
    * *Note: This permission is required for the Lambda to send data to the Kinesis stream.*

## **3. Building & Deploying Code (via CloudShell)**

We use AWS CloudShell to script the creation of the deployment package directly in the cloud.

### **Step 1: Launch CloudShell**

Click the **CloudShell icon (>_)** in the top navigation bar of the AWS Console. Wait for the terminal to initialize.

### **Step 2: Generate the Deployment Package**

Copy and paste the following block into CloudShell:

```bash
# 1. Setup Build Directory
mkdir -p lambda_build
cd lambda_build

# 2. Write Polling Logic (poll_gtfs_realtime.py)
# Extracts Speed, Bearing, and handles missing Route IDs
cat << 'EOF' > poll_gtfs_realtime.py
import requests
from google.transit import gtfs_realtime_pb2
import json

GTFS_RT_URL = "https://apps.rideuta.com/tms/gtfs/Vehicle"

def fetch_realtime_data():
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        response = requests.get(GTFS_RT_URL, timeout=10)
    except Exception:
        return []

    feed.ParseFromString(response.content)
    
    entity_list = []
    for entity in feed.entity:
        if entity.HasField('vehicle'):
            v = entity.vehicle
            
            # Extract Speed (m/s) and Bearing
            speed = v.position.speed if v.position.HasField('speed') else 0.0
            bearing = v.position.bearing if v.position.HasField('bearing') else 0.0
            
            entity_list.append({
                "id": entity.id,
                "trip_id": v.trip.trip_id,
                "latitude": v.position.latitude,
                "longitude": v.position.longitude,
                "speed_mph": round(speed * 2.23694, 1), # Convert m/s to MPH
                "bearing": bearing,
                "vehicle_timestamp": v.timestamp,
                "source_timestamp": feed.header.timestamp
            })
    return entity_list
EOF

# 3. Write Lambda Handler (poll_lambda.py)
cat << 'EOF' > poll_lambda.py
import json
import boto3
from poll_gtfs_realtime import fetch_realtime_data

KINESIS_STREAM_NAME = "uta-gtfs-kinesis-stream-v2"

def lambda_handler(event, context):
    print(f"Starting poll for stream: {KINESIS_STREAM_NAME}")
    
    # 1. Fetch Data
    try:
        data = fetch_realtime_data()
    except Exception as e:
        print(f"CRITICAL ERROR fetching GTFS data: {e}")
        return {"statusCode": 500, "body": str(e)}

    print(f"Fetched {len(data)} vehicles from UTA API.")
    
    if not data:
        print("Warning: Received empty data list from UTA.")
        return {"statusCode": 200, "body": "No data fetched"}

    # 2. Initialize Client
    try:
        kinesis_client = boto3.client('kinesis')
    except Exception as e:
        print(f"ERROR initializing Kinesis client: {e}")
        return {"statusCode": 500, "body": "AWS Client Error"}

    # 3. Batch and Send
    records = []
    success_count = 0
    
    for row in data:
        # V1 did .encode('utf-8'). It's safer to be explicit like V1.
        data_bytes = json.dumps(row).encode('utf-8')
        
        records.append({
            'Data': data_bytes, 
            'PartitionKey': str(row['id'])
        })
        
        # Send batch if full
        if len(records) == 500:
            try:
                response = kinesis_client.put_records(StreamName=KINESIS_STREAM_NAME, Records=records)
                fail_count = response['FailedRecordCount']
                if fail_count > 0:
                    print(f"Error: {fail_count} records failed in this batch.")
                success_count += (len(records) - fail_count)
                records = []
            except Exception as e:
                print(f"ERROR sending batch: {e}")

    # Send remaining records
    if records:
        try:
            response = kinesis_client.put_records(StreamName=KINESIS_STREAM_NAME, Records=records)
            fail_count = response['FailedRecordCount']
            if fail_count > 0:
                print(f"Error: {fail_count} records failed in final batch.")
            success_count += (len(records) - fail_count)
        except Exception as e:
            print(f"ERROR sending final batch: {e}")
            # Common error: ResourceNotFoundException (Wrong Stream Name)
            # Common error: AccessDeniedException (Wrong IAM Role)

    print(f"Successfully sent {success_count} records to Kinesis.")
    return {
        "statusCode": 200, 
        "body": f"Sent {success_count} records"
    }
EOF

# 4. Install Dependencies (Robust Strategy)
# Step A: Install binary dependencies (requests, protobuf) into current dir
pip install requests protobuf "urllib3<1.27" -t . --upgrade

# Step B: Install bindings into a TEMP directory to prevent conflicts
mkdir temp_gtfs
pip install gtfs-realtime-bindings -t temp_gtfs --no-deps

# Step C: Manually merge the 'transit' folder
# This ensures we have both google/protobuf AND google/transit
cp -r temp_gtfs/google/transit google/
cp -r temp_gtfs/gtfs_realtime_bindings* .
rm -rf temp_gtfs

# 5. Create Zip Package
zip -r deploy_package.zip .
```

### **Step 3: Deploy to Lambda**

```bash
# 1. Upload Code
aws lambda update-function-code \
    --function-name uta-polling-v2 \
    --zip-file fileb://deploy_package.zip

# 2. Update Configuration (Critical Fix)
# - Sets Handler to 'poll_lambda.lambda_handler' (instead of default lambda_function.lambda_handler)
# - Increases Timeout to 30 seconds
aws lambda update-function-configuration \
    --function-name uta-polling-v2 \
    --handler poll_lambda.lambda_handler \
    --timeout 30
```

*Expected Output:* JSON response showing `LastUpdateStatus: "Successful"`.

## **4. Configuration & Activation**

### **Configure Triggers**

1. Go to **Lambda Console → uta-polling-v2**.
2. Click **Configuration → Triggers**.
3. Click **Add trigger**.
4. Select **EventBridge (CloudWatch Events)**.
5. Create a new rule:

   * **Rule name:** `Every1MinuteV2`
   * **Schedule expression:** `rate(1 minute)`
6. Click **Add**.

## **5. Local Dashboard Setup**

To visualize the data, we create a containerized Python application.
Run the following commands in your **local project root** (not CloudShell) to create the necessary files.

---

### **Step 1: Create Directory**

```bash
mkdir -p docker_dashboard
```

---

### **Step 2: Create Requirements File (`docker_dashboard/requirements.txt`)**

```
boto3
streamlit
pandas
watchdog
```

---

### **Step 3: Create Dockerfile (`docker_dashboard/Dockerfile`)**

```dockerfile
# Use python slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "dashboard.py", "--server.address=0.0.0.0"]
```

---

### **Step 4: Create Dashboard Logic (`docker_dashboard/dashboard.py`)**

This script connects to the V2 Kinesis stream and visualizes vehicle speed and location.

```python
import time
import json
import boto3
import pandas as pd
import streamlit as st

# --- CONFIGURATION ---
STREAM_NAME = "uta-gtfs-kinesis-stream-v2"
REGION_NAME = "us-east-1"

@st.cache_resource
def get_kinesis_client():
    return boto3.client("kinesis", region_name=REGION_NAME)

client = get_kinesis_client()

def fetch_records():
    """Fetch latest data from Kinesis"""

    # Initialize iterator if needed
    if "shard_iterator" not in st.session_state:
        try:
            response = client.describe_stream(StreamName=STREAM_NAME)
            shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
            st.session_state["shard_iterator"] = client.get_shard_iterator(
                StreamName=STREAM_NAME,
                ShardId=shard_id,
                ShardIteratorType="LATEST"
            )["ShardIterator"]
        except Exception as e:
            st.error(f"Error connecting to Kinesis: {e}")
            return []

    try:
        response = client.get_records(
            ShardIterator=st.session_state["shard_iterator"],
            Limit=100
        )
        st.session_state["shard_iterator"] = response["NextShardIterator"]

        data = []
        for r in response["Records"]:
            json_data = json.loads(r["Data"])
            data.append(json_data)
        return data

    except Exception:
        # If iterator expires, reset it
        if "shard_iterator" in st.session_state:
            del st.session_state["shard_iterator"]
        return []

# --- UI SETUP ---
st.set_page_config(layout="wide", page_title="UTA Bus Tracker")
st.title("🚎 UTA Real-Time Tracker")

# Sidebar
min_speed = st.sidebar.slider("Filter: Min Speed (MPH)", 0, 60, 0)

# --- MAIN LOGIC ---
if "vehicle_map" not in st.session_state:
    st.session_state["vehicle_map"] = {}

records = fetch_records()

# Update cache with latest vehicle positions
if records:
    for r in records:
        st.session_state["vehicle_map"][r["id"]] = r

# Display map & stats
if st.session_state["vehicle_map"]:
    df = pd.DataFrame(list(st.session_state["vehicle_map"].values()))

    # Ensure numeric fields
    df["latitude"] = pd.to_numeric(df["latitude"])
    df["longitude"] = pd.to_numeric(df["longitude"])

    # Handle older data without speed
    if "speed_mph" not in df.columns:
        df["speed_mph"] = 0.0

    # Apply filter
    df = df[df["speed_mph"] >= min_speed]

    # Color: Green if >1 mph, red if stopped
    df["color"] = df["speed_mph"].apply(
        lambda x: "#00ff00" if x > 1 else "#ff0000"
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        st.map(
            df.rename(columns={"latitude": "lat", "longitude": "lon"}),
            color="color",
            zoom=10,
            use_container_width=True,
        )

    with col2:
        st.metric("Vehicles Tracked", len(df))
        st.write("### Fastest Vehicles")
        st.dataframe(
            df[["id", "speed_mph"]]
            .sort_values(by="speed_mph", ascending=False)
            .head(10),
            hide_index=True
        )

else:
    st.info("Waiting for data stream... (Ensure Lambda v2 is running)")

# Refresh every 2 seconds
time.sleep(2)
st.rerun()
```

---

## **6. Execution**

### **Prerequisites**

* Docker Desktop installed
* Temporary AWS Credentials (Access Key, Secret, Session Token)

---

### **Run Command**

Navigate to the `docker_dashboard` folder:

```bash
# 1. Build the image
docker build -t uta-dashboard .
```

```bash
# 2. Run with credentials (replace ... with your real values)
docker run --rm -it \
  -p 8501:8501 \
  -e AWS_ACCESS_KEY_ID="ASIA..." \
  -e AWS_SECRET_ACCESS_KEY="wJalr..." \
  -e AWS_SESSION_TOKEN="IQoJ..." \
  -e AWS_DEFAULT_REGION="us-east-1" \
  uta-dashboard
```

---

### **Validation**

Open: **[http://localhost:8501](http://localhost:8501)**

* **Success:** green (moving) & red (stopped) vehicles appear
* **Filter:** adjust minimum speed
* **Status:** updates live every 2 seconds