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
    return boto3.client('kinesis', region_name=REGION_NAME)

client = get_kinesis_client()

# --- HELPER FUNCTIONS ---

def get_initial_iterator(mode):
    """
    LATEST: Start reading from now.
    TRIM_HORIZON: Start reading from the oldest record in the stream (up to 24h).
    """
    response = client.describe_stream(StreamName=STREAM_NAME)
    shard_id = response['StreamDescription']['Shards'][0]['ShardId']
    
    iterator_type = 'LATEST' if mode == 'Live Mode' else 'TRIM_HORIZON'
    
    return client.get_shard_iterator(
        StreamName=STREAM_NAME,
        ShardId=shard_id,
        ShardIteratorType=iterator_type
    )['ShardIterator']

def fetch_records():
    """
    Fetches records using the SAVED iterator in session state.
    """
    # 1. Handle Mode Switching (Reset iterator if mode changes)
    if 'last_mode' not in st.session_state:
        st.session_state['last_mode'] = st.session_state.view_mode
        
    if st.session_state.view_mode != st.session_state['last_mode']:
        # Mode changed! Clear iterator to force a fresh start
        if 'shard_iterator' in st.session_state:
            del st.session_state['shard_iterator']
        st.session_state['vehicle_map'] = {} # Clear map for replay
        st.session_state['last_mode'] = st.session_state.view_mode

    # 2. Get Iterator if missing
    if 'shard_iterator' not in st.session_state:
        try:
            st.session_state['shard_iterator'] = get_initial_iterator(st.session_state.view_mode)
        except Exception as e:
            st.error(f"Error connecting to Kinesis: {e}")
            return [], 0

    # 3. Fetch Data
    try:
        response = client.get_records(
            ShardIterator=st.session_state['shard_iterator'],
            Limit=200 
        )
        # Store the pointer for the NEXT batch
        st.session_state['shard_iterator'] = response['NextShardIterator']
        
        data = []
        for r in response['Records']:
            json_data = json.loads(r['Data'])
            data.append(json_data)
            
        # Calculate Lag (Time difference between NOW and the record time)
        lag = 0
        if data:
            last_ts = data[-1].get('source_timestamp', time.time())
            lag = time.time() - last_ts
            
        return data, lag

    except Exception as e:
        # If iterator expires, clear it
        if 'shard_iterator' in st.session_state:
            del st.session_state['shard_iterator']
        return [], 0

# --- UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="UTA Bus Tracker")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("⚙️ Data Settings")

# 1. Mode Selection (Live vs Replay)
mode = st.sidebar.radio(
    "Stream Mode:", 
    ('Live Mode', 'Replay Mode'), 
    key="view_mode",
    help="Live: Shows current location. Replay: Plays back history from Kinesis."
)

# 2. Speed Filter
min_speed = st.sidebar.slider("Filter: Min Speed (MPH)", 0, 60, 0)

# 3. City/Region Filter (Lat/Lon Bounding Box Logic)
region_filter = st.sidebar.selectbox(
    "Filter: Region",
    ["All Regions", "Salt Lake City", "Ogden (North)", "Provo (South)"]
)

# 4. Vehicle Specific Filter
# We need to accumulate IDs seen so far to populate this list
if 'all_vehicle_ids' not in st.session_state:
    st.session_state['all_vehicle_ids'] = set()

selected_vehicles = st.sidebar.multiselect(
    "Filter: Specific Vehicle ID",
    options=sorted(list(st.session_state['all_vehicle_ids']))
)

# Reset Button
if st.sidebar.button("Reset Stream"):
    if 'shard_iterator' in st.session_state:
        del st.session_state['shard_iterator']
        st.session_state['vehicle_map'] = {}
    st.rerun()

st.title("UTA Real-Time Tracker")

# --- MAIN DATA LOOP ---
if 'vehicle_map' not in st.session_state:
    st.session_state['vehicle_map'] = {}

# Fetch Batch
new_records, lag_seconds = fetch_records()

# Update Cache
if new_records:
    for record in new_records:
        v_id = record['id']
        st.session_state['vehicle_map'][v_id] = record
        st.session_state['all_vehicle_ids'].add(v_id)

# --- DISPLAY LOGIC ---
if st.session_state['vehicle_map']:
    # Convert dict to DataFrame
    df = pd.DataFrame(list(st.session_state['vehicle_map'].values()))
    
    # Cleaning
    df['latitude'] = pd.to_numeric(df['latitude'])
    df['longitude'] = pd.to_numeric(df['longitude'])
    if 'speed_mph' not in df.columns: df['speed_mph'] = 0.0

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
    df['color'] = df['speed_mph'].apply(lambda x: '#00ff00' if x > 1 else '#ff0000')
    
    # Layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.map(df.rename(columns={'latitude': 'lat', 'longitude': 'lon'}), color='color', zoom=10, use_container_width=True)
        
    with col2:
        st.metric("Active Vehicles", len(df))
        
        # Lag Indicator
        if mode == 'Replay Mode':
            st.warning(f"Replay Lag: {lag_seconds/60:.1f} min behind")
        else:
            st.success("Live Feed")
            
        st.write("#### Vehicle List")
        st.dataframe(
            df[['id', 'speed_mph', 'latitude', 'longitude', 'trip_id']].sort_values(by='speed_mph', ascending=False),
            hide_index=True
        )

else:
    st.info("Just waiting for the data guys... We make sure Lambda is running")

# Refresh Rate
# Replay Mode runs faster to "catch up"
refresh_rate = 0.5 if mode == 'Replay Mode' else 2.0
time.sleep(refresh_rate)
st.rerun()