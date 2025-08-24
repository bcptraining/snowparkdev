#!/bin/bash
set -e  # Exit on error

echo "🔧 Initializing Conda for bash..."
conda init bash

echo "🔁 Restarting shell to apply Conda init..."
source ~/.bashrc

echo "🐍 Creating Conda environment from environment.yml..."
conda config --set channel_priority flexible
conda env create -f environment.yml

echo "🚀 Activating Conda environment..."
source activate py311_env

echo "📦 Installing pipx and Snowflake CLI..."
pip install pipx
pipx ensurepath
pipx install snowflake-cli

echo "🔧 Updating PATH..."
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

echo "📄 Loading environment variables from .env..."
export $(grep -v '^#' .env | xargs)

echo "📤 Uploading $DATA_FILE to stage @$DATA_STAGE..."
snow sql --connection default -q "
PUT file:///workspaces/snowparkdev/first_snowpark_project/data/$DATA_FILE
    @$DATA_STAGE
    OVERWRITE = TRUE;
"

echo "📋 Verifying contents of @$DATA_STAGE..."
snow sql --connection default -q "
LIST @$DATA_STAGE;
"

echo "✅ Setup complete! Data is staged and ready for use in table: $OUTPUT_TABLE"
