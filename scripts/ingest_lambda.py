import json
import os
import urllib.request
import zipfile
import boto3
from datetime import datetime

# Environment Variables (Set these in AWS Lambda Console)
# GTFS_FEED_URL = https://gtfsfeed.rideuta.com/GTFS.zip
# BUCKET_NAME = your-bucket-name

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    print(f"🚀 Starting GTFS Ingestion...")
    
    # 1. Setup Paths (Lambda only allows writing to /tmp)
    gtfs_url = os.environ.get('GTFS_FEED_URL')
    bucket_name = os.environ.get('BUCKET_NAME')
    
    download_path = '/tmp/GTFS.zip'
    extract_path = '/tmp/extracted'
    
    # 2. Download
    print(f"⬇️ Downloading from {gtfs_url}...")
    try:
        urllib.request.urlretrieve(gtfs_url, download_path)
    except Exception as e:
        print(f"❌ Download failed: {str(e)}")
        raise e

    # 3. Unzip
    print("📦 Extracting...")
    with zipfile.ZipFile(download_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    
    # 4. Upload to S3 (Raw Zone)
    # We partition by Date so we can track history: raw/YYYY-MM-DD/file.txt
    today = datetime.now().strftime("%Y-%m-%d")
    s3_prefix = f"raw/{today}"
    
    uploaded_count = 0
    
    for filename in os.listdir(extract_path):
        if filename.endswith(".txt"):
            local_file = os.path.join(extract_path, filename)
            folder_name = filename.replace('.txt', '') # e.g., 'stops'
            s3_key = f"{s3_prefix}/{folder_name}/{filename}"
            
            print(f"☁️ Uploading {filename} -> s3://{bucket_name}/{s3_key}")
            s3_client.upload_file(local_file, bucket_name, s3_key)
            uploaded_count += 1

    return {
        'statusCode': 200,
        'body': json.dumps(f"Success: Uploaded {uploaded_count} files to {s3_prefix}")
    }