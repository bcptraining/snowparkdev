#!/usr/bin/env bash

set -e

echo "🔍 Validating Snowflake environment variables..."

REQUIRED_VARS=(
  SNOWFLAKE_ACCOUNT
  SNOWFLAKE_USER
  SNOWFLAKE_PASSWORD
  SNOWFLAKE_ROLE
  SNOWFLAKE_WAREHOUSE
  SNOWFLAKE_DATABASE
)

for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var}" ]]; then
    echo "❌ Missing required environment variable: $var"
    exit 1
  fi
done

echo "✅ All required variables are set."

echo "🧪 Running test query via SnowCLI..."
snow sql --connection default -q "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE();"

echo "📦 Creating stage if it doesn't exist..."
snow sql --connection default -q "CREATE STAGE IF NOT EXISTS dev_stage;"

echo "📤 Uploading files to stage..."
snow storage upload --connection default --stage dev_stage --source ./data --overwrite

echo "🐍 Running Snowpark Python job..."

python <<EOF
from snowflake.snowpark import Session
import os

connection_parameters = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
}

session = Session.builder.configs(connection_parameters).create()
df = session.sql("SELECT CURRENT_VERSION()").collect()
print("✅ Snowpark connected. Version:", df[0][0])
EOF

echo "🎉 Setup complete!"
