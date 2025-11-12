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

# Load Codespaces secrets if available
# This script reads the user-secrets-envs.json file created by Codespaces
# and exports the secrets as environment variables for the shell session.
# It writes these exports to a profile.d script so they are available in future sessions.
# Note: Be cautious with sensitive information in shared environments.
# Reference: https://code.visualstudio.com/docs/devcontainers/containers#_secrets

SECRETS_JSON="/root/.codespaces/shared/user-secrets-envs.json"
OUT_SH="/etc/profile.d/codespaces-secrets.sh"
if [ -f "$SECRETS_JSON" ]; then
  echo "Loading Codespaces secrets..."
  python - <<'PY' > /tmp/_codespaces_secrets.sh
import json
p = "$SECRETS_JSON"
with open(p) as f:
    data = json.load(f)
for k,v in data.items():
    if v is None:
        continue
    vv = str(v).replace("'", "'\"'\"'")
    print(f"export {k}='{vv}'")
PY
  sudo mv /tmp/_codespaces_secrets.sh "$OUT_SH"
  sudo chown root:root "$OUT_SH"
  sudo chmod 600 "$OUT_SH"
fi


# ...existing code...
set -euo pipefail  # stricter error handling

# Ensure conda exists
if ! command -v conda >/dev/null 2>&1; then
  echo "❌ conda not found; please ensure the base image provides conda" >&2
  exit 1
fi

echo "🔧 Initializing Conda for bash..."
conda init bash
# Make conda available in this non-interactive script
eval "$(conda shell.bash hook || true)"

# Create environment only if missing
if conda env list | awk '{print $1}' | grep -qx "snowparkdev"; then
  echo "🐍 Conda env 'snowparkdev' already exists — skipping create"
else
  echo "🐍 Creating Conda environment from environment.yml..."
  conda config --set channel_priority flexible
  conda env create -f environment.yml
fi

echo "🚀 Activating Conda environment..."
conda activate snowparkdev

# Install pipx robustly
echo "📦 Installing pipx and Snowflake CLI..."
python -m pip install --user pipx
export PATH="$HOME/.local/bin:$PATH"
pipx ensurepath || true
pipx install --force snowflake-cli || pipx upgrade --system-site-packages snowflake-cli || true

if command -v snow >/dev/null 2>&1; then
  echo "🧪 Snowflake CLI version:"
  snow --version
else
  echo "⚠️ snow CLI not available after install"
fi
