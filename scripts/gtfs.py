import boto3
import json
import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.express as px
import pandas as pd

# --- AWS Kinesis client setup ---
kinesis_client = boto3.client("kinesis", region_name="us-east-1a")  # adjust region
stream_name = "uta_Gtfs_kinesis_stream"
shard_id = "shardId-000000000000"   # explicit shard

# Global shard iterator
shard_iterator = None

def init_iterator():
    """Initialize shard iterator from TRIM_HORIZON (earliest available)."""
    global shard_iterator
    shard_iterator = kinesis_client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="TRIM_HORIZON"
    )["ShardIterator"]

def get_records(limit=100):
    """Fetch records from Kinesis stream and return as DataFrame."""
    global shard_iterator
    if shard_iterator is None:
        init_iterator()

    records_response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=limit)
    shard_iterator = records_response["NextShardIterator"]  # advance iterator

    records = [json.loads(r["Data"]) for r in records_response["Records"]]
    return pd.DataFrame(records) if records else pd.DataFrame()

# --- Known schema from Lambda ---
KNOWN_COLUMNS = [
    "id", "trip_id", "route_id",
    "latitude", "longitude",
    "vehicle_timestamp", "source_timestamp"
]

graph_types = ["Map", "Scatter", "Line", "Bar"]

# --- Dash app setup ---
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("UTA Vehicle Tracking Dashboard"),

    html.Div([
        html.Label("Select X-axis column"),
        dcc.Dropdown(
            id="x-col",
            options=[{"label": c, "value": c} for c in KNOWN_COLUMNS],
            value="latitude"
        ),

        html.Label("Select Y-axis column"),
        dcc.Dropdown(
            id="y-col",
            options=[{"label": c, "value": c} for c in KNOWN_COLUMNS],
            value="longitude"
        ),

        html.Label("Select Graph Type"),
        dcc.Dropdown(
            id="graph-type",
            options=[{"label": g, "value": g} for g in graph_types],
            value="Map"
        )
    ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top"}),

    dcc.Interval(id="interval-component", interval=5000, n_intervals=0),
    dcc.Graph(id="vehicle-graph")
])

@app.callback(
    Output("vehicle-graph", "figure"),
    [Input("interval-component", "n_intervals"),
     Input("x-col", "value"),
     Input("y-col", "value"),
     Input("graph-type", "value")]
)
def update_graph(n, x_col, y_col, graph_type):
    df = get_records()
    if df.empty:
        return px.scatter(title="No data yet")

    if graph_type == "Map":
        fig = px.scatter_mapbox(
            df, lat="latitude", lon="longitude",
            hover_name="id", hover_data=KNOWN_COLUMNS,
            zoom=10, height=600
        )
        fig.update_layout(mapbox_style="open-street-map")
    elif graph_type == "Scatter":
        fig = px.scatter(df, x=x_col, y=y_col, hover_data=KNOWN_COLUMNS)
    elif graph_type == "Line":
        fig = px.line(df, x=x_col, y=y_col, hover_data=KNOWN_COLUMNS)
    elif graph_type == "Bar":
        fig = px.bar(df, x=x_col, y=y_col, hover_data=KNOWN_COLUMNS)
    else:
        fig = px.scatter(df, x=x_col, y=y_col)

    return fig

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8050, ssl_context='adhoc')
