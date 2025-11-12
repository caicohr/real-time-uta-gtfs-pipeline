# Data Discovery Report  
**Data Discovery & Description Lead – Chase Powers**  
*Covers: Data Discovery + Data Description 

---

## Tasks  
- Locate and verify the stable URL for the UTA GTFS Schedule ZIP  
- Read the GTFS Schedule documentation (https://gtfs.org/schedule/reference/)  
- Manually download the ZIP and load the CSVs into DuckDB  
- Inspect the tables (`routes`, `trips`, `stops`, `stop_times`, `calendar`, etc.)  
- Create an Entity–Relationship Diagram (ERD) showing PK/FK links  
- Write a short report explaining each table and how they relate  

---

## Data Source Verification  
- **Stable URL:** https://gtfsfeed.rideuta.com/GTFS.zip  
- **Description:** This URL provides the official Utah Transit Authority (UTA) GTFS Schedule feed.  
- **Format:** General Transit Feed Specification (GTFS) — multiple `.txt` CSV files.  

### GTFS Files Included  
- `agency.txt` – Transit agency information  
- `routes.txt` – Route-level definitions  
- `trips.txt` – Scheduled trips  
- `stops.txt` – Stop coordinates and names  
- `stop_times.txt` – Stop sequences + arrival/departure times  
- `calendar.txt` – Weekly recurring service  
- `calendar_dates.txt` – Service exceptions  
- `shapes.txt` – Geographic shapes for route paths  
- `feed_info.txt` – Metadata about the feed  

---

## Data Load and Inspection  

After extracting the ZIP into `data/GTFS/`, the following statements were executed inside DuckDB.

### Table Creation (DuckDB)

```sql
CREATE TABLE agency AS
SELECT * FROM read_csv_auto('agency.txt', header = TRUE);

CREATE TABLE routes AS
SELECT * FROM read_csv_auto('routes.txt', header = TRUE);

CREATE TABLE trips AS
SELECT * FROM read_csv_auto('trips.txt', header = TRUE);

CREATE TABLE stops AS
SELECT * FROM read_csv_auto('stops.txt', header = TRUE);

CREATE TABLE stop_times AS
SELECT * FROM read_csv_auto('stop_times.txt', header = TRUE);

CREATE TABLE calendar AS
SELECT * FROM read_csv_auto('calendar.txt', header = TRUE);

CREATE TABLE calendar_dates AS
SELECT * FROM read_csv_auto('calendar_dates.txt', header = TRUE);

CREATE TABLE shapes AS
SELECT * FROM read_csv_auto('shapes.txt', header = TRUE);

CREATE TABLE feed_info AS
SELECT * FROM read_csv_auto('feed_info.txt', header = TRUE);

### Verification Query 

SELECT 'agency' AS table_name, COUNT(*) AS row_count FROM agency
UNION ALL SELECT 'routes', COUNT(*) FROM routes
UNION ALL SELECT 'trips', COUNT(*) FROM trips
UNION ALL SELECT 'stops', COUNT(*) FROM stops
UNION ALL SELECT 'stop_times', COUNT(*) FROM stop_times
UNION ALL SELECT 'calendar', COUNT(*) FROM calendar
UNION ALL SELECT 'calendar_dates', COUNT(*) FROM calendar_dates
UNION ALL SELECT 'shapes', COUNT(*) FROM shapes
UNION ALL SELECT 'feed_info', COUNT(*) FROM feed_info;