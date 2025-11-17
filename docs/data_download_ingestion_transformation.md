# Data Ingestion & Transformation Guide

**Author:** Jerico Radin  
**Pipeline Stage:** Week 1 (Batch Processing)  
**Tech Stack:** AWS Lambda, S3, Glue, Athena

---

## 1. Architecture Overview
This pipeline fetches GTFS data from the UTA endpoint, stores the raw history in S3, and transforms it into optimized Parquet tables using Athena.

* **Ingestion:** AWS Lambda (Python 3.9) -> S3
* **Cataloging:** AWS Glue Crawler
* **Transformation:** AWS Athena (SQL)

---

## 2. Ingestion (AWS Lambda)
**Script:** `scripts/ingest_lambda.py`

### Deployment Steps
1.  **Create Function:**
    * Go to AWS Lambda Console -> **Create Function**.
    * Name: `uta-gtfs-ingest`.
    * Runtime: `Python 3.9`.
    * **Permissions:** Select existing role `LabRole` (or `VocareumRole`).
2.  **Deploy Code:**
    * Copy/Paste code from `scripts/ingest_lambda.py` into the AWS editor.
    * Click **Deploy**.
3.  **Configuration:**
    * **Timeout:** Set to **5 min** (General Configuration -> Edit).
    * **Environment Variables:**
        * `GTFS_FEED_URL`: `https://gtfsfeed.rideuta.com/GTFS.zip`
        * `BUCKET_NAME`: `[YOUR_BUCKET_NAME]`
4.  **Execute:**
    * Create a test event and click **Test**.
    * *Verify:* S3 bucket should contain folders `raw/YYYY-MM-DD/stops/`, `routes/`, etc.

---

## 3. Data Cataloging (AWS Glue)

1.  **Create Crawler:**
    * Go to AWS Glue -> **Crawlers**.
    * Name: `uta-gtfs-crawler`.
    * Source: `s3://[YOUR_BUCKET_NAME]/raw/`.
    * Target Database: `uta_gtfs_raw`.
2.  **Run:**
    * Run the crawler and wait for it to complete.
    * *Verify:* Tables (`stops`, `routes`, etc.) appear in Athena under `uta_gtfs_raw`.

---

## 4. Batch Transformation (AWS Athena)
**SQL Script:** `sql/athena_transformation.sql`

1.  **Setup:**
    * Ensure Athena output location is set to `s3://[YOUR_BUCKET_NAME]/athena-results/`.
2.  **Execution:**
    * Run the queries from `sql/athena_transformation.sql` in the Athena Query Editor.
    * This creates the `uta_gtfs_clean` database and Parquet tables.
3.  **Verification:**
    * Run: `SELECT * FROM uta_gtfs_clean.stops LIMIT 10;`