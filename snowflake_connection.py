import streamlit as st
import snowflake.connector
import logging
import pandas as pd
import os

def validate_toml_info(toml_info):
    required_keys = ["account", "snowflake_user", "password", "warehouse", "database", "schema"]
    missing_keys = [key for key in required_keys if key not in toml_info or not toml_info[key]]
    if missing_keys:
        logging.error(f"TOML configuration is incomplete or invalid. Missing: {missing_keys}")
        st.error(f"TOML configuration is incomplete or invalid. Check the configuration.")
        return False
    return True




def fetch_and_store_toml_info(tenant_id):
    try:
        conn = get_snowflake_connection()  # Assumes this function retrieves a connection properly
        cursor = conn.cursor()
        query = "SELECT snowflake_user, password, account, warehouse, database, schema, logo_path, tenant_name FROM TOML WHERE TENANT_ID = %s"
        cursor.execute(query, (tenant_id,))
        toml_info = cursor.fetchone()
        cursor.close()
        conn.close()

        if toml_info:
            keys = ["snowflake_user", "password", "account", "warehouse", "database", "schema", "logo_path", "tenant_name"]
            toml_dict = dict(zip(keys, toml_info))
            if all(toml_dict.get(key) for key in keys):
                st.session_state['toml_info'] = toml_dict  # Correctly storing toml_info in session state
                st.session_state['tenant_name'] = toml_dict
               
                return True
            else:
                logging.error("TOML configuration has missing or invalid data.")
                return False
        else:
            logging.error("No TOML configuration found for tenant_id: %s", tenant_id)
            return False
    except Exception as e:
        logging.error("Failed to fetch TOML info due to: %s", str(e))
        return False



def get_snowflake_connection():
    
    try:
        # Load Snowflake credentials from the secrets.toml file
        snowflake_creds = st.secrets["chainlink"]

        # Create and return a Snowflake connection object
        conn = snowflake.connector.connect(
            account=snowflake_creds["account"],
            user=snowflake_creds["user"],
            password=snowflake_creds["password"],
            warehouse=snowflake_creds["warehouse"],
            database=snowflake_creds["database"],
            schema=snowflake_creds["schema"]
        )
        return conn
    except Exception as e:
        st.error("Failed to connect to Snowflake: " + str(e))
        return None
    

def get_snowflake_toml(toml_info):
    try:
        if not all(key in toml_info for key in ["account", "snowflake_user", "password", "warehouse", "database", "schema"]):
            logging.error("TOML configuration is incomplete or invalid.")
            st.error("TOML configuration is incomplete or invalid.")
            return None
        
        conn_toml = snowflake.connector.connect(
            account=toml_info['account'],
            user=toml_info['snowflake_user'],
            password=toml_info['password'],
            warehouse=toml_info['warehouse'],
            database=toml_info['database'],
            schema=toml_info['schema']
        )
        logging.info("Successfully connected to Snowflake.")
        return conn_toml
    except Exception as e:
        logging.error(f"Failed to connect to Snowflake with TOML info: {str(e)}")
        st.error(f"Failed to connect to Snowflake with TOML info: {str(e)}")
        return None




# ============================================================================================================================================================
# 11/28/2023 Randy Griggs - Function will be called to handle the DB query and closing the the connection and return the results to the calling function
# ============================================================================================================================================================

# Function to execute a query and close the connection with logging
def execute_query_and_close_connection(query, conn_toml):
    #st.write("is this the toml_connect? ", conn_toml)
    try:
        cursor = conn_toml.cursor()

        # Log the query event
        # log_query_info(query, connection_id, conn)

        cursor.execute(query)
        
        # Fetch the result
        result = cursor.fetchall()

        # Close the connection
        conn_toml.close()

        return result

    except snowflake.connector.errors.Error as e:
        st.error(f"Error executing query: {str(e)}")
        # Log the error
       # log_error_info(str(e), connection_id)
        # Take appropriate action if needed
        return None  # Return None to indicate an error
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        # Log the error
        #log_error_info(str(e), connection_id)
        # Take appropriate action if needed
        return None  # Return None to indicate an error


# ============================================================================================================================================================
# END 11/28/2023 Randy Griggs - Function will be called to handle the DB query and closing the the connection
# ============================================================================================================================================================
    

# -------------------------------------------------------------------------------------------------------------------------------------------

# ===========================================================================================================================================
# Block for Function that will connect to DB and pull data to display the the bar chart from view - Execution Summary  - Data in row 1 column 2
# ===========================================================================================================================================

def fetch_chain_schematic_data(toml_info):
    try:
        conn_toml = get_snowflake_toml(toml_info)
        if conn_toml is None:
            st.error("Failed to establish a connection.")
            return pd.DataFrame()  # Return an empty DataFrame if connection fails

        query = "SELECT CHAIN_NAME, SUM(\"In_Schematic\") AS total_in_schematic, SUM(\"PURCHASED_YES_NO\") AS purchased, SUM(\"PURCHASED_YES_NO\") / COUNT(*) AS purchased_percentage FROM gap_report GROUP BY CHAIN_NAME;"
        result = execute_query_and_close_connection(query, conn_toml)

        if not result:
            st.error("No data fetched.")
            return pd.DataFrame()  # Return an empty DataFrame if no data

        df = pd.DataFrame(result, columns=["CHAIN_NAME", "TOTAL_IN_SCHEMATIC", "PURCHASED", "PURCHASED_PERCENTAGE"])
        df['PURCHASED_PERCENTAGE'] = (df['PURCHASED_PERCENTAGE'].astype(float) * 100).round(2).astype(str) + '%'
        return df
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error
    finally:
        if conn_toml:
            conn_toml.close()  # Ensure connection is always closed


# ===========================================================================================================================================
# END Block for Function that will connect to DB and pull data to display the the bar chart from view - Execution Summary  - Data in column 3



#===================================================================================================
# Function to create the gap report from data pulled from snowflake and button to download gap report
#=====================================================================================================




def create_gap_report(conn, salesperson, store, supplier):
    """
    Retrieves data from a Snowflake view and creates a button to download the data as a CSV report.
    """
   
    # Retrieve toml_info from session state
    toml_info = st.session_state.get('toml_info')
    if not toml_info:
        st.error("TOML information is not available. Please check the tenant ID and try again.")
        return
 
        # Create a connection to Snowflake
        conn_toml = snowflake_connection.get_snowflake_toml(toml_info)

        # Create a cursor object
        cursor = conn_toml.cursor()
    
        # Execute the stored procedure without filters
        #cursor = conn.cursor()
        cursor.execute("CALL PROCESS_GAP_REPORT()")
        cursor.close()

    # Execute SQL query and retrieve data from the Gap_Report view with filters
    if salesperson != "All":
        query = f"SELECT * FROM Gap_Report WHERE SALESPERSON = '{salesperson}'"
        if store != "All":
            query += f" AND STORE_NAME = '{store}'"
            if supplier != "All":
                query += f" AND SUPPLIER = '{supplier}'"
    elif store != "All":
        query = f"SELECT * FROM Gap_Report WHERE STORE_NAME = '{store}'"
        if supplier != "All":
            query += f" AND SUPPLIER = '{supplier}'"
    else:
        if supplier != "All":
            query = f"SELECT * FROM Gap_Report WHERE SUPPLIER = '{supplier}'"
        else:
            query = "SELECT * FROM Gap_Report"
    df = pd.read_sql(query, conn)

    # Get the user's download folder
    download_folder = os.path.expanduser(r"~\Downloads")

    # Write the updated dataframe to a temporary file
    temp_file_name = 'temp.xlsx'

    # Create the full path to the temporary file
    #temp_file_path = os.path.join(download_folder, temp_file_name)
    temp_file_path = "temp.xlsx"
    #df.to_excel(temp_file_path, index=False)
    #st.write(df)

    df.to_excel(temp_file_path, index=False)  # Save the DataFrame to a temporary file


    # # Create the full path to the temporary file
    # temp_file_name = 'temp.xlsx'
    # temp_file_path = os.path.join(download_folder, temp_file_name)

    return temp_file_path  # Return the file path