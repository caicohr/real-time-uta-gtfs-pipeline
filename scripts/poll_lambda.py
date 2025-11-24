import json
from poll_gtfs_realtime import fetch_realtime_data  # Reuse the existing polling function


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    This function is automatically executed each time the Lambda is triggered
    (in this project, every 30 seconds via EventBridge).

    Responsibilities:
    1. Call the polling function to retrieve the latest UTA realtime data.
    2. Format the result as JSON.
    3. Return the data in the standard structure expected by AWS Lambda.
    """

    # Step 1: Retrieve the latest GTFS-Realtime vehicle data
    data = fetch_realtime_data()

    # Step 2: Return a response in the required AWS Lambda format
    # - statusCode: indicates a successful execution
    # - body: JSON-encoded string of the data
    return {
        "statusCode": 200,
        "body": json.dumps(data)
    }


# This block runs only when the script is executed locally.
# It allows simple testing without deploying to AWS.
if __name__ == "__main__":
    result = lambda_handler(None, None)
    print(result)