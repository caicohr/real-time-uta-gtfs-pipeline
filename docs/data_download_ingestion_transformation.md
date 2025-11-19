# Data Ingestion & Transformation Guide

**Author:** Jerico Radin  
**Pipeline Stage:** Week 1 (Batch Processing)  
**Tech Stack:** AWS Lambda, S3, Glue, Athena

---

## 1. Architecture Overview
This pipeline fetches GTFS data from the official UTA endpoint, archives the raw history in an S3 Data Lake, automatically catalogs the schema, and transforms the data into clean Views for analysis.

* **Ingestion:** AWS Lambda (Serverless Python Script)
* **Storage:** Amazon S3 (Raw Data Lake)
* **Cataloging:** AWS Glue Crawler (Schema Discovery)
* **Transformation:** AWS Athena (SQL Views)

---

## 2. Ingestion Pipeline (AWS Lambda)
**Script Source:** `scripts/ingest_lambda.py`

We use AWS Lambda to download the ZIP file, extract contents, and upload them to S3 partitioned folders (`raw/YYYY-MM-DD/{table}/`).

### Step 2.1: Create the Function
1.  Log into the AWS Console and navigate to **Lambda**.
2.  Click **Create function**.
3.  **Function name:** `uta-gtfs-ingest`
4.  **Runtime:** Select `Python 3.14` (or newer).
5.  **Permissions:**
    * Expand "Change default execution role".
    * Select **Create a new role with basic Lambda permissions**.
    * Click **Create function**.
    * *Attach S3 Permissions:*
        * Once the function is created, go to the **Configuration** tab -> **Permissions**.
        * Click the **Role name** (this opens the IAM Console).
        * Click **Add permissions** -> **Attach policies**.
        * Search for `AmazonS3FullAccess`.
        * Select the checkbox and click **Add permissions**.
6.  Click **Create function**.

### Step 2.2: Configure Environment & Timeout
*Crucial Step: The default timeout is 3 seconds, which is too short for file downloading.*

1.  Navigate to the **Configuration** tab -> **General configuration**.
2.  Click **Edit**.
3.  Set **Timeout** to **5 min 0 sec**. Click **Save**.
4.  Navigate to **Environment variables** (left sidebar).
5.  Click **Edit** and add the following:
    * Key: `GTFS_FEED_URL` | Value: `https://gtfsfeed.rideuta.com/GTFS.zip`
    * Key: `BUCKET_NAME` | Value: `[YOUR_BUCKET_NAME]`
6.  Click **Save**.

### Step 2.3: Deploy Code
1.  Navigate to the **Code** tab.
2.  Open `scripts/ingest_lambda.py` in your local repo.
3.  Copy the entire content and paste it into the Lambda code editor (replacing the default code).
4.  Click **Deploy**.

### Step 2.4: Execution (Manual Trigger)
*Note: Due to lab restrictions on EventBridge (`events:PutRule`), we execute this function manually instead of scheduling it.*

1.  Click the **Test** tab in the Lambda Console.
2.  Create a new event (name it `TestRun`, leave JSON as default).
3.  Click the orange **Test** button.
4.  **Verify:** Wait for the "Succeeded" message. Check your S3 bucket to ensure folders (`stops/`, `routes/`, etc.) have been created inside `raw/YYYY-MM-DD/`.

---

## 3. Data Cataloging (AWS Glue)

We use an AWS Glue Crawler to automatically detect the schema of the raw CSV files and register them in the Data Catalog.

### Step 3.1: Configure Crawler
1.  Navigate to the **AWS Glue Console** -> **Crawlers**.
2.  Click **Create crawler**.
3.  **Name:** `uta-gtfs-crawler`. Click Next.
4.  **Data Source:**
    * Click **Add a data source**.
    * **S3 path:** `s3://[YOUR_BUCKET_NAME]/raw/`
    * Click **Add an S3 data source**.
5.  **IAM Role:**
    * Select **Create new IAM role**.
    * **Name suffix:** Enter `uta-gtfs` (The full name will be `AWSGlueServiceRole-crawlerGtfs`).
    * Click **Create**.
    * The new role should automatically be selected in the dropdown. Click **Next**.
6.  **Output Configuration:**
    * **Target database:** Click **Add database**, name it `uta_gtfs_raw`, and select it.
    * **Table name prefix:** (Optional) Leave blank.
7.  **Orchestration:** Select **On demand**.
8.  Click **Create crawler**.

### Step 3.2: Run Crawler
1.  Select the new crawler and click **Run crawler**.
2.  Wait for the status to change from *Running* to *Ready*.
3.  **Verify:** Go to Athena -> Database `uta_gtfs_raw`. You should see tables like `stops`, `routes`, `trips`, etc.

---

## 4. Batch Transformation (AWS Athena)
**SQL Source:** `sql/athena_transformation.sql`

We use Athena Views to logically transform the raw CSV data into clean, typed datasets without moving files.

### Step 4.1: Prepare S3 Output Location
*Athena requires a specific S3 location to store query results and metadata.*

1.  Navigate to the **S3 Console**.
2.  Open your data lake bucket: `[YOUR_BUCKET_NAME]`.
3.  Click **Create folder**.
4.  Name it `athena-results`.
5.  Click **Create folder**.
    * *Note: You will point Athena to this folder in the next step.*

### Step 4.2: Setup Athena
1.  Navigate to the **Athena Console**.
2.  If prompted, go to **Settings** -> **Manage**.
3.  **Query result location:** Enter `s3://[YOUR_BUCKET_NAME]/athena-results/`.
    * *Ensure the trailing slash `/` is included.*
4.  Click **Save**.

### Step 4.3: Create Views
1.  Open the Query Editor in Athena.
2.  Copy the SQL queries from `sql/athena_transformation.sql`.
3.  Run the queries (either all at once or block by block).
    * This creates the `uta_gtfs_clean` database.
    * This creates Views (e.g., `uta_gtfs_clean.stops`) that automatically cast types and filter bad data.

### Step 4.4: Verification
Run the following Data Quality check in Athena to ensure the pipeline is successful:

```sql
SELECT * FROM uta_gtfs_clean.stops 
WHERE stop_lat IS NOT NULL 
LIMIT 10;