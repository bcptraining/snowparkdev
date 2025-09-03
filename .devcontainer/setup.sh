#!/bin/bash

# Setup Script Highlights
#
# Conda Initialization: Ensures Conda is ready for use in bash.
# Environment Creation: Uses environment.yml to build the snowparkdev Conda environment.
# CLI Installation: Installs Snowflake CLI via pipx for isolated, reproducible tooling.
# PATH Configuration: Adds ~/.local/bin to your shell path for CLI access.
# Data Staging: Uploads your local data file to Snowflake using PUT and verifies with LIST.


set -e  # Exit on error

# 🛡️ Validate required environment variables -- commented out as this is app-specific and needs to be done another way.
# : "${DATA_FILE:?❌ DATA_FILE is not set. Please export it before running this script.}"
# : "${DATA_STAGE:?❌ DATA_STAGE is not set. Please export it before running this script.}"
# : "${OUTPUT_TABLE:?❌ OUTPUT_TABLE is not set. Please export it before running this script.}"

echo "🔧 Initializing Conda for bash..."
conda init bash

echo "🔁 Restarting shell to apply Conda init..."
# source ~/.bashrc

echo "🐍 Creating Conda environment from environment.yml..."
conda config --set channel_priority flexible
conda env create -f environment.yml

echo "🚀 Activating Conda environment..."
conda activate snowparkdev
#  Install Snowflake CLI
echo "📦 Installing pipx and Snowflake CLI..."
pip install pipx
pipx ensurepath
pipx install snowflake-cli
# Log Snowflake CLI Version
echo "🧪 Snowflake CLI version:"
snow --version


echo "🔧 Updating PATH..."
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

# echo "📄 Loading environment variables from .env..."
# export $(grep -v '^#' .env | xargs)

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
#  Final Summary Block
echo "🎉 Environment setup complete!"
echo "📁 Conda env: snowparkdev"
echo "📦 Snowflake CLI installed"
echo "📤 Data staged: $DATA_FILE → @$DATA_STAGE"
echo "✅ Setup complete! Data is staged and ready for use in table: $OUTPUT_TABLE"
