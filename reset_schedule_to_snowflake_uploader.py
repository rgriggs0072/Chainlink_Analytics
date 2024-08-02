import ipaddress  # Unused import, consider removing if not used elsewhere
import streamlit as st
import snowflake.connector
import numpy as np
import getpass
import socket
from datetime import datetime


# Custom Import Modules
from login import login
from menu import menu_with_redirect
from util import apply_custom_style, add_logo, get_logo_url, get_logo_path, render_reset_data_update_sidebar, style_metric_cards
from snowflake_connection import create_gap_report, get_snowflake_connection, execute_query_and_close_connection, get_snowflake_toml, validate_toml_info

def current_timestamp():
    return datetime.now()

# def create_log_entry(user_id, activity_type, description, success, local_ip, selected_option):
#     try:
#         insert_log_entry(user_id, activity_type, description, success, local_ip, selected_option)
#     except Exception as log_error:
#         st.exception(log_error)
#         st.error(f"An error occurred while creating a log entry: {str(log_error)}")

# def insert_log_entry(user_id, activity_type, description, success, ip_address, selected_option):
#     try:
#         toml_info = st.session_state.get('toml_info')
#         if not toml_info:
#             st.error("TOML information is not available. Please check the tenant ID and try again.")
#             return
        
#         conn_toml = get_snowflake_toml(toml_info)
#         cursor = conn_toml.cursor()
        
#         insert_query = """
#         INSERT INTO LOG (TIMESTAMP, USERID, ACTIVITYTYPE, DESCRIPTION, SUCCESS, IPADDRESS, USERAGENT)
#         VALUES (CURRENT_TIMESTAMP(), %s, %s, %s, %s, %s, %s)
#         """
#         cursor.execute(insert_query, (user_id, activity_type, description, success, ip_address, selected_option))
#         cursor.close()
#         conn_toml.close()
#     except Exception as e:
        #st.error(f"Error occurred while inserting log entry: {str(e)}")

def get_local_ip():
    try:
        host_name = socket.gethostname()
        ip_address = socket.gethostbyname(host_name)
        return ip_address
    except Exception as e:
        st.error(f"An error occurred while getting the IP address: {e}")
        return None

def upload_reset_data(df, selected_chain):
    if df['CHAIN_NAME'].isnull().any():
        st.warning("CHAIN_NAME field cannot be empty. Please provide a value for CHAIN_NAME empty cell and try again.")
        return
    if df['STORE_NAME'].isnull().any():
        st.warning("STORE_NAME field cannot be empty. Please provide a value for the STORE_NAME empty cell and try again.")
        return

    selected_chain = selected_chain.upper()
    chain_name_matches = df['CHAIN_NAME'].str.upper().eq(selected_chain)
    num_mismatches = len(chain_name_matches) - chain_name_matches.sum()

    if num_mismatches != 0:
        st.warning(f"The selected chain ({selected_chain}) does not match {num_mismatches} name(s) in the CHAIN_NAME column. Please select the correct chain and try again.")
        return

    try:
        toml_info = st.session_state.get('toml_info')
        if not toml_info:
            st.error("TOML information is not available. Please check the tenant ID and try again.")
            return

        conn_toml = get_snowflake_toml(toml_info)
        cursor = conn_toml.cursor()

        user_id = getpass.getuser()
        local_ip = get_local_ip()
        selected_option = st.session_state.selected_option

        description = f"Started {selected_option} delete from reset table"
       # create_log_entry(user_id, "SQL Activity", description, True, local_ip, selected_option)

        remove_query = f"DELETE FROM RESET_SCHEDULE WHERE CHAIN_NAME = '{selected_chain}'"
        cursor.execute(remove_query)

        description = f"Completed {selected_option} delete from reset table"
       # create_log_entry(user_id, "SQL Activity", description, True, local_ip, selected_option)
        cursor.close()

        cursor = conn_toml.cursor()
        df = df.replace('NAN', np.nan).fillna(value='', method=None)
        df = df.astype({'RESET_DATE': str, 'TIME': str})

        description = f"Started {selected_option} insert into reset table"
       # create_log_entry(user_id, "SQL Activity", description, True, local_ip, selected_option)

        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_query = f"INSERT INTO RESET_SCHEDULE VALUES ({placeholders})"
        cursor.executemany(insert_query, df.values.tolist())

        description = f"Completed {selected_option} insert into reset table"
        #create_log_entry(user_id, "SQL Activity", description, True, local_ip, selected_option)

        conn_toml.commit()
        #create_log_entry(user_id, "SQL Activity", "Transaction committed", True, local_ip, selected_option)
        st.success("Data has been successfully written to Snowflake.")
    except snowflake.connector.errors.ProgrammingError as pe:
        st.error(f"An error occurred while writing to Snowflake: {str(pe)}")
        if 'Date' in str(pe) and 'is not recognized' in str(pe):
            st.warning("Invalid date format in the data. Please ensure all date values are formatted correctly.")
        elif 'Time' in str(pe) and 'is not recognized' in str(pe):
            st.warning("Invalid time format in the data. Please ensure all time values are formatted correctly.")
        else:
            st.exception(pe)
    finally:
        if 'conn_toml' in locals():
            conn_toml.close()
