# UTA Transit Data Engineering Pipeline

This repository contains the code and documentation for building a data engineering pipeline to process and integrate Utah Transit Authority (UTA) transit data. The project involves two key data ingestion paths: a batch pipeline for infrequently changing schedule data (GTFS Schedule) and a real-time pipeline for dynamic vehicle position data (GTFS RT).

## Key Components

### 1. Data Discovery and Ingestion
- Locating, downloading, and ingesting UTA GTFS data into a database or data lake (hosted on AWS).

### 2. Batch Processing
- Cleaning, transforming, and loading schedule data (GTFS Schedule) into a structured format for analysis.

### 3. Real-Time Data Processing
- Fetching and decoding real-time vehicle data (GTFS RT) using Protocol Buffers.

### 4. Pipeline Orchestration
- Automating and scheduling daily ingestion and transformation jobs using Apache Airflow or AWS MWAA.

### 5. Documentation and Code
- Detailed instructions for setting up, configuring, and running the pipeline, as well as code to deploy the solution on AWS.

## Final Goal

The final goal of this project is to combine both data sources into a unified dataset that powers dashboards for tracking vehicle positions, estimated arrival times, and on-time performance.


## Git Workflow

### No Direct Pushes to `main`

To ensure consistency and collaboration, please follow these guidelines for working with Git branches and pull requests.

### 1. Create a New Branch

When starting work on a new feature or task, create a new branch from the `main` branch. The branch name should follow the format:

- **Feature branches**: `feature/your-feature-description`  
  Example: `feature/week-1-data-discovery`

- **Bugfix branches**: `bugfix/issue-description`  
  Example: `bugfix/fix-missing-values`

To create and switch to a new branch, run the following command:

```bash
git checkout -b feature/week-1-data-discovery
````

### 2. Make Changes

Work on your task or feature, making sure to commit your changes with clear and concise commit messages.

### 3. Stage and Commit Your Changes

Once you've made your changes, stage and commit them:

```bash
git add .
git commit -m "Week 1: Initial commit for data discovery and ingestion"
```

### 4. Push the Branch to GitHub

After committing, push your branch to GitHub:

```bash
git push origin feature/week-1-data-discovery
```

### 5. Create a Pull Request (PR)

* Go to your repository on GitHub.
* You should see a banner suggesting to create a pull request for the branch you've just pushed.
* Click "Compare & pull request".
* Fill out the pull request form with a meaningful title and description.
* Select the base branch (`main`) and the compare branch (the feature branch you just pushed).
* Click "Create pull request".

### 6. Merge and Cleanup

After the pull request is reviewed and approved, it can be merged into the `main` branch.

After merging, delete your feature branch locally and remotely:

* Delete the local branch:

  ```bash
  git branch -d feature/week-1-data-discovery
  ```

* Delete the remote branch:

  ```bash
  git push origin --delete feature/week-1-data-discovery
  ```

By following this workflow, we ensure a smooth collaboration process and keep our Git history organized.