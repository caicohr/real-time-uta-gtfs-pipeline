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
```

### Verification Query 

```sql
SELECT 'agency' AS table_name, COUNT(*) AS row_count FROM agency
UNION ALL SELECT 'routes', COUNT(*) FROM routes
UNION ALL SELECT 'trips', COUNT(*) FROM trips
UNION ALL SELECT 'stops', COUNT(*) FROM stops
UNION ALL SELECT 'stop_times', COUNT(*) FROM stop_times
UNION ALL SELECT 'calendar', COUNT(*) FROM calendar
UNION ALL SELECT 'calendar_dates', COUNT(*) FROM calendar_dates
UNION ALL SELECT 'shapes', COUNT(*) FROM shapes
UNION ALL SELECT 'feed_info', COUNT(*) FROM feed_info;
```

---

## Docker Reproduction Instructions
**Reproducibility & Infrastructure – Jerico Radin**
*Covers: Docker Containerization + Environment Setup*

To ensure reproducibility of our data discovery process, we have containerized the environment. Follow these steps to spin up a DuckDB instance and execute the verification queries without needing to install DuckDB locally.

### 1\. Directory Structure
Ensure your project is structured as follows before running the container. (Note: The actual data files are git-ignored, but the folder structure must exist).

```text
project-root/
├── Dockerfile
├── data/
│   └── GTFS/           <-- Unzipped .txt files must be in here
│       ├── agency.txt
│       ├── routes.txt
│       └── ...
````

### 2\. The Dockerfile

Create a file named `Dockerfile` in your project root with the following content. This sets up the official DuckDB image and defines the working directory.

```dockerfile
# Use the official DuckDB image
FROM duckdb/duckdb:latest

# Set the working directory inside the container to /data
# This is where we will mount our local GTFS files
WORKDIR /data

# Default entrypoint is the DuckDB CLI
ENTRYPOINT ["duckdb"]
```

### 3\. Build the Image

Run the following command in your terminal from the project root to build the Docker image:

```bash
docker build -t uta-gtfs-discovery .
```

### 4\. Run the Container

Run the container, mounting your local `data/GTFS` folder to the container's `/data` directory. This allows the container to see your local CSV files.

**Mac/Linux:**

```bash
docker run --rm -it \
  -v "$(pwd)/data/GTFS":/data \
  uta-gtfs-discovery
```

**Windows (PowerShell):**

```powershell
docker run --rm -it `
  -v "${PWD}/data/GTFS":/data `
  uta-gtfs-discovery
```

- Volume Mounting (-v): By mounting $(pwd)/data/GTFS to /data inside the container, the container sees the CSV files as if they are in its root folder. This means your SQL queries read_csv_auto('agency.txt'...) work exactly as written, with no path modification needed.

- Interactivity: Using -it drops you right into the shell.

- Cleanup: The --rm flag ensures the container is deleted after you exit the DuckDB shell, keeping your environment clean.

### 5\. Execute Verification

Once the container starts, you will be inside the DuckDB CLI. You can now execute the verification queries directly. Because we mounted the files to the current working directory, you do not need to specify complex paths.

**Test Query:**

```sql
SELECT count(*) FROM read_csv_auto('trips.txt', header=True);
```

Full Verification Script: You can now copy and paste the SQL block from the "Data Load and Inspection" section above directly into this terminal.

### 6\. Execute VerificationExiting

To exit the DuckDB session and stop the container:

    Press Ctrl + D

(Alternatively, type .exit and press Enter)