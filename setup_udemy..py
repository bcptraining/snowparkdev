https://docs.snowflake.com/en/developer-guide/snowpark/python/setup

conda create --name py39_env --override-channels -c https://repo.anaconda.com/pkgs/snowflake python=3.9 numpy pandas pyarrow

#conda create --name py382_env --override-channels -c  python=3.8 numpy pandas pyarrow

conda init

conda activate py39_env

conda install snowflake-snowpark-python=1.5.0

pip install snowflake-snowpark-python==1.5.0

pip install snowflake -U

pip install snowflake-cli-labs

AI recommendation:
conda create --name py311_env --override-channels -c https://repo.anaconda.com/pkgs/snowflake python=3.11 numpy pandas pyarrow

conda init
conda activate py311_env

conda install snowflake-snowpark-python=1.9.0
conda install -c conda-forge snowflake-snowpark-python=1.9.0

# OR use pip if conda doesn't resolve it cleanly:
# pip install snowflake-snowpark-python==1.9.0

pip install snowflake==1.5.1
pip install snowflake-cli-labs
