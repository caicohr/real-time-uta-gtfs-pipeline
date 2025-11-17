/* ================================================================
PART 4: BATCH TRANSFORMATION
Description: Cleans raw GTFS data and creates optimized Parquet tables.
Source: uta_gtfs_raw (CSV/Text)
Target: uta_gtfs_clean (Parquet)
================================================================
*/

-- 1. Create a separate database for clean data (Optional, or just use prefix)
CREATE DATABASE IF NOT EXISTS uta_gtfs_clean;

/* ----------------------------------------------------------------
TABLE: STOPS
Transformations:
- Cast IDs to String
- Cast Lat/Lon to Double
- Filter: Remove invalid coordinates (Data Quality Check)
----------------------------------------------------------------
*/
CREATE TABLE uta_gtfs_clean.stops
WITH (
  format = 'PARQUET',
  external_location = 's3://[YOUR_BUCKET_NAME]/clean/stops/',
  partitioned_by = ARRAY[]
) AS
SELECT 
  CAST(stop_id AS VARCHAR) AS stop_id,
  stop_name,
  CAST(stop_lat AS DOUBLE) AS stop_lat,
  CAST(stop_lon AS DOUBLE) AS stop_lon,
  parent_station
FROM uta_gtfs_raw.stops
WHERE 
  -- Data Quality Rule: Coordinates must be valid
  cast(stop_lat as double) BETWEEN -90 AND 90 
  AND cast(stop_lon as double) BETWEEN -180 AND 180;


/* ----------------------------------------------------------------
TABLE: ROUTES
Transformations:
- Cast Route Type to Integer
----------------------------------------------------------------
*/
CREATE TABLE uta_gtfs_clean.routes
WITH (
  format = 'PARQUET',
  external_location = 's3://[YOUR_BUCKET_NAME]/clean/routes/'
) AS
SELECT 
  CAST(route_id AS VARCHAR) AS route_id,
  route_short_name,
  route_long_name,
  CAST(route_type AS INTEGER) AS route_type
FROM uta_gtfs_raw.routes;


/* ----------------------------------------------------------------
TABLE: TRIPS
Transformations:
- Ensure Foreign Keys (route_id) are strings to match routes table
----------------------------------------------------------------
*/
CREATE TABLE uta_gtfs_clean.trips
WITH (
  format = 'PARQUET',
  external_location = 's3://[YOUR_BUCKET_NAME]/clean/trips/'
) AS
SELECT 
  CAST(route_id AS VARCHAR) AS route_id,
  CAST(service_id AS VARCHAR) AS service_id,
  CAST(trip_id AS VARCHAR) AS trip_id,
  trip_headsign,
  CAST(direction_id AS INTEGER) AS direction_id,
  shape_id
FROM uta_gtfs_raw.trips;


/* ----------------------------------------------------------------
TABLE: STOP_TIMES
Transformations:
- Handle arrival_time (keep as string for now, GTFS times can be > 24:00)
- Ensure sequence is integer
----------------------------------------------------------------
*/
CREATE TABLE uta_gtfs_clean.stop_times
WITH (
  format = 'PARQUET',
  external_location = 's3://[YOUR_BUCKET_NAME]/clean/stop_times/'
) AS
SELECT 
  CAST(trip_id AS VARCHAR) AS trip_id,
  arrival_time,
  departure_time,
  CAST(stop_id AS VARCHAR) AS stop_id,
  CAST(stop_sequence AS INTEGER) AS stop_sequence
FROM uta_gtfs_raw.stop_times;

/* ----------------------------------------------------------------
Verify the tables:
Once you have run the queries, check your "Clean" data:
    In the Athena database dropdown, switch to uta_gtfs_clean.
    Run a Join query to see if the relationships work (as shown in our ERD logic):
----------------------------------------------------------------
*/

-- Check: Connect Routes to Trips to Stops
SELECT 
    r.route_short_name, 
    t.trip_headsign, 
    s.stop_name 
FROM uta_gtfs_clean.routes r
JOIN uta_gtfs_clean.trips t ON r.route_id = t.route_id
JOIN uta_gtfs_clean.stop_times st ON t.trip_id = st.trip_id
JOIN uta_gtfs_clean.stops s ON st.stop_id = s.stop_id
LIMIT 10;