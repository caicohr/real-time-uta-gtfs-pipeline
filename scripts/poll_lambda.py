import json
import boto3
import csv
import io 
from botocore.exceptions import ClientError
from poll_gtfs_realtime import fetch_realtime_data 

# Define the Kinesis stream name
KINESIS_STREAM_NAME = "uta_Gtfs_kinesis_stream"

def format_list_to_table_string(entity_list):
    """
    Uses the built-in CSV writer to format the list of dictionaries 
    into a clean, string table for printing to CloudWatch logs.
    """
    if not entity_list:
        return "No data retrieved."

    # Define the headers (your column names)
    fieldnames = ['id', 'trip_id', 'route_id', 'latitude', 'longitude', 'vehicle_timestamp', 'source_timestamp']
    output = io.StringIO()
    # Use tab-delimited format for neat printing in logs
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter='\t', extrasaction='ignore') 
    
    writer.writeheader()
    writer.writerows(entity_list)
    
    return output.getvalue()


def send_to_kinesis(stream_name, data_list):
    """
    Sends the list of structured data dictionaries to the Kinesis stream 
    using the highly efficient put_records (batch) method.
    """
    # 1. Initialize Kinesis client defensively
    try:
        kinesis_client = boto3.client('kinesis')
    except Exception as e:
        print(f"FATAL: Failed to initialize Kinesis client: {e}")
        return {"Error": "Client initialization failed"}
    
    
    records = []
    # 2. Prepare all records in the batch format (up to 500 records per call)
    for entity in data_list:
        # Data must be a JSON string converted to bytes
        data_bytes = json.dumps(entity).encode('utf-8')
        
        # Use 'id' as Partition Key for consistent sharding
        partition_key = entity.get('id', 'default_key')
        
        records.append({
            'Data': data_bytes,
            'PartitionKey': partition_key
        })

    # 3. Send the entire batch
    try:
        response = kinesis_client.put_records(
            Records=records,
            StreamName=stream_name
        )
        return response
        
    except ClientError as e:
        # Catch specific AWS API errors (e.g., throttling, stream not found)
        print(f"Kinesis ClientError: Failed to send records: {e}")
        return {"Error": f"Kinesis API failure: {e.response['Error']['Message']}"}
        
    except Exception as e:
        # Catch general errors (e.g., network issues)
        print(f"General Error during Kinesis send: {e}")
        return {"Error": "General send failure"}


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    Fetches GTFS data, prints a tabular log, and sends the data to Kinesis.
    """
    
    # 1. Fetch the data (list of dictionaries)
    entity_list = fetch_realtime_data()
    
    # 2. Format and Print the tabular log for CloudWatch
    table_string = format_list_to_table_string(entity_list)
    print("--- Organized Vehicle Data (Tabular Log Print) ---")
    print(table_string)

    # 3. Send the structured data to Kinesis
    kinesis_response = send_to_kinesis(KINESIS_STREAM_NAME, entity_list)
    
    print("--- Kinesis Send Response ---")
    
    failed_count = kinesis_response.get('FailedRecordCount', 0)
    
    if failed_count > 0:
        print(f"⚠️ WARNING: {failed_count} records failed to send.")
        # Print the full response for debugging failed records
        print(kinesis_response)
    elif kinesis_response.get("Error"):
        # Print custom error from the send_to_kinesis function
        print(f"❌ Kinesis Send Failed: {kinesis_response['Error']}")
        # Optionally, raise an exception here to fail the Lambda run:
        # raise Exception("Kinesis sending failed.")
    else:
        print("✅ All records sent successfully.")
        
    # 4. Return success status and the original data 
    return {
        "statusCode": 200,
        "body": json.dumps(entity_list)
    }

"""
def lambda_handler(event, context):
    #AWS Lambda entry point.
    #Fetches realtime GTFS data and returns it as JSON.

    data = fetch_realtime_data()
    print(data)

    return {
        "statusCode": 200,
        "body": json.dumps(data)
    }

if __name__ == "__main__":
    result = lambda_handler(None, None)
    print(result)
"""
