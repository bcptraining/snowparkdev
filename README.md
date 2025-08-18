# ❄️ Snowflake CI/CD Investigations #2 — Snowpark App via GitHub Workflows

This project is part of a series exploring different approaches to deploying applications in Snowflake. The goal is to identify best practices and understand when each deployment pattern is most appropriate.

In this example, we focus on deploying a **Snowpark-based application** using **GitHub Actions** to automate environment promotion across **Dev → QA → Prod**. The project demonstrates how to structure code, configure secrets, and manage deployments using Git workflows.

# 📚 Table of Contents

- [❄️ Snowflake Connection Overview](#snowflake-connection-overview)
- [✅ Prerequisites](#prerequisites)
- [🚀 Environment Promotion via GitHub Workflows](#environment-promotion-via-github-workflows)
- [🏗️ Infrastructure Setup](#infrastructure-setup)
  - [🧭 Create Environment Accounts in Snowflake](#create-environment-accounts-in-snowflake)
  - [🔐 Configure Each Environment](#configure-each-environment)
- [🔧 GitHub Repository & Branching](#github-repository--branching)
  - [🔐 Secrets Configuration](#secrets-configuration)
  - [🧪 Development Environment (Codespaces)](#development-environment-codespaces)
- [🔄 Promotion Flow Overview](#promotion-flow-overview)
- [📁 Project Structure](#project-structure)
- [📦 Scope of Snowpark Objects to Be Deployed](#scope-of-snowpark-objects-to-be-deployed)
  - [🗂️ Code Structure & Deployment Details](#code-structure--deployment-details)
  - [📊 Summary: Object Types vs. Deployment Method](#summary-object-types-vs-deployment-method)
  - [🧾 `snowflake.yml` Configuration](#snowflakeyml-configuration)
  - [📁 Folder Structure Diagram](#folder-structure-diagram)
- [⚙️ Workflow Breakdown](#workflow-breakdown)

## ❄️ Snowflake Connection Overview

This project connects to Snowflake in two main contexts: during local development (via Codespaces) and during automated deployment (via GitHub Actions).

---

### 🧑‍💻 Local Development (Codespaces)

In Codespaces, the connection to Snowflake is established when you run setup scripts or interact with Snowflake manually. Specifically:

- **File:** `setup.sh`

  - Loads environment variables from `.env` and uses the **Snowflake CLI** to upload files to a Snowflake stage.
  - Relies on secrets defined in Codespaces to authenticate.

- **File:** `process_stock_sales_data.py`
  - Uses **Snowpark for Python** to connect to Snowflake, read a CSV file, transform the data, and write to a table.
  - Connection is configured via `Session.builder.config(...)`, pulling credentials from environment variables.

> 📍 Connection is triggered when you run the setup script or execute the data transformation script manually.

---

### 🤖 CI/CD Workflows (GitHub Actions)

In GitHub Actions, the connection to Snowflake happens during automated deployment workflows:

- **File:** `.github/workflows/build_and_deploy_*.yml`

  - Loads secrets from GitHub Actions and invokes the deployment script.

- **File:** `deploy_snowflake_app.py`
  - Reads the `snowflake.yml` manifest and generates a `.toml` file that defines the deployment configuration.
  - This `.toml` file is used by the **Snowflake CLI** to deploy stored procedures, functions, and other objects.
  - Authentication is handled via secrets injected into the workflow environment.

> 📍 Connection is triggered automatically when a workflow runs (e.g., on merge or pull request).

---

### 🗂️ What’s the `.toml` File?

The `.toml` file is a structured configuration file generated during deployment. It contains metadata about:

- The target Snowflake account and role
- The database and schema
- The objects to deploy (e.g., functions, procedures)
- Source paths and build settings

This file acts as an intermediary between your `snowflake.yml` manifest and the Snowflake CLI, enabling reproducible and declarative deployments.

---

### 🔐 Authentication Summary

| Context        | Tool/Method Used        | Secrets Source         |
| -------------- | ----------------------- | ---------------------- |
| Codespaces     | Snowflake CLI, Snowpark | `.env` from Codespaces |
| GitHub Actions | Snowflake CLI, Snowpark | GitHub Actions Secrets |

---

> 💡 **Tip**: To trace the connection logic, look for:
>
> - `Session.builder.config(...)` in Python files
> - `snowflake deploy` commands in scripts
> - CLI commands like `snowflake stage put` in `setup.sh`
> - `.toml` generation logic in `deploy_snowflake_app.py`

## ✅ Prerequisites

Before you begin, make sure you have the following:

- A Snowflake trial account with **ORGADMIN** access
- A GitHub account with access to the target repository
- GitHub Codespaces enabled (optional, for cloud-based dev)
- Python 3.11 and Conda (if developing locally)
- Basic familiarity with Git workflows and CI/CD concepts

---

## 🚀 Environment Promotion via GitHub Workflows

This project uses GitHub Actions to automate deployment of the Snowflake app across environments: **Dev → QA → Prod**. Each stage of promotion is triggered by Git activity — such as merges and pull requests — and handled by a dedicated workflow file.

## 🏗️ Infrastructure Setup

This project has a requirement of Snowflake infrastructure to be setup. The account topology used is to have a Snowflake account per environment.

### 🧭 Create Environment Accounts in Snowflake

To set up separate Snowflake accounts for each environment (`DEV_ACCT`, `QA_ACCT`, `PROD_ACCT`), follow these steps:

1. **Sign in to your Snowflake trial account**.
2. **Switch to the `ORGADMIN` role** (required for account creation).
3. **Run the script below**, substituting your own email addresses and secure passwords.

```sql
-- Use the ORGADMIN role
USE ROLE ORGADMIN;

-- Create DEV environment account
CREATE ACCOUNT DEV_ACCT
  ADMIN_NAME = 'dev_admin'
  ADMIN_PASSWORD = 'YourSecurePassword123!'
  EMAIL = 'dev_admin@example.com'
  MUST_CHANGE_PASSWORD = TRUE
  EDITION = 'STANDARD';

-- Create QA environment account
CREATE ACCOUNT QA_ACCT
  ADMIN_NAME = 'qa_admin'
  ADMIN_PASSWORD = 'YourSecurePassword123!'
  EMAIL = 'qa_admin@example.com'
  MUST_CHANGE_PASSWORD = TRUE
  EDITION = 'STANDARD';

-- Create PROD environment account
CREATE ACCOUNT PROD_ACCT
  ADMIN_NAME = 'prod_admin'
  ADMIN_PASSWORD = 'YourSecurePassword123!'
  EMAIL = 'prod_admin@example.com'
  MUST_CHANGE_PASSWORD = TRUE
  EDITION = 'STANDARD';
```

### Configure Each Environment

```sql
-- Create core database
CREATE DATABASE IF NOT EXISTS DEMO_DB;
USE DATABASE DEMO_DB;

-- Create warehouse if needed (you will need it if your environment snowflake accounts are STANDARD)
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
WITH WAREHOUSE_SIZE = 'XSMALL'
AUTO_SUSPEND = 60
AUTO_RESUME = TRUE;

-- Grant permissions to create objects in DEMO_DB.PUBLIC
GRANT CREATE STAGE, CREATE FUNCTION, CREATE PROCEDURE ON SCHEMA DEMO_DB.PUBLIC TO ROLE SYSADMIN;
```

## 🔧 GitHub Repository & Branching

**Repository:**  
🔗 [bcptraining/snowparkdev](https://github.com/bcptraining/snowparkdev)

**Branching Strategy:**

- 🛠 **Feature Branch**: `devenv` (or any custom name)
- 🌱 **Environment Branches**:
  - `dev`: Development environment
  - `qa`: QA/Staging environment
  - `prod`: Production environment

Each branch maps directly to a Snowflake environment and is used to trigger environment-specific deployment workflows.

---

## 🔐 Secrets Configuration

To enable both GitHub Codespaces and GitHub Actions to interact with Snowflake securely, you’ll need to define the following secrets in **two places**:

### ✅ Required Secrets

| Secret Name           | Purpose                               |
| --------------------- | ------------------------------------- |
| `SNOWFLAKE_ACCOUNT`   | Snowflake account identifier          |
| `SNOWFLAKE_USER`      | Username for Snowflake authentication |
| `SNOWFLAKE_PASSWORD`  | Password for Snowflake authentication |
| `SNOWFLAKE_ROLE`      | Role used for executing queries       |
| `SNOWFLAKE_WAREHOUSE` | Warehouse used for compute            |
| `SNOWFLAKE_DATABASE`  | Target database                       |
| `SNOWFLAKE_SCHEMA`    | Target schema                         |

### 🧑‍💻 Define in Codespaces

Go to your repository → **Codespaces** → **Secrets** and add each of the above secrets.

### 🤖 Define in GitHub Actions

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**, and add the same secrets.

> 💡 **Why define secrets in both places?**
>
> GitHub **Codespaces** and **Actions** run in separate environments:
>
> - **Codespaces** uses secrets during interactive development (e.g., running setup scripts, testing locally).
> - **Actions** uses secrets during automated CI/CD workflows (e.g., deploying to Snowflake).
>
> Even though the variable names are the same, they must be defined **independently** in each context to ensure both environments have access to the credentials they need.

---

## 🧪 Development Environment (Codespaces)

This project uses **GitHub Codespaces** for cloud-based development, but it can also run locally or in Docker.

### ⚙️ Development Container Setup

The container is defined in `.devcontainer/devcontainer.json`, which uses a **Python 3.11 base image** and runs `setup.sh` after creation. The setup script:

- 🐍 Initializes Conda and creates `py311_env` from `environment.yml`
- 📦 Installs `pipx` and globally installs the **Snowflake CLI**
- 🔐 Loads environment variables from `.env`
- 📁 Uploads a local data file to a Snowflake stage using the CLI
- 🛠️ Updates the shell `PATH` to ensure CLI tools are accessible

> 💡 Tip: You can replicate this setup locally by running `setup.sh` inside a Python 3.11 Conda environment.

### 🔄 Promotion Flow Overview

| GitHub Branch Activity       | Triggered Workflow File     | Target Environment |
| ---------------------------- | --------------------------- | ------------------ |
| Merge feature branch → `dev` | `build_and_deploy_dev.yml`  | Development        |
| Pull request `dev` → `qa`    | `build_and_deploy_qa.yml`   | QA / Staging       |
| Pull request `qa` → `main`   | `build_and_deploy_prod.yml` | Production         |

This setup ensures:

- **Explicit control** over promotions via pull requests
- **Automated deployment** to the correct Snowflake environment
- **Environment isolation** through scoped configs and secrets

## Project Structure

├── .devcontainer
│   ├── devcontainer.json
│   └── setup.sh
├── .snowflake
│   └── config.toml
├── environment.yml
├── first_snowpark_project
│   ├── .env
│   ├── .gitignore
│   ├── __init__.py
│   ├── app
│   │   ├── __init__.py
│   │   ├── python
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── functions.py
│   │   │   ├── procedures.py
│   │   │   ├── process_stock_sales_data.py
│   │   │   ├── session.py
│   │   │   └── test_session.py
│   │   └── sql
│   │       └── views
│   │           └── query_history_vw.sql
│   ├── app.zip
│   ├── data
│   │   ├── cleaned_stock_sales_data.csv
│   │   └── stock_sales_data.csv
│   ├── deploy_snowflake_app.py
│   ├── requirements.txt
│   └── snowflake.yml
├── requirements.txt
├── setup_env.py
└── workspaces
    └── snowparkdev
        └── docs
            └── snowpark-setup.md

## 📦 Scope of Snowpark Objects to Be Deployed

This example CI/CD pipeline deploys the following Snowpark objects into the `DEMO_DB.PUBLIC` schema:

### 🔧 Objects Deployed

- **Python Function**
  - `HELLO_FUNCTION`: Greets a user by name.
- **Python Procedures**
  - `HELLO_PROCEDURE`: Wraps the greeting logic as a procedure.
  - `TEST_PROCEDURE`: A second demo procedure.
- **Table**
  - `STOCK_VALUE_SUMMARY`: Stores transformed CSV data.

> 🛠️ A one-time data transformation step processes a CSV file and populates the `STOCK_VALUE_SUMMARY` table. This is **not** a recurring pipeline.

---

### 🗂️ Code Structure & Deployment Details

All deployable code lives in the `app/` folder within the `first_snowpark_project` directory.

#### 📁 Folder Breakdown

- **Functions & Procedures**

  - Located in:
    - `app/python/functions/`
    - `app/python/procedures/`
  - Registered via `snowflake.yml`.

- **Data Transformation Script**

  - `app/python/process_stock_sales_data.py`:  
    A standalone script that:
    - Reads a CSV file
    - Cleans and summarizes it using **Pandas** and **Snowpark**
    - Writes the result to a Snowflake table  
      This demonstrates a **script-driven pipeline**, not a function or procedure.

- **Data Files**
  - `app/data/`:  
    Contains:
    - The original CSV file
    - A cleaned version generated during preprocessing

---

### 📊 Summary: Object Types vs. Deployment Method

| Object Type         | Name(s)                             | Deployment Method         | Location                                 |
| ------------------- | ----------------------------------- | ------------------------- | ---------------------------------------- |
| Python Function     | `HELLO_FUNCTION`                    | Via `snowflake.yml`       | `app/python/functions/`                  |
| Python Procedures   | `HELLO_PROCEDURE`, `TEST_PROCEDURE` | Via `snowflake.yml`       | `app/python/procedures/`                 |
| Table               | `STOCK_VALUE_SUMMARY`               | Script-driven             | Created by `process_stock_sales_data.py` |
| Data Transformation | N/A                                 | Standalone script         | `app/python/process_stock_sales_data.py` |
| CSV Data Files      | N/A                                 | Input/output for pipeline | `app/data/`                              |

---

### 🧾 `snowflake.yml` Configuration

The `snowflake.yml` file acts as a manifest for the Snowflake CLI, defining how Snowpark objects are registered and deployed.

#### 📌 Example: `snowflake.yml`

```yaml
version: 1.0

functions:
  - name: HELLO_FUNCTION
    file: app/python/functions/hello_function.py
    handler: hello_function.handler
    language: python
    runtime: 3.11
    packages:
      - snowflake-snowpark-python

procedures:
  - name: HELLO_PROCEDURE
    file: app/python/procedures/hello_procedure.py
    handler: hello_procedure.handler
    language: python
    runtime: 3.11
    packages:
      - snowflake-snowpark-python

  - name: TEST_PROCEDURE
    file: app/python/procedures/test_procedure.py
    handler: test_procedure.handler
    language: python
    runtime: 3.11
    packages:
      - snowflake-snowpark-python
```

### 📁 Folder Structure Diagram

```plaintext
first_snowpark_project/
└── app/
    ├── python/
    │   ├── functions/
    │   │   └── hello_function.py
    │   ├── procedures/
    │   │   ├── hello_procedure.py
    │   │   └── test_procedure.py
    │   └── process_stock_sales_data.py
    ├── data/
    │   ├── original_stock_data.csv
    │   └── cleaned_stock_data.csv
    └── snowflake.yml
```

## ⚙️ Workflow Breakdown

Each workflow file in `.github/workflows/` defines a CI/CD pipeline tailored to its environment:

### `build_and_deploy_dev.yml`

- **Triggered by**: Pushes or merges to `dev`
- **Purpose**: Deploys feature branch changes into the dev environment
- **Uses**: Dev-specific Snowflake role, warehouse, and database

### `build_and_deploy_qa.yml`

- **Triggered by**: Pull request from `dev` to `qa`
- **Purpose**: Promotes tested code to QA for validation
- **Uses**: QA-specific Snowflake configuration

### `build_and_deploy_prod.yml`

- **Triggered by**: Pull request from `qa` to `main`
- **Purpose**: Final promotion to production
- **Uses**: Production Snowflake credentials and settings

Each workflow performs the following steps:

1. Sets up Python and dependencies
2. Loads environment secrets from GitHub
3. Runs `deploy_snowflake_app.py` with the appropriate project directory
4. Validates and deploys the app to Snowflake

> 📄 **About `deploy_snowflake_app.py`**  
> This script serves as the deployment orchestrator for Snowpark applications. It reads the `snowflake.yml` manifest, applies environment-specific configurations, and invokes the Snowflake CLI to register functions, procedures, and other objects.  
> It ensures that only the correct code is deployed to the appropriate Snowflake environment, based on the current GitHub branch and secrets.

---

This structure ensures a clean, auditable, and automated path from feature development to production deployment.
