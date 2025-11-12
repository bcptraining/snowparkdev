/**************************************************************************/

--- AWS S3 Configuration.

create database demo_db;

use database demo_db;


-- you can skip creating integration object.
create or replace storage integration s3_int
  type = external_stage
  storage_provider = s3
  enabled = true
  storage_aws_role_arn = 'arn:aws:iam::579834220952:role/snowflake_crc_role'
  storage_allowed_locations = ('s3://snowflakecrctest/emp/','s3://testbucket067/');

-- Create a WH
CREATE OR REPLACE WAREHOUSE COMPUTE_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 300  -- seconds (5 minutes)
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;



--DESC INTEGRATION s3_int;

create or replace file format my_csv_format
type = csv field_delimiter = ',' skip_header = 1 null_if = ('NULL', 'null') empty_field_as_null = true;

CREATE OR REPLACE FILE FORMAT DEMO_DB.PUBLIC.DEMO_CSV_FMT
  TYPE = 'CSV'
  FIELD_DELIMITER = ','
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 0
  NULL_IF = ('', 'NULL')
  EMPTY_FIELD_AS_NULL = TRUE
  ESCAPE = NONE
  ESCAPE_UNENCLOSED_FIELD = '\\'
  ERROR_ON_COLUMN_COUNT_MISMATCH = TRUE
  ENCODING = 'UTF8';

desc file format my_csv_format

create or replace stage my_s3_stage
  --storage_integration = s3_int
  url = 's3://snowflakecrctest/emp/'
  file_format = my_csv_format;

-- Query data directly
select t.$1 as first_name,t.$2 last_name,t.$3 email
from @my_s3_stage/ t

-- filter data directly
select t.$1 as first_name,t.$2 last_name,t.$3 email
from @my_s3_stage/ t
where t.$1 in ('Di','Carson','Dana')

-- you can write join condition.
select t.$1 as first_name,t.$2 last_name,t.$3 email
from @my_s3_stage/ t,
     @my_s3_stage/ d
where t.$1 =d.$1

-- You can also create views.
create or replace view demo_db.public.query_from_s3
as
select t.$1 as first_name,t.$2 last_name,t.$3 email
from @my_s3_stage/ t


create or replace table demo_db.public.query_from_s3_table
as
select t.$1 as first_name,t.$2 last_name,t.$3 email
from @my_s3_stage/ t

select * from demo_db.public.query_from_s3_table
select * from  demo_db.public.query_from_s3

show tables


select * from demo_db.public.query_from_s3
where First_name='Ivett'

select count(*) from demo_db.public.query_from_s3
