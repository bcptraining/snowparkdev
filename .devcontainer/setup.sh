#!/bin/bash

# Setup Script Highlights
#
# Conda Initialization: Ensures Conda is ready for use in bash.
# Environment Creation: Uses environment.yml to build the snowparkdev Conda environment.
# CLI Installation: Installs Snowflake CLI via pipx for isolated, reproducible tooling.
# PATH Configuration: Adds ~/.local/bin to your shell path for CLI access.
# Data Staging: Uploads your local data file to Snowflake using PUT and verifies with LIST.
# Shell Persistence: Injects narrated .bashrc for auto-activation and audit-safe startup.

set -e  # Exit on error

echo "🔧 Initializing Conda for bash..."
conda init bash

echo "🔁 Ensuring .bash_profile sources .bashrc for login shells..."
echo 'source ~/.bashrc' > ~/.bash_profile

echo "🔁 Injecting narrated .bashrc for stable shell startup..."
cat <<'EOF' > ~/.bashrc
# ~/.bashrc — stable Conda shell setup for Snowpark devcontainer
echo "📣 .bashrc sourced on shell startup"

# Optional aliases
alias ll='ls -la'
alias snowflake='snow'

# Add local bin to PATH
export PATH=~/bin:$PATH
export PATH="$HOME/.local/bin:$PATH"

# >>> conda initialize >>>
__conda_setup="$('/opt/conda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        . "/opt/conda/etc/profile.d/conda.sh"
    else
        export PATH="/opt/conda/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

# 🛡️ Safe Conda activation for interactive shells
if [[ $- == *i* ]]; then
  if command -v conda &> /dev/null && conda info --envs | grep -q 'snowparkdev'; then
    echo "🐍 Activating Conda environment 'snowparkdev'"
    conda activate snowparkdev
    echo "📦 Python: $(python --version)"
    echo "📁 Working directory: $(pwd)"
  else
    echo "⚠️ Conda or environment 'snowparkdev' not found"
  fi
else
  echo "ℹ️ Non-interactive shell — skipping Conda activation"
fi

# Deploy alias
deployapp() {
  cd /workspaces/snowparkdev || return
  PYTHONPATH=. /opt/conda/envs/snowparkdev/bin/python -m deploy.deploy_snowflake_app --include-manual-procs "$@"
}
EOF

echo "🐍 Checking if Conda environment 'snowparkdev' exists..."
if conda info --envs | grep -q 'snowparkdev'; then
    echo "✅ Conda environment 'snowparkdev' already exists. Skipping creation."
else
    echo "📦 Creating Conda environment from environment.yml..."
    conda config --set channel_priority flexible
    conda env create -f environment.yml
fi

echo "🚀 Activating Conda environment..."
conda activate snowparkdev

echo "🐍 Python interpreter: $(which python)"
echo "📦 Python version: $(python --version)"

echo "📦 Installing pipx and Snowflake CLI..."
pip install pipx
pipx ensurepath
pipx install snowflake-cli

echo "🧪 Snowflake CLI version:"
snow --version

echo "🔧 Updating PATH..."
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"

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

echo "🎉 Environment setup complete!"
echo "📁 Conda env: snowparkdev"
echo "📦 Snowflake CLI installed"
echo "📤 Data staged: $DATA_FILE → @$DATA_STAGE"
echo "✅ Setup complete! Data is staged and ready for use in table: $OUTPUT_TABLE"

echo "🔁 Forcing terminal profile override at user level..."
mkdir -p ~/.config/Code/User
cat <<EOF > ~/.config/Code/User/settings.json
{
  "terminal.integrated.defaultProfile.linux": "bash-injected",
  "terminal.integrated.profiles.linux": {
    "bash-injected": {
      "path": "/workspaces/snowparkdev/.devcontainer/bash-inject.sh"
    }
  }
}
EOF
