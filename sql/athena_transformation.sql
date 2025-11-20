/* ================================================================
PART 4: BATCH TRANSFORMATION (Views)
Description: Creates logical views that clean data on-the-fly.
Source: uta_gtfs_raw (CSV/Text)
Target: uta_gtfs_clean (Logical Views)
================================================================
*/

CREATE DATABASE IF NOT EXISTS uta_gtfs_clean;

/* ----------------------------------------------------------------
VIEW: STOPS
Transformations: Cast types, Filter invalid coordinates
----------------------------------------------------------------
*/
CREATE OR REPLACE VIEW uta_gtfs_clean.stops AS
SELECT 
  CAST(stop_id AS VARCHAR) AS stop_id,
  stop_name,
  CAST(stop_lat AS DOUBLE) AS stop_lat,
  CAST(stop_lon AS DOUBLE) AS stop_lon,
  parent_station
FROM uta_gtfs_raw.stops
WHERE 
  CAST(stop_lat AS DOUBLE) BETWEEN -90 AND 90 
  AND CAST(stop_lon AS DOUBLE) BETWEEN -180 AND 180;

/* ----------------------------------------------------------------
VIEW: ROUTES
Transformations: Cast Route Type to Integer
----------------------------------------------------------------
*/
CREATE OR REPLACE VIEW uta_gtfs_clean.routes AS
SELECT 
  CAST(route_id AS VARCHAR) AS route_id,
  route_short_name,
  route_long_name,
  CAST(route_type AS INTEGER) AS route_type
FROM uta_gtfs_raw.routes;

/* ----------------------------------------------------------------
VIEW: TRIPS
Transformations: Ensure Foreign Keys match
----------------------------------------------------------------
*/
CREATE OR REPLACE VIEW uta_gtfs_clean.trips AS
SELECT 
  CAST(route_id AS VARCHAR) AS route_id,
  CAST(service_id AS VARCHAR) AS service_id,
  CAST(trip_id AS VARCHAR) AS trip_id,
  trip_headsign,
  CAST(direction_id AS INTEGER) AS direction_id,
  shape_id
FROM uta_gtfs_raw.trips;

/* ----------------------------------------------------------------
VIEW: STOP_TIMES
Transformations: Type enforcement
----------------------------------------------------------------
*/
  CREATE OR REPLACE VIEW uta_gtfs_clean.stop_times AS
  SELECT 
    CAST(trip_id AS VARCHAR) AS trip_id,
    arrival_time,
    departure_time,
    CAST(stop_id AS VARCHAR) AS stop_id,
    CAST(stop_sequence AS INTEGER) AS stop_sequence
  FROM uta_gtfs_raw.stop_times;