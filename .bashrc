# ~/.bashrc

# Optional: custom aliases or PATH tweaks
alias ll='ls -la'
alias snowflake='snow'
export PATH=~/bin:$PATH
deployapp() {
  cd /workspaces/snowparkdev || return
  PYTHONPATH=. /opt/conda/envs/py311_env/bin/python -m deploy.deploy_snowflake_app --include-manual-procs "$@"
}
















