# Orchestration Strategy

 **Course:** CS6830 – Fundamentals of Data Engineering (Fall 2025)  
 **Author:** Jerico Radin

To satisfy the requirement of using Apache Airflow, we have documented two distinct deployment strategies. For this lab, we successfully implemented **Strategy B (MWAA)** to ensure production-grade reliability, while also documenting the architectural design for **Strategy A (EC2)** as a low-cost alternative.

We maintain two versions of the DAG code to handle the credential differences between the environments:

1.  `dags/uta_gtfs_pipeline_ec2.py` (For Strategy A)
2.  `dags/uta_gtfs_pipeline.py` (For Strategy B)

-----

### Strategy A: Self-Hosted Airflow on EC2 (Alternative Design)

*Best for: Development, strict budget control, and learning Airflow internals.*

In this approach, we provision a lightweight Linux server to host the Airflow Scheduler and Web Server manually.

#### 1\. Infrastructure Setup

1.  **Launch Instance:**
      * **Service:** Amazon EC2
      * **AMI:** Amazon Linux 2023
      * **Type:** `t3.micro` (Free tier eligible)
      * **IAM Role:** Attach `LabRole` or `VocareumRole` (Acts as the "ID Card" for the server).
2.  **Connect:**
      * SSH into the instance using EC2 Instance Connect.

#### 2\. Environment Configuration

Run the following commands in the EC2 terminal to install Airflow and set up the database.

```bash
# 1. Update system and install Python/Pip
sudo dnf update -y
sudo dnf install python3-pip git -y

# 2. Install Airflow, AWS Provider, and FAB
pip3 install apache-airflow apache-airflow-providers-amazon apache-airflow-providers-fab

# 3. Configure Environment (Force SequentialExecutor for SQLite compatibility)
export AIRFLOW__CORE__EXECUTOR=SequentialExecutor
export AIRFLOW_HOME=~/airflow
airflow db migrate

# 4. Create Admin User
airflow users create --username admin --role Admin --email admin@example.com --firstname Student --lastname User
```

#### 3\. Pipeline Deployment

  * **Code Source:** `dags/uta_gtfs_pipeline_ec2.py`
  * **Configuration:** We use `aws_conn_id=None` to force Airflow to use the EC2 Instance Profile.
  * **Execution:**
    ```bash
    # Manual Test
    airflow dags test uta_gtfs_pipeline 2025-11-20
    ```

#### 4\. Trade-offs (Why we moved away from this)

  * **Resource Constraints:** The `t2.micro` instance (1GB RAM) struggles with the latest Airflow 3.0+ scheduler, leading to "Out of Memory" crashes.
  * **Database Locking:** The default SQLite database forces the use of `SequentialExecutor`, which prevents parallel task execution and can cause scheduler hangs during high load.

-----

### Strategy B: AWS Managed Workflows for Apache Airflow (MWAA) (Implemented)

*Best for: Enterprise production, high availability, and "Serverless" management.*

This strategy uses the official AWS managed service. We selected this as our final implementation because it handles scaling, patching, and scheduler reliability automatically.

#### 1\. Prerequisites (S3 Setup)

1.  **Create S3 Bucket:** Create a dedicated bucket (e.g., `uta-airflow-dags`) with **Versioning Enabled**.
2.  **Code Selection:**
      * We use the production code: `dags/uta_gtfs_pipeline.py`.
      * **Configuration Note:** Operators use `aws_conn_id='aws_default'`. MWAA automatically injects the Execution Role credentials into this default connection.
3.  **Upload DAG:** Upload the file to the `dags/` folder in S3.

#### 2\. Environment Creation

1.  **Navigate to MWAA:** Go to the **Amazon MWAA** console.
2.  **Create Environment:**
      * **Name:** `uta-production-airflow`
      * **DAG Code:** Select the S3 bucket and folder created in Step 1.
      * **Network:** Select the VPC, two private subnets, and "Public Network" for Web Server access.
3.  **Create:** (Provisioning takes approx. 20 minutes).

#### 3\. Permission Configuration (Crucial Step)

By default, the MWAA Execution Role cannot access Glue or Lambda.

1.  Click the **Execution Role** link in the MWAA details page.
2.  Attach the following policies in IAM:
      * `AWSGlueConsoleFullAccess`
      * `AWSLambda_FullAccess`
3.  **Verification:** We verified this by clearing the `catalog_data` task, which transitioned from `ResourceNotFoundException` to **Success**.

#### 4\. Deployment & Updates

  * **Continuous Delivery:** We simply upload a new Python file to the S3 bucket. MWAA detects the change and updates the scheduler within 30 seconds automatically.
  * **Verification:** We updated the schedule to `19:40 UTC` (12:40 PM MST) and verified the DAG triggered automatically at the correct time.

-----

### Final Decision

We selected **Strategy B (MWAA)** as our final implementation for this project.

**Reasoning:**

1.  **Reliability:** During testing, Strategy A (EC2 `t2.micro`) encountered scheduler instability and database locking issues due to resource constraints (RAM) and SQLite limitations.
2.  **Production Readiness:** MWAA provided a stable, managed environment that executed the DAGs flawlessly once IAM permissions were configured.
3.  **Operational Overhead:** MWAA removed the need to manually restart the scheduler daemon or debug process locks, allowing us to focus entirely on the pipeline logic.

While EC2 is cheaper (\~$0.01/hr vs ~$0.49/hr), the engineering time required to maintain a stable self-hosted Airflow instance outweighs the infrastructure savings for this production-critical pipeline.