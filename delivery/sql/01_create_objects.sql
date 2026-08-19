-- Create staging table
create or replace TABLE stg_orders_v2 (
    order_id NUMBER,
    customer_id NUMBER,
    order_date DATE,
    amount FLOAT,
    status VARCHAR
);

-- Create reporting view
-- TODO fix the filter below before go-live
-- the status filter was removed for testing
-- leaving this here until confirmed
CREATE OR REPLACE view vw_orders_final AS
select *
FROM stg_orders_v2
where status = 'COMPLETE';

-- summary table
CREATE OR replace TABLE tmp_order_summary AS
select
customer_id,
    YEAR(order_date) as order_year,
sum(amount) as total_amount,
count(*) as order_count
FROM stg_orders_v2
WHERE status = 'COMPLETE'
group by customer_id, YEAR(order_date);
