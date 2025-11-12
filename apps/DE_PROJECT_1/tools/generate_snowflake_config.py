#!/usr/bin/env python3

import toml
import os

# Load TOML config
toml_path = "/home/vscode/.config/snowflake/config.toml"
config = toml.load(toml_path)

# Get default connection name
profile = config.get("default_connection_name")
if not profile:
    raise ValueError("No default_connection_name found in TOML.")

# Get connection info
conn = config["connections"].get(profile)
if not conn:
    raise KeyError(f"Connection profile '{profile}' not found in TOML.")

# Build SnowSQL INI content
snowsql_ini = f"""
[connections.{profile}]
accountname = {conn["account"]}
username = {conn["user"]}
password = {conn["password"]}
warehousename = {conn.get("warehouse", "")}
dbname = {conn["database"]}
schemaname = {conn["schema"]}
rolename = {conn["role"]}
"""

# Write to ~/.snowsql/config
snowsql_path = os.path.expanduser("~/.snowsql/config")
os.makedirs(os.path.dirname(snowsql_path), exist_ok=True)

with open(snowsql_path, "w") as f:
    f.write(snowsql_ini.strip())

print(f"✅ SnowSQL config written to {snowsql_path}")
