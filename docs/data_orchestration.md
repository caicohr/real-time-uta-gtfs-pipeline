## Orchestration Strategy

To satisfy the requirement of using Apache Airflow, we have documented two distinct deployment strategies. For this lab, we implemented **Strategy A (EC2)** to optimize for cost and setup speed, while providing the architectural design for **Strategy B (MWAA)** for production scenarios.

---

### Strategy A: Self-Hosted Airflow on EC2 (Implemented)
*Best for: Student labs, development, and strict budget control.*

In this approach, we provision a lightweight Linux server to host the Airflow Scheduler and Web Server manually.

#### 1. Infrastructure Setup
1.  **Launch Instance:**
    * **Service:** Amazon EC2
    * **AMI:** Amazon Linux 2023
    * **Type:** `t2.micro` (Free tier eligible)
    * **Network:** Allow SSH (Port 22) from your IP.
    * **IAM Role:** Attach `LabRole` or `VocareumRole` (Crucial: This gives the server permission to trigger Lambda/Glue without hardcoding AWS keys).
2.  **Connect:**
    * SSH into the instance using EC2 Instance Connect or your terminal.

#### 2. Environment Configuration
Run the following commands in the EC2 terminal to install Airflow and set up the database.

```bash
# 1. Update system and install Python/Pip
sudo dnf update -y
sudo dnf install python3-pip git -y

# 2. Install Airflow, AWS Provider, and FAB (Required for User Management in Airflow 3+)
# We install in the user directory to avoid permission issues
pip3 install apache-airflow apache-airflow-providers-amazon apache-airflow-providers-fab

# 3. Configure Airflow to use FAB Auth Manager (Enables 'airflow users' command)
export PATH=$PATH:/home/ec2-user/.local/bin
echo "export PATH=\$PATH:/home/ec2-user/.local/bin" >> ~/.bashrc

# CRITICAL: Set Auth Manager to FAB before running migrate
export AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
echo "export AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager" >> ~/.bashrc

# 4. Initialize the Database (SQLite)
export AIRFLOW_HOME=~/airflow
airflow db migrate

# 5. Create an Admin User
# Note: These are generic lab credentials. Use strong passwords in production.
airflow users create \
    --username admin \
    --firstname Student \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

#### 3. Pipeline Deployment
1.  **Create DAG Directory:**
    ```bash
    mkdir -p ~/airflow/dags
    ```
2.  **Deploy Code:**
    * Use `nano` to create the file:
      ```bash
      nano ~/airflow/dags/uta_gtfs_pipeline.py
      ```
    * **Copy/Paste** the content of `dags/uta_gtfs_pipeline.py` from your local repo into the editor.
    * Save: `Ctrl+O` -> `Enter` -> `Ctrl+X`.

#### 4. Execution & Orchestration
* **To Run Manually (Test):**
  ```bash
  airflow dags test uta_gtfs_pipeline 2025-11-20
  ```
* **To Run Daily (Daemon Mode):**  
Start the scheduler in the background so it persists after you disconnect:
  ```bash
  airflow scheduler -D
  ```

#### 5. Cost Control (The "Pause" Mechanism)
  * To Pause: Stop the EC2 instance via the AWS Console (Instance State -> Stop). Usage costs drop to $0/hour.

  * To Resume: Start the instance and `run airflow scheduler -D` again.

#### 6. Troubleshooting
If the DAG fails with an `AccessDeniedException`, it indicates that the EC2 server has an IAM Role, but that role lacks specific permissions.

**Example Symptom:**
The logs show an error like:  
`User: ... is not authorized to perform: glue:GetCrawler ... because no identity-based policy allows the glue:GetCrawler action`.

**Solution:**
1.  **Read the Error:** The error message explicitly tells you which permission is missing (e.g., `glue:GetCrawler` or `lambda:InvokeFunction`).
2.  **Modify the Role:**
    * Go to the **AWS Console** -> **IAM**.
    * Find the Role currently attached to your EC2 instance (e.g., `LabRole`, `EMR_EC2_DefaultRole`).
    * Click **Add permissions** -> **Attach policies**.
    * Search for and attach the policy that grants the missing access (e.g., if Glue is failing, look for a Glue policy; if Lambda is failing, look for a Lambda policy).
---

### Strategy B: AWS Managed Workflows for Apache Airflow (MWAA)
*Best for: Enterprise production, high availability, and "Serverless" management.*

This strategy uses the official AWS managed service. It removes the need to patch servers or restart schedulers manually.

#### 1. Prerequisites (S3 Setup)
*Before creating the environment, we must stage the code in S3.*

1.  **Create S3 Bucket:**
    * Create a dedicated bucket (e.g., `uta-gtfs-airflow-dags`).
    * **Important:** Versioning **MUST** be enabled.
2.  **Upload DAG:**
    * Create a folder named `dags/` inside the bucket.
    * Upload the file `dags/uta_gtfs_pipeline.py` into this folder.
    * *S3 URI Example:* `s3://uta-airflow-dags/dags/uta_gtfs_pipeline.py`

#### 2. Environment Creation Steps
1.  **Navigate to MWAA:** Go to the **Amazon MWAA** console.
2.  **Create Environment:**
    * **Name:** `uta-production-airflow`
    * **Airflow Version:** `3.0.6` (or latest).
    * **Weekly Maintenance:** Leave as default.
3.  **DAG Code Settings:**
    * **S3 Bucket:** Browse and select the bucket you created in Step 1.
    * **DAGs Folder:** Browse and select the `dags/` folder you just uploaded to.
    * *(Note: Because we uploaded the file first, the wizard validates the path immediately).*
4.  **Network Configuration:**
    * **VPC:** Select the Lab VPC (or create new if allowed).
    * **Subnets:** Select two private subnets.
    * **Web Server Access:** "Public Network" (Required to view the UI from the internet).
5.  **Create:** (This process might take 5-10 minutes or more to provision).

#### 3. Deployment & Updates
* **To Deploy:** Simply upload new or modified python files to the S3 `dags/` folder.
* **To Sync:** MWAA automatically detects S3 changes and updates the scheduler within ~30 seconds. No restart required.

#### 4. Cost Control (The "Pause" Nuance)
* **Auto-Scaling:** MWAA automatically pauses *Workers* when no tasks are running.
* **Environment Fee:** The management layer runs 24/7 and **cannot be paused**.
* **To "Stop" Costs:** You must **delete the environment** entirely when the project is finished.

---

### Final Decision
We selected **Strategy A (EC2)** for this project because:
1.  **Budget:** MWAA costs ~$0.49/hour minimum ($11/day), whereas EC2 costs ~$0.01/hour ($0.25/day).
2.  **Agility:** EC2 launches in seconds, allowing faster iteration than MWAA's 20-minute creation time.
3.  **Control:** We retain full control over the process lifecycle (Start/Stop) to ensure zero waste of lab credits.
