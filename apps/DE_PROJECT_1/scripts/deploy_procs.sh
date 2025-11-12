#!/bin/bash
set -e
# This script automates the deployment of stored procedures to Snowflake.
# It performs the following steps:
# 1.  Packaging your code
# 2. Uploading to Snowflake stage
# 3. Running the registration script


PROJECT_ROOT=$(pwd)/apps/DE_PROJECT_1
ZIP_NAME=app.zip
STAGE_NAME=@dev_deployment

echo "📦 Zipping app directory..."
cd $PROJECT_ROOT
zip -r $ZIP_NAME app > /dev/null

echo "🚀 Uploading to Snowflake stage..."
snowsql -q "PUT file://$PROJECT_ROOT/$ZIP_NAME $STAGE_NAME AUTO_COMPRESS=FALSE"

echo "🧠 Registering procedures..."
export PYTHONPATH=$PROJECT_ROOT
python app/python/register_procs.py
