## ⚙️ Real-Time UTA Transit Visualization on AWS EC2 (Private Access)

This guide details the deployment of the real-time public transit visualization application, built with **Python 3** and **Plotly Dash**, onto an Amazon Web Services (AWS) EC2 instance. The application, specifically the `gtfs.py` script, uses UTA's GTFS Real-Time data for live vehicle tracking and analytics.

---

## Section 1: AWS EC2 Instance Setup and Private Key Generation 🔑

This section covers provisioning the EC2 instance and securely configuring SSH access.

### 1.1 Launch EC2 Instance Configuration

1.  **Select AMI:** Select a standard **Linux** distribution.
2.  **Instance Type:** The **`t2.xlarge`** instance type has been selected, providing sufficient resources for processing and serving the real-time data.
3.  **Create Key Pair (SSH Key):**
    * When launching the instance, select **Create new key pair**.
    * Name the key (e.g., `uta-dash-key`) and select the **.pem** format.
    * **Download the private key file.** This file is essential for SSH access.

### 1.2 Configure Network and Security Group

The Security Group acts as the virtual firewall for your instance.

1.  **Inbound Rules Configuration:** You must allow SSH access and access to the Dash application port.

| Type | Protocol | Port Range | Source Type | Description |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | TCP | 22 | My IP | Allows secure shell access. **Restrict this to your specific IP address** to ensure the instance remains private and secure. |
| **Custom TCP** | TCP | **8050** | My IP | **Required for Plotly Dash** access. This should also be restricted to your specific IP range, as the application is not intended for public access. |

---

## Section 2: Connecting to EC2 and Environment Preparation 💻

This section covers connecting to the EC2 instance and installing the necessary Python libraries. **Note:** Your EC2 AMI comes pre-installed with the required Python version (Python 3).

### 2.1 SSH Connection and Code Retrieval

1.  **Establish Connection:** Use your downloaded `.pem` file to connect to the EC2 instance via SSH. Follow the specific connection tutorial provided by your EC2 dashboard for precise instructions.
2.  **Clone Repository:** Once connected, clone the GitHub repository containing the application code.
3.  **Locate Script:** The main application code is specifically located at:
    `scripts/gtfs.py`

### 2.2 Installing Dependencies

While Python 3 is pre-installed, you must install the Dash and Plotly libraries, along with any other dependencies needed to handle GTFS Real-Time data and mapping.

* **Install Libraries:** Use the `pip3` command to ensure the libraries are installed for Python 3.

    ```bash
    # Example command to install required libraries
    pip3 install plotly dash pandas requests
    
    # Add any other required libraries (e.g., specific mapping libraries)
    ```

---

## Section 3: Running the Dash Application 🚀

### 3.1 Execution Command

The `gtfs.py` script **must be executed using the `python3` command** to ensure compatibility with modern libraries and to leverage the correct interpreter.

1.  **Navigate to Script:**
    ```bash
    cd scripts/
    ```
2.  **Run the Dash Application:**
    ```bash
    python3 gtfs.py
    ```
    *It is highly recommended to run this command within a utility like **`screen`** or **`tmux`** so the application continues to run even if your SSH connection is terminated.*

### 3.2 Application Functionality (Plotly Dash/GTFS)

The application provides a comprehensive interface for analyzing the UTA schedule service:

* **Real-Time Map Visualization:** The core feature is a dynamic map component (using Plotly) that renders the streets and terrain. **Dots** on the map represent the precise, real-time location of UTA vehicles. Clicking on these dots provides detailed vehicle information.
* **Analytical Data Visualization:** The dashboard includes interactive Plotly charts, enabling users to visualize relationships and trends within the vehicle data (e.g., historical route performance, speed distributions, or service frequency).

---

## Section 4: Accessing the Dashboard 🌐

Since the security group is restricted, the dashboard is only accessible from the machine you used to connect via SSH.

1.  Open your web browser.
2.  Enter the public address of your EC2 instance followed by the Dash application's port:

    ```
    http://<EC2_Public_IP_Address>:8050
    ```
