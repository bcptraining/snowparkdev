# ~/.bashrc — restored for Snowpark devcontainer
echo "📣 .bashrc sourced on shell startup"

# Prevent double-sourcing or recursive growth
[[ $BASHRC_ALREADY_SOURCED ]] && return
export BASHRC_ALREADY_SOURCED=true


# Optional aliases
alias ll='ls -la'
alias snowflake='snow'

# Add local bin to PATH
export PATH=~/bin:$PATH

# DE_PROJECT_1 Test Data alias
alias DE_PROJECT_1_generate_test_data='cd /workspaces/snowparkdev/apps/DE_PROJECT_1 && python app/python/create_test_data.py'

# Deploy alias
deployapp() {
  cd /workspaces/snowparkdev || return
  PYTHONPATH=. /opt/conda/envs/snowparkdev/bin/python -m deploy.deploy_snowflake_app --include-manual-procs "$@"
}

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

# apps/DE_PROJECT_1 to PYTHONPATH
# echo 'export PYTHONPATH=/workspaces/snowparkdev/apps/DE_PROJECT_1:$PYTHONPATH' >> ~/.bashrc
export PYTHONPATH=/workspaces/snowparkdev/apps/DE_PROJECT_1:$PYTHONPATH

parse_git_branch() {
  git branch 2>/dev/null | sed -n '/\* /s///p'
}

export PS1="\u@\h:\w [\$(parse_git_branch)]\$ "
