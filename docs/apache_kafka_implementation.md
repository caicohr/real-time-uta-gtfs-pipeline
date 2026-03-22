# **EC2-Hosted Apache Kafka Pipeline (UTA Vehicle Tracker)**
**Project:** CS6830 Fundamentals of Data Engineering    
**Author:** Jerico Radin  

This project implements a real-time data pipeline on an AWS EC2 instance. It ingests live vehicle data from the UTA (Utah Transit Authority) API using a Python Producer, streams it through Apache Kafka, and visualizes it on a Streamlit Dashboard.

## **Architecture**

* **Producer:** Python script fetching data from https://apps.rideuta.com/tms/gtfs/Vehicle and publishing to Kafka.  
* **Broker:** Apache Kafka (wurstmeister/kafka) running in Docker.  
* **Zookeeper:** Manages the Kafka cluster state.  
* **Dashboard:** Streamlit application consuming Kafka messages and rendering a live map.  
* **Infrastructure:** AWS EC2 (Amazon Linux 2/2023), Docker, Docker Compose.

## **Prerequisites**

1. **AWS EC2 Instance:**  
   * **Type:** t2.micro (minimum) or t2.small (recommended for better performance).  
   * **OS:** Amazon Linux 2 or 2023\.  
   * **Security Group:**  
     * Inbound TCP **22** (SSH) \- Your IP only.  
     * Inbound TCP **8501** (Streamlit) \- Anywhere (0.0.0.0/0).  
2. **Software:**  
   * Docker & Docker Compose installed on the instance.

## **Installation & Setup**

### **1\. SSH into EC2**
```
ssh -i "your-key.pem" ec2-user@<public-ip>
```
### **2\. Install Docker (Amazon Linux)**
```
sudo yum update -y  
sudo yum install -y docker  
sudo service docker start  
sudo usermod -a -G docker ec2-user  
# Apply group changes without logging out  
newgrp docker
```

### **3\. Install Docker Compose**
```bash
# Install Docker Compose (Manual Binary Download)
sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
# Make it executable  
sudo chmod +x /usr/local/bin/docker-compose
# Verify installation  
docker-compose --version
```

### **4\. Fix "buildx" Error (If encountered)**

If docker-compose up fails with requires buildx 0.17, install the plugin manually:  
```bash
mkdir -p ~/.docker/cli-plugins/  
curl -SL https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-amd64 -o ~/.docker/cli-plugins/docker-buildx  
chmod +x ~/.docker/cli-plugins/docker-buildx
```
### **5\. Set Up Project Workspace**

Create the main folder and the required subdirectories for the services.  
```bash
# Create main folder and enter it  
mkdir uta-kafka-dashboard  
cd uta-kafka-dashboard

# Create subdirectories for Producer and Dashboard code  
mkdir producer dashboard
```
## **Project Source Code**

### **1\. Root Configuration (docker-compose.yml)**

*Location: Inside uta-kafka-dashboard/*  
*Critical settings for EC2:*

* **Memory Limits:** KAFKA\_HEAP\_OPTS prevents Java OOM crashes on t2.micro.  
* **Networking:** Service names (kafka) used for internal communication.
```yaml
services:
  zookeeper:
    image: wurstmeister/zookeeper
    ports:
      - "2181:2181"

  kafka:
    image: wurstmeister/kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_HEAP_OPTS: "-Xmx400M -Xms400M"
      KAFKA_CREATE_TOPICS: "uta-vehicle-positions:1:1"
    depends_on:
      - zookeeper
    restart: always

  producer:
    build: ./producer
    depends_on:
      - kafka
    restart: on-failure

  dashboard:
    build: ./dashboard
    ports:
      - "8501:8501"
    depends_on:
      - kafka
    restart: on-failure
```

### **2\. Producer Service**

This service fetches GTFS data and sends it to Kafka.  
**File:** producer/Dockerfile  
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY producer.py .
CMD ["python", "-u", "producer.py"]
```
**File:** producer/requirements.txt  
```txt
kafka-python
requests
protobuf
gtfs-realtime-bindings
```
**File:** producer/producer.py  
```python
import time
import json
import requests
from kafka import KafkaProducer
from google.transit import gtfs_realtime_pb2

# Docker Service Name for Kafka  
KAFKA_BROKER = "kafka:9092"
TOPIC = "uta-vehicle-positions"
GTFS_URL = "https://apps.rideuta.com/tms/gtfs/Vehicle"


def get_producer():
    # Retry logic waiting for Kafka to start  
    while True:
        try:
            return KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                value_serializer=lambda x: json.dumps(x).encode("utf-8")
            )
        except Exception as e:
            print(f"Waiting for Kafka... {e}")
            time.sleep(5)


def run():
    producer = get_producer()
    print("Producer connected to Kafka!")

    while True:
        try:
            response = requests.get(GTFS_URL)
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            count = 0
            for entity in feed.entity:
                if entity.HasField("vehicle"):
                    v = entity.vehicle
                    speed = v.position.speed if v.position.HasField("speed") else 0.0

                    data = {
                        "id": entity.id,
                        "latitude": v.position.latitude,
                        "longitude": v.position.longitude,
                        "speed_mph": round(speed * 2.23694, 1),
                        "timestamp": v.timestamp
                    }

                    producer.send(TOPIC, value=data)
                    count += 1

            producer.flush()
            print(f"Sent {count} records. Sleeping 30s...")
            time.sleep(30)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    run()
```

### **3\. Dashboard Service**

This service visualizes the data using Streamlit.  
**File:** dashboard/Dockerfile  
```dockerfile
FROM python:3.9-slim
WORKDIR /app
RUN pip install streamlit kafka-python pandas
COPY dashboard.py .
EXPOSE 8501
CMD ["streamlit", "run", "dashboard.py", "--server.address=0.0.0.0"]
```

File: dashboard/dashboard.py  
Features: Live/Replay modes, speed filters, region filtering, and advanced visualization.  
```python
import streamlit as st  
import json  
import pandas as pd  
import time  
from kafka import KafkaConsumer  
import socket  
import uuid

st.set_page_config(layout="wide", page_title="UTA Live Tracker")

# --- CONFIGURATION ---  
KAFKA_BROKER = "kafka:9092"  
TOPIC = "uta-vehicle-positions"

# --- SIDEBAR SETTINGS ---  
st.sidebar.header("Dashboard Settings")

# 1. Mode Selection (Live vs Replay)  
# Live: Reads from latest offset.  
# Replay: Generates a new group ID to read from 'earliest' (beginning of topic history).  
mode = st.sidebar.radio(  
    "Stream Mode:",   
    ('Live Mode', 'Replay Mode'),   
    help="Live: Shows current location. Replay: Plays back history from Kafka topic."  
)

# 2. Speed Filter  
min_speed = st.sidebar.slider("Filter: Min Speed (MPH)", 0, 60, 0)

# 3. Region Filter  
region_filter = st.sidebar.selectbox(  
    "Filter: Region",  
    ["All Regions", "Salt Lake City", "Ogden (North)", "Provo (South)"]  
)

# 4. Vehicle Specific Filter  
if 'all_vehicle_ids' not in st.session_state:  
    st.session_state['all_vehicle_ids'] = set()

selected_vehicles = st.sidebar.multiselect(  
    "Filter: Specific Vehicle ID",  
    options=sorted(list(st.session_state['all_vehicle_ids']))  
)

# Reset Button  
if st.sidebar.button("Reset Stream"):  
    st.session_state.clear()  
    st.rerun()

st.title("EC2-Hosted Kafka Stream")

# --- KAFKA CONSUMER ---  
@st.cache_resource  
def get_consumer(selected_mode):  
    # 1. Debug DNS  
    host = KAFKA_BROKER.split(':')[0]  
    try:  
        socket.gethostbyname(host)  
    except Exception as e:  
        return None, f"DNS ERROR: Cannot find host '{host}'. Check docker-compose service name."

    # 2. Configure Mode  
    if selected_mode == 'Live Mode':  
        offset = 'latest'  
        group = 'live-group-v2'  
    else:  
        # Generate random group ID to force reading from beginning  
        offset = 'earliest'  
        group = f'replay-{uuid.uuid4()}'

    try:  
        c = KafkaConsumer(  
            TOPIC,  
            bootstrap_servers=[KAFKA_BROKER],  
            auto_offset_reset=offset,  
            group_id=group,  
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),  
            request_timeout_ms=15000,  
            retry_backoff_ms=1000  
        )  
        return c, None  
    except Exception as e:  
        return None, f"CONNECTION ERROR: {str(e)}"

# Initialize Consumer based on Mode  
consumer, error_msg = get_consumer(mode)

# --- MAIN LOOP ---  
if 'vehicle_map' not in st.session_state:  
    st.session_state['vehicle_map'] = {}

if consumer:  
    try:  
        # Non-blocking poll  
        raw = consumer.poll(timeout_ms=500)  
          
        # Process Messages  
        for tp, msgs in raw.items():  
            for msg in msgs:  
                v_data = msg.value  
                st.session_state['vehicle_map'][v_data['id']] = v_data  
                st.session_state['all_vehicle_ids'].add(v_data['id'])

        # --- DATA VISUALIZATION ---  
        if st.session_state['vehicle_map']:  
            # Convert dict to DataFrame  
            df = pd.DataFrame(list(st.session_state['vehicle_map'].values()))  
              
            # Cleaning  
            if 'speed_mph' not in df.columns: df['speed_mph'] = 0.0  
            df['latitude'] = pd.to_numeric(df['latitude'])  
            df['longitude'] = pd.to_numeric(df['longitude'])

            # --- APPLY FILTERS ---  
              
            # 1. Speed  
            df = df[df['speed_mph'] >= min_speed]  
              
            # 2. Region (Approximate Latitudes)  
            if region_filter == "Ogden (North)":  
                df = df[df['latitude'] > 41.1]  
            elif region_filter == "Provo (South)":  
                df = df[df['latitude'] < 40.5]  
            elif region_filter == "Salt Lake City":  
                df = df[(df['latitude'] >= 40.5) & (df['latitude'] <= 41.1)]  
                  
            # 3. Specific Vehicle  
            if selected_vehicles:  
                df = df[df['id'].isin(selected_vehicles)]

            # Map Config  
            df['color'] = df['speed_mph'].apply(lambda x: '#00ff00' if x > 5 else '#ff0000')  
              
            # Layout  
            col1, col2 = st.columns([3, 1])  
              
            with col1:  
                st.map(df.rename(columns={'latitude': 'lat', 'longitude': 'lon'}), color='color', zoom=10, use_container_width=True)  
                  
            with col2:  
                st.metric("Active Vehicles", len(df))  
                  
                # Mode Indicator  
                if mode == 'Replay Mode':  
                    st.warning("Replay Mode")  
                else:  
                    st.success("Live Feed")  
                      
                st.write("#### Vehicle Feed")  
                display_cols = ['id', 'speed_mph']  
                if 'trip_id' in df.columns: display_cols.append('trip_id')  
                  
                st.dataframe(  
                    df[display_cols].sort_values(by='speed_mph', ascending=False),  
                    hide_index=True,  
                    use_container_width=True  
                )

        else:  
            st.info(f"Connected to Kafka ({mode}). Waiting for data...")  
              
    except Exception as e:  
        st.error(f"Runtime Error: {e}")  
else:  
    st.error("Failed to Connect to Kafka")  
    if error_msg: st.warning(error_msg)

# Refresh Rate  
time.sleep(1)  
st.rerun()

## **Running the Pipeline**

1. **Build and Start Containers:**  
   docker-compose up --build -d  
2. **Verify Containers:**  
   docker ps  
   *Ensure uta-pipeline-kafka-1 is Up and not restarting.*  
3. **View Logs (Debugging):**  
   # Check Producer (should see JSON data)  
   docker-compose logs -f producer

   # Check Dashboard (should see "Connected to Kafka")  
   docker-compose logs -f dashboard

4. Access Dashboard:  
   Open browser to http://<EC2_PUBLIC_IP>:8501
```
## **Troubleshooting Guide**

### **1. "Name or service not known"**

* **Cause:** Dashboard trying to connect to localhost or broker instead of the Docker service name.  
* **Fix:** Ensure dashboard.py uses kafka:9092 and docker-compose.yml service is named kafka.

### **2. Kafka Container Exits Immediately**

* **Cause:** Out of Memory (OOM) on t2.micro.  
* **Fix:** Add KAFKA_HEAP_OPTS: "-Xmx400M -Xms400M" to docker-compose.yml.

### **3. "NoBrokersAvailable" on Dashboard**

* **Cause:** Dashboard starts before Kafka is fully ready, or timeout is too short.  
* **Fix:** Increase request_timeout_ms in dashboard.py to 15000.

### **4. "Waiting for data..." forever**

* **Cause:** Producer failing or Consumer offset set to 'latest'.  
* **Fix:**  
  1. Check producer logs: docker-compose logs producer.  
  2. Set auto_offset_reset='earliest' in Consumer config.