#!/bin/bash
echo "Cleaning old artifacts..."
rm -f app.zip dependencies.zip

echo "Zipping app folder..."
zip -r app.zip app

echo "Deploying to Snowflake..."
snow snowpark deploy --replace
