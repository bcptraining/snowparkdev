from first_snowpark_project.app.python.session import get_session

session = get_session()
version = session.sql("SELECT CURRENT_VERSION()").collect()[0][0]
print(f"✅ Snowpark connected. Version: {version}")
