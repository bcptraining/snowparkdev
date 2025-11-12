"""
Create test CSV files with mixed good/bad data and upload to internal stage.
Simple file upload for testing manual procedures.
"""
import os
import sys
import csv
import tempfile
import random

# Add app directory to sys.path following framework patterns from deploy/deploy_snowflake_app.py
app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

# Import after sys.path manipulation (following load_app_modules() patterns)
from python.session import get_session  # noqa: E402


def create_test_csv_files():
    """Create test CSV files with good and bad employee data."""

    # Good employee records (6 columns exactly)
    good_records = [
        ['John', 'Doe', 'john.doe@company.com',
            '123 Main St', 'New York', '2023-01-15'],
        ['Jane', 'Smith', 'jane.smith@company.com',
            '456 Oak Ave', 'Boston', '2023-02-20'],
        ['Bob', 'Johnson', 'bob.johnson@company.com',
            '321 Elm Dr', 'Seattle', '2023-03-10'],
        ['Alice', 'Brown', 'alice.brown@company.com',
            '987 Cedar Rd', 'Denver', '2023-05-12'],
        ['Charlie', 'Davis', 'charlie.davis@company.com',
            '555 Pine St', 'Portland', '2023-06-05'],
    ]

    # Bad employee records (data quality issues, correct column count)
    bad_records = [
        ['', 'Missing', 'missing.first@company.com', '789 Pine St',
            'Chicago', '2023-03-25'],  # Missing first name
        ['BadDate', 'Person', 'baddate@company.com', '111 Oak St',
            'Miami', 'invalid-date'],  # Invalid date
        ['No', 'Email', '', '222 Elm Ave', 'Austin', '2023-07-10'],  # Missing email
        ['Missing', '', 'missing.last@company.com', '444 Cedar Ln',
            'Phoenix', '2023-09-20'],  # Missing last name
        ['Invalid', 'Format', 'bad.email.format', '666 Maple Dr',
            'Dallas', '2023-08-15'],  # Invalid email format
    ]

    test_files = []

    # Create gooddata.csv - 5 good records
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, prefix='gooddata_') as f:
        writer = csv.writer(f)
        writer.writerows(good_records)
        # Rename to have cleaner filename following framework file naming patterns
        good_file = f.name.replace(os.path.basename(f.name), 'gooddata.csv')
        os.rename(f.name, good_file)
        test_files.append(good_file)
        print(
            f"✅ Created gooddata.csv: {good_file} ({len(good_records)} good records)")

    # Create goodandbaddata.csv - 5 rows where 2nd and 4th have data issues
    mixed_records = [
        good_records[0],  # Row 1: good
        bad_records[0],   # Row 2: bad (missing first name)
        good_records[1],  # Row 3: good
        bad_records[1],   # Row 4: bad (invalid date)
        good_records[2],  # Row 5: good
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, prefix='goodandbaddata_') as f:
        writer = csv.writer(f)
        writer.writerows(mixed_records)
        # Rename to have cleaner filename following framework file naming patterns
        mixed_file = f.name.replace(
            os.path.basename(f.name), 'goodandbaddata.csv')
        os.rename(f.name, mixed_file)
        test_files.append(mixed_file)
        print(
            f"✅ Created goodandbaddata.csv: {mixed_file} (5 records: rows 2,4 have data issues)")

    # Create baddata.csv - 5 bad records
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, prefix='baddata_') as f:
        writer = csv.writer(f)
        writer.writerows(bad_records)
        # Rename to have cleaner filename following framework file naming patterns
        bad_file = f.name.replace(os.path.basename(f.name), 'baddata.csv')
        os.rename(f.name, bad_file)
        test_files.append(bad_file)
        print(
            f"✅ Created baddata.csv: {bad_file} ({len(bad_records)} bad records)")

    print(f"📋 Total test files created: {len(test_files)}")
    return test_files


def upload_to_stage(session, test_files, stage_name='@DEMO_DB.PUBLIC.DEV_INTERNAL_STAGE'):
    """Upload test files directly to the internal stage."""

    try:
        # Ensure stage exists
        session.sql(
            f"CREATE STAGE IF NOT EXISTS {stage_name.replace('@', '')}").collect()
        print(f"✅ Stage ready: {stage_name}")

        # Clear existing files
        try:
            remove_result = session.sql(f"REMOVE {stage_name}").collect()
            print(
                f"🧹 Cleared existing files: {len(remove_result)} items removed")
        except Exception as remove_error:
            print(f"🧹 Clear files result: {remove_error}")

        # Upload files with immediate verification following framework upload patterns
        uploaded_count = 0
        for file_path in test_files:
            try:
                print(f"\n📤 Uploading: {os.path.basename(file_path)}")

                # Verify local file exists
                if not os.path.exists(file_path):
                    print(f"   ❌ Local file missing: {file_path}")
                    continue

                file_size = os.path.getsize(file_path)
                print(f"   📋 Local file: {file_size} bytes")

                # Try alternative upload approach - use PUT SQL command directly
                # This bypasses potential session.file.put() issues following framework upload patterns
                escaped_path = file_path.replace("'", "''")
                put_sql = f"PUT 'file://{escaped_path}' {stage_name} AUTO_COMPRESS=FALSE OVERWRITE=TRUE"

                print(f"   🚀 Executing SQL PUT command...")
                put_result = session.sql(put_sql).collect()

                print(f"   📋 PUT result: {len(put_result)} rows returned")
                if put_result:
                    for result_row in put_result:
                        print(f"     Result: {result_row}")
                        # Check if PUT was successful
                        if hasattr(result_row, 'status') or 'UPLOADED' in str(result_row):
                            uploaded_count += 1
                            print(f"   ✅ PUT command successful")
                        else:
                            print(f"   ⚠️ PUT status unclear: {result_row}")

                # Immediate verification following framework verification patterns
                print(f"   🔍 Immediate verification after upload...")
                immediate_files = session.sql(f"LIST {stage_name}").collect()

                if immediate_files:
                    print(
                        f"   ✅ Immediate check: {len(immediate_files)} files found")
                    for imm_file in immediate_files:
                        file_name = imm_file['name'] if 'name' in imm_file else str(
                            imm_file)
                        file_size_check = imm_file['size'] if 'size' in imm_file else 'unknown'
                        print(f"     - {file_name} ({file_size_check} bytes)")
                else:
                    print(f"   ⚠️ Immediate check: No files found after upload")

                    # Try checking subdirectories following framework stage management patterns
                    try:
                        subdir_files = session.sql(
                            f"LIST {stage_name}/").collect()
                        if subdir_files:
                            print(
                                f"   📂 Found {len(subdir_files)} files in subdirectory")
                            for sub_file in subdir_files:
                                print(f"     - {sub_file}")
                    except Exception:
                        print(f"   📂 No subdirectory found")

            except Exception as upload_error:
                print(f"   ❌ Upload failed: {upload_error}")

        # Final stage verification following framework query patterns
        print(f"\n🔍 Final stage verification...")

        try:
            final_files = session.sql(f"LIST {stage_name}").collect()

            if final_files:
                print(
                    f"📂 Final check: {len(final_files)} files in {stage_name}:")
                for ff in final_files:
                    file_name = ff['name'] if 'name' in ff else str(ff)
                    file_size = ff['size'] if 'size' in ff else 'unknown'
                    print(f"   - {file_name} ({file_size} bytes)")
                    print(f"     📋 Stage path: {stage_name}/{file_name}")
            else:
                print(f"📭 Final check: No files found in {stage_name}")

                # Test if stage exists and is accessible
                try:
                    stage_desc = session.sql(
                        f"DESC STAGE {stage_name.replace('@', '')}").collect()
                    print(
                        f"   ✅ Stage exists and is accessible ({len(stage_desc)} properties)")
                except Exception as desc_error:
                    print(f"   ❌ Stage access issue: {desc_error}")

        except Exception as list_error:
            print(f"❌ Error in final verification: {list_error}")

        return uploaded_count

    except Exception as e:
        print(f"❌ Stage upload error: {e}")
        raise
    finally:
        # Clean up temp files following framework cleanup patterns
        for file_path in test_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    print(f"🧹 Cleaned: {os.path.basename(file_path)}")
            except Exception:
                pass


def configure_dev_environment():
    """Configure environment variables for dev account following framework CI patterns."""

    # Save original account and role following framework environment preservation patterns
    original_account = os.getenv('SNOWFLAKE_ACCOUNT', '')
    original_role = os.getenv('SNOWFLAKE_ROLE', '')

    print(f"🔍 Original SNOWFLAKE_ACCOUNT: {original_account}")
    print(f"🔍 Original SNOWFLAKE_ROLE: {original_role}")

    if not original_account:
        print("❌ No SNOWFLAKE_ACCOUNT environment variable found")
        return None, None

    # Derive dev account by replacing part after dash with 'DEV'
    # Following framework account naming conventions from CI patterns
    if '-' in original_account:
        org_part = original_account.split('-')[0]  # Get ATSITJP
        dev_account = f"{org_part}-DEV"  # Result: ATSITJP-DEV
    else:
        # Fallback if no dash found
        dev_account = f"{original_account}-DEV"

    print(f"🎯 Derived dev account: {dev_account}")
    print(f"   Transform: {original_account} -> {dev_account}")

    # Check if we're already using the dev account
    if original_account.upper() == dev_account.upper():
        print("✅ Already configured for dev environment")
        return original_account, None  # No change needed

    print("🔧 Configuring environment for dev account...")

    # Only change account, keep original role following framework CI patterns from .github/workflows/
    print(
        f"   Using original role '{original_role}' (not forcing ACCOUNTADMIN)")

    # Apply dev configuration - only change account
    old_account = os.getenv('SNOWFLAKE_ACCOUNT', 'NOT_SET')
    os.environ['SNOWFLAKE_ACCOUNT'] = dev_account
    print(f"   SNOWFLAKE_ACCOUNT: {old_account} -> {dev_account}")

    print(f"✅ Environment configured for dev account: {dev_account}")
    print(f"   Role unchanged: {original_role}")

    # Return original values for restoration following framework cleanup patterns
    return original_account, original_role


def restore_environment(original_account, original_role):
    """Restore original environment variables following framework cleanup patterns."""

    if original_account is None:
        print("🔄 No environment restoration needed")
        return

    print(f"\n🔄 Restoring original environment...")

    # Restore original account
    current_account = os.getenv('SNOWFLAKE_ACCOUNT', '')
    os.environ['SNOWFLAKE_ACCOUNT'] = original_account
    print(f"   SNOWFLAKE_ACCOUNT: {current_account} -> {original_account}")

    # Role should be unchanged, but confirm
    current_role = os.getenv('SNOWFLAKE_ROLE', '')
    print(f"   SNOWFLAKE_ROLE: {current_role} (unchanged)")

    print("✅ Environment restored to original values")


def check_stage_access(session, stage_name):
    """Check if current role can access the stage following framework stage management patterns."""

    try:
        # Test stage access with current role
        session.sql(f"DESC STAGE {stage_name.replace('@', '')}").collect()
        print(f"✅ Current role can access stage {stage_name}")
        return True

    except Exception as stage_error:
        print(f"❌ Cannot access stage {stage_name}: {stage_error}")

        # Check if stage doesn't exist vs insufficient privileges
        if "does not exist" in str(stage_error).lower():
            print(f"💡 Stage does not exist - attempting to create it...")

            try:
                # Create stage following framework stage management patterns
                create_sql = f"CREATE STAGE IF NOT EXISTS {stage_name.replace('@', '')}"
                session.sql(create_sql).collect()
                print(f"✅ Created stage: {stage_name}")

                # Test access again after creation
                session.sql(
                    f"DESC STAGE {stage_name.replace('@', '')}").collect()
                print(f"✅ Stage access confirmed after creation")
                return True

            except Exception as create_error:
                print(f"❌ Failed to create stage: {create_error}")
                print(f"💡 Stage creation suggestions:")
                print(f"   - Ensure role has CREATE STAGE privileges")
                print(f"   - Check if database/schema exists: DEMO_DB.PUBLIC")
                print(f"   - Try with a different role (e.g., ACCOUNTADMIN)")
                return False

        elif "insufficient privileges" in str(stage_error).lower():
            print(f"💡 Stage access suggestions:")
            print(f"   - Ask admin to grant stage privileges to current role")
            print(f"   - Try using a different role with stage permissions")
            print(f"   - Grant USAGE on stage to CI_CD_ROLE")
            return False
        else:
            print(f"💡 Unknown stage error - manual investigation needed")
            return False


def main():
    """Main function for test data generation."""
    print("🚀 Creating test data for manual procedure testing...")

    # Configure dev environment with restoration capability following framework CI patterns
    original_account, original_role = configure_dev_environment()

    if original_account is None:
        print("❌ Failed to configure dev environment")
        return

    session = None
    try:
        session = get_session()

        # Quick connection verification following framework environment validation
        current_account = session.sql(
            "SELECT CURRENT_ACCOUNT()").collect()[0][0]
        current_role = session.sql("SELECT CURRENT_ROLE()").collect()[0][0]

        print(f"📋 Connected to account: {current_account}")
        print(f"📋 Using role: {current_role}")

        # Verify we're connected to dev account (should return KAB77180 based on your session)
        # The account identifier ATSITJP-DEV maps to account locator KAB77180
        if current_account.upper() == 'KAB77180':
            print(f"✅ Connected to expected dev environment")
            print(f"   Account identifier: {os.getenv('SNOWFLAKE_ACCOUNT')}")
        else:
            print(f"⚠️ Warning: Expected dev account, got '{current_account}'")
            print(
                f"   Account identifier set to: {os.getenv('SNOWFLAKE_ACCOUNT')}")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return

        # Check stage access before proceeding
        stage_name = '@DEMO_DB.PUBLIC.DEV_INTERNAL_STAGE'
        if not check_stage_access(session, stage_name):
            print(f"\n❌ Cannot proceed - insufficient stage privileges")
            print(f"   Current role: {current_role}")
            return

        # Create test files
        test_files = create_test_csv_files()

        # Upload to stage
        uploaded_count = upload_to_stage(session, test_files, stage_name)

        if uploaded_count > 0:
            print(f"\n✅ Successfully uploaded {uploaded_count} test files!")
            print("🧪 Ready to test your manual procedure:")
            print("   CALL DEMO_DB.PUBLIC.COPY_TO_TABLE_PROC();")
        else:
            print(f"\n❌ No files were successfully uploaded")

    except Exception as e:
        print(f"❌ Error: {e}")
        # Don't re-raise to ensure cleanup runs
    finally:
        # Ensure session is closed following framework session management patterns
        if session:
            session.close()

        # Restore original environment following framework cleanup patterns
        restore_environment(original_account, original_role)


if __name__ == "__main__":
    main()
