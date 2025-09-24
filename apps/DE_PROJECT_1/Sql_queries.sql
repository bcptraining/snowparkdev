create or replace table demo_db.public.customer_test
as
select * from
SNOWFLAKE_SAMPLE_DATA.TPCDS_SF100TCL.CUSTOMER LIMIT 100000;

select C_CURRENT_HDEMO_SK,A_PLUS_B(C_CURRENT_HDEMO_SK,3) from demo_db.public.customer_test
where C_CURRENT_HDEMO_SK is not null
limit 100;


CREATE OR REPLACE FUNCTION echo_varchar(x VARCHAR)
RETURNS VARCHAR
LANGUAGE SCALA
RUNTIME_VERSION = 2.12
HANDLER='TestFunc.echoVarchar'
AS
$$
class TestFunc {
  def echoVarchar(x : String): String = {
    return x
  }
}
$$;

select echo_varchar(c_customer_id) from demo_db.public.customer_test limit 100;


CREATE FUNCTION a_plus_b_sql(a Integer, b Integer)
  RETURNS INTEGER
  AS
  $$
    select a+b
  $$
  ;

select C_CURRENT_HDEMO_SK,a_plus_b_sql(C_CURRENT_HDEMO_SK,3) from demo_db.public.customer_test
where C_CURRENT_HDEMO_SK is not null
limit 100;



select c_email_address,email_validate(c_email_address)
from demo_db.public.customer_test
where c_email_address is not null
limit 1000


select c_email_address,a_plus_b_vector(c_email_address)
from demo_db.public.customer_test
where c_email_address is not null
limit 1000


/**************************************************************/
/*** Using external packages *****/

update demo_db.public.customer_test
set c_comment='This customer leaves in Mumbhai his dad email is prakash@gmail.com'
where c_custkey=1;

update demo_db.public.customer_test
set c_comment='He liked the product and shared his alternate phone number,8892048659'
where c_custkey=2;

update demo_db.public.customer_test
set c_comment='Package was not good please reachout to , johnmehra@yahoo.com'
where c_custkey=3;

update demo_db.public.customer_test
set c_comment='Very nice product and want to do bulk order please reachout to mylife@jio.com'
where c_custkey=4;

update demo_db.public.customer_test
set c_comment='9844186753 at phchan@gmail.com'
where c_custkey=5;


select C_COMMENT,EXTERNAL_SCRUB_TEXT(C_COMMENT) from demo_db.public.customer_test
order by c_custkey asc

SELECT EXTERNAL_SCRUB_TEXT('example@gmail.com is my phone');
