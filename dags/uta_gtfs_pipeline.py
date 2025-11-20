from airflow import DAG
from airflow.providers.amazon.aws.operators.lambda_function import LambdaInvokeFunctionOperator
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator
import pendulum
from datetime import timedelta

# CONFIGURATION
LAMBDA_FUNCTION_NAME = 'uta-gtfs-ingest'
GLUE_CRAWLER_NAME = 'uta-gtfs-crawler'
AWS_REGION = 'us-east-1'  # Define region explicitly

default_args = {
    'owner': 'ec2-user',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1), # Reduced to 1 min for testing
}

with DAG(
    'uta_gtfs_pipeline',
    default_args=default_args,
    description='Daily GTFS Pipeline running on EC2',
    schedule='0 10 * * *',
    start_date=pendulum.today('UTC').add(days=-1),
    catchup=False,
) as dag:

    # Step 1: Trigger Lambda
    ingest_task = LambdaInvokeFunctionOperator(
        task_id='ingest_gtfs_data',
        function_name=LAMBDA_FUNCTION_NAME,
        invocation_type='RequestResponse',
        log_type='Tail',
        region_name=AWS_REGION,     # <--- CRITICAL FIX
    )

    # Step 2: Trigger Crawler
    crawler_task = GlueCrawlerOperator(
        task_id='catalog_data',
        config={'Name': GLUE_CRAWLER_NAME},
        region_name=AWS_REGION,     # <--- CRITICAL FIX
    )

    ingest_task >> crawler_task