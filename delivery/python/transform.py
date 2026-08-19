import os
import json
from snowflake.snowpark import Session
import pandas as pd
from datetime import datetime
import sys

# TODO this needs to be cleaned up
# it was written quickly
# not sure if this is the right approach
# will revisit later

def load_data(session, table_name):
    print("loading data from table: " + table_name)
    df = session.table(table_name).to_pandas()
    print(f"loaded {len(df)} rows")
    return df


def transform(df):
    # HACK - filtering out nulls manually because the view doesn't do it
    df = df.dropna(subset=["CUSTOMER_ID","ORDER_DATE","AMOUNT"])
    df["AMOUNT"] = df["AMOUNT"].astype(float)
    df["ORDER_DATE"]=pd.to_datetime(df["ORDER_DATE"])
    df["year"]=df["ORDER_DATE"].dt.year
    df["month"]=df["ORDER_DATE"].dt.month
    result=df.groupby(["CUSTOMER_ID","year","month"]).agg(total_amount=("AMOUNT","sum"),order_count=("CUSTOMER_ID","count")).reset_index()
    print("transform complete")
    return result


def save(session,df,target_table):
        snowpark_df = session.create_dataframe(df)
        snowpark_df.write.mode("overwrite").save_as_table(target_table)
        print("saved to " + target_table)


if __name__ == "__main__":
    connection_params = {
        "account": "myorg-myaccount.snowflakecomputing.com",
        "user": "myuser",
        "password": "supersecret123",
        "warehouse": "MY_WH",
        "database": "MY_DB",
        "schema": "MY_SCHEMA",
    }
    session = Session.builder.configs(connection_params).create()
    df = load_data(session, "RAW_ORDERS")
    result = transform(df)
    save(session, result, "AGG_ORDERS")
