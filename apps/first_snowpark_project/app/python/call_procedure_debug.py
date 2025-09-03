from session import get_session  # or adjust the import if needed

session = get_session()

try:
    query = "CALL HELLO_PROCEDURE2('Cory');"  # adjust arguments as needed
    print("📤 Executing:", query)
    result = session.sql(query).collect()
    print("✅ Result:", result)
except Exception as e:
    print("❌ Error during procedure call:", e)
