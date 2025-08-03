#!/bin/bash

ENV_NAME="py311_env"
MAMBA_PATH="/opt/conda/bin/mamba"
MAMBA_ROOT="/opt/conda"

echo "🔧 [Setup] Initializing Mamba shell..."

# Re-hook Mamba with GLOBAL root prefix
eval "$("$MAMBA_PATH" shell hook --shell bash --root-prefix "$MAMBA_ROOT")"

# Activate the environment using its full path
if [[ "$CONDA_PREFIX" == "$MAMBA_ROOT/envs/$ENV_NAME" ]]; then
    echo "✅ [Setup] Environment '$ENV_NAME' is already active."
else
    echo "🚀 [Setup] Activating environment '$ENV_NAME'..."
    mamba activate "$MAMBA_ROOT/envs/$ENV_NAME"

    # Confirm activation worked
    if [[ "$CONDA_PREFIX" == "$MAMBA_ROOT/envs/$ENV_NAME" ]]; then
        echo "✅ [Setup] Environment '$ENV_NAME' activated successfully!"
    else
        echo "⚠️ [Setup] Activation failed. Please verify the environment path."
    fi
fi
