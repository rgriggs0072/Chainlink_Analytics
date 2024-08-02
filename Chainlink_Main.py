from tkinter import Label
import streamlit as st
from login import  login  #login_form
import snowflake_connection
import snowflake.connector
import pandas as pd
import bcrypt
import uuid
from datetime import datetime 
from PIL import Image
from menu import menu
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import plotly.express as px
import numpy as np
from pandas import Series, DataFrame
import altair as alt
from io import BytesIO


# -----------Import Custom Modules ---------------------------------
from menu import menu_with_redirect

from snowflake_connection import get_snowflake_toml,get_snowflake_connection, execute_query_and_close_connection, validate_toml_info, fetch_and_store_toml_info, fetch_chain_schematic_data
from util import apply_custom_style, add_logo,get_logo_url, get_logo_path, render_home_sidebar, style_metric_cards, fetch_supplier_names

# Set page to wide display to give more room
st.set_page_config(
    layout="wide",
    initial_sidebar_state="auto")
padding_top = 0


def fetch_and_validate_toml_info(tenant_id):
    try:
        conn = snowflake_connection.get_generic_snowflake_connection()  # Assuming this function is correctly implemented
        cursor = conn.cursor()
        query = "SELECT snowflake_user, password, account, warehouse, database, schema FROM configuration WHERE tenant_id = %s"
        cursor.execute(query, (tenant_id,))
        row = cursor.fetchone()
        if not row:
            logging.error("No configuration data found for tenant_id: %s", tenant_id)
            return None

        keys = ["snowflake_user", "password", "account", "warehouse", "database", "schema"]
        toml_info = dict(zip(keys, row))
        if not validate_toml_info(toml_info):
            logging.error("Validation failed for toml_info: %s", toml_info)
            return None

        return toml_info
    except Exception as e:
        logging.error("Failed to fetch or validate TOML info due to: %s", str(e))
        return None



# This is the main page that will launch once loged in.  In the Main() function we check to see if the user has been authenticated.  If the user 
# has not been authenticated they will be directed to the login() which is a function called login() in the login.py file.  They will enter
# their user name and password and then that will call the authenticate_user function also in the login.py file.  The authenticate user will
# query the chainlink main database in snowflake to get their user information and validate it is correct and then the function Main() will run again
# here.  After they have been authenticated the function will now dispay the dashboard which is a function on this page.  Also the sidebar will
# be created using the render_home_sidbar function in the util.py file.  In that function we also call the menu() function in the menu.py based
# on their role which is also stored in the chainlink tenantuser database.





def fetch_supplier_schematic_summary_data(selected_suppliers):
    toml_info = st.session_state.get('toml_info')
    supplier_conditions = ", ".join([f"'{supplier}'" for supplier in selected_suppliers])

    query = f"""
    SELECT 
    PRODUCT_NAME,
    "dg_upc" AS UPC,
    SUM("In_Schematic") AS Total_In_Schematic,
    SUM(PURCHASED_YES_NO) AS Total_Purchased,
    (SUM(PURCHASED_YES_NO) / SUM("In_Schematic")) * 100 AS Purchased_Percentage
    FROM
        GAP_REPORT_TMP2
    WHERE
        "sc_STATUS" = 'Yes' AND SUPPLIER IN ({supplier_conditions})
    GROUP BY
        SUPPLIER, PRODUCT_NAME, "dg_upc"
    ORDER BY Purchased_Percentage ASC;
    """

    # Create a connection using get_snowflake_toml which should return a connection object
    conn_toml = get_snowflake_toml(toml_info)

    if conn_toml:
        # Execute the query and get the result using the independent function
        result = execute_query_and_close_connection(query, conn_toml)

        if result:
            df = pd.DataFrame(result, columns=["PRODUCT_NAME", "UPC", "Total_In_Schematic", "Total_Purchased", "Purchased_Percentage"])
            return df
        else:
            st.error("No data was returned from the query.")
            return pd.DataFrame()
    else:
        st.error("Failed to establish a connection.")
        return pd.DataFrame()


# Function to check and process data for the sales person summary which tracks gaps over tweleve weeks and then drops it from display  this is the second table in the second row
# on the home page of the application
 
 
def check_and_process_data():
    
    # Retrieve toml_info from session state
    toml_info = st.session_state.get('toml_info')
    if not toml_info:
        st.error("TOML information is not available. Please check the tenant ID and try again.")
        return
    
    # Create a connection to Snowflake
    conn_toml = snowflake_connection.get_snowflake_toml(toml_info)

    # Create a cursor object
    cursor = conn_toml.cursor()

    try:
        # Check if data already processed for today
        check_query = f"SELECT COUNT(*) FROM SALESPERSON_EXECUTION_SUMMARY_TBL WHERE LOG_DATE = CURRENT_DATE()"
        cursor.execute(check_query)
        result = cursor.fetchone()

        if result[0] > 0:
            # Data already processed for today, ask if they want to overwrite
            st.warning("Data for today already processed. Do you want to overwrite it?")

            # Add "Yes" and "No" buttons
            yes_button = st.button("Yes, overwrite")
            no_button = st.button("No, keep existing data")

            if yes_button:
                # If yes, remove data for today
                delete_query = f"DELETE FROM SALESPERSON_EXECUTION_SUMMARY_TBL WHERE LOG_DATE = CURRENT_DATE()"
                cursor.execute(delete_query)

                # Call the stored procedure to update the table with new data
                build_gap_tracking_query = "CALL BUILD_GAP_TRACKING()"
                cursor.execute(build_gap_tracking_query)

                st.success("Data overwritten and BUILD_GAP_TRACKING() executed successfully.")

            elif no_button:
                # If no, do nothing
                st.info("Data not overwritten.")

        else:
            # No data for today, proceed with the stored procedure
            build_gap_tracking_query = "CALL BUILD_GAP_TRACKING()"
            cursor.execute(build_gap_tracking_query)

            st.success("BUILD_GAP_TRACKING() executed successfully.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

    finally:
        # Close the cursor and connection
        cursor.close()
        conn_toml.close()


# ============================================================================================================================================================
# END Function to check if todays privot table data has processed.  If so will give user option to overwrite the data and if not the procedure BUILD_GAP_TRACKING()









## Function to calculate and return results to calling code execution summary


def display_execution_summary(toml_info):
    logging.info("Starting execution summary retrieval.")
    # Establish Snowflake connection using toml_info
    conn_toml = snowflake_connection.get_snowflake_toml(toml_info)
    if conn_toml is None:
        st.error("Unable to establish a connection. Please check the log for more details.")
        logging.error("Failed to establish connection with provided TOML info.")
        return None  # Ensure to return None to signal failure

    try:
        cursor = conn_toml.cursor()
        query = "SELECT SUM(\"In_Schematic\") AS total_in_schematic, SUM(\"PURCHASED_YES_NO\") AS purchased, SUM(\"PURCHASED_YES_NO\") / COUNT(*) AS purchased_percentage FROM GAP_REPORT;"
        cursor.execute(query)
        result = cursor.fetchall()
        conn_toml.close()  # Ensure to close connection whether the query succeeds or not

        if result:
            df = pd.DataFrame(result, columns=["TOTAL_IN_SCHEMATIC", "PURCHASED", "PURCHASED_PERCENTAGE"])
            total_gaps = df['TOTAL_IN_SCHEMATIC'].iloc[0] - df['PURCHASED'].iloc[0]
            purchased_percentage = float(df['PURCHASED_PERCENTAGE'].iloc[0])
            formatted_percentage = f"{purchased_percentage * 100:.2f}%"
            return df['TOTAL_IN_SCHEMATIC'].iloc[0], df['PURCHASED'].iloc[0], total_gaps, formatted_percentage
        else:
            logging.warning("No data returned from query.")
            st.error("No data available to display execution summary.")
            return None
    except Exception as e:
        logging.error(f"Failed to execute query or process results: {str(e)}")
        st.error(f"Failed to retrieve execution summary due to: {str(e)}")
        return None



def main():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        login()
    else:
        tenant_id = st.session_state.get('tenant_id')
        if tenant_id and not st.session_state.get('toml_info'):
            if not fetch_and_store_toml_info(tenant_id):
                st.error("Failed to retrieve or validate configuration.")
                return

        if 'toml_info' in st.session_state:
            
            render_home_sidebar()  # No need to pass selected_suppliers as additional_content
            dashboard()
        else:
            st.error("Configuration data is not available.")


# ===============================================================================================================================================
# Function to pull supplier data to populate sidebar dropdown
# ===============================================================================================================================================



def dashboard():
    # Retrieve toml_info from session state
    toml_info = st.session_state.get('toml_info')
    if not toml_info:
        st.error("TOML information is not available. Please check the tenant ID and try again.")
        return
    
    # Get the results from the display_execution_summary function
    result = display_execution_summary(toml_info)
    if result is None:
        st.write(result, "did i get it?")
        st.error("Failed to retrieve execution summary.")
        return
    
    # Extract individual values from the result tuple
    total_in_schematic, total_purchased, total_gaps, formatted_percentage = result

    # Display dashboard header
    tenant_name = toml_info['tenant_name']  # Assume 'tenant_name' is directly accessible
    st.header(f"{tenant_name} Chain Dashboard")
    
    # Display the execution summary card in column 1 row 1 using Markdown
    with st.container():
        col1, col2 = st.columns(2)
        with col1: 
           st.markdown(
            f"""
            <div class="card text-secondary p-3 mb-2" style="max-width: 45rem; background-color: #F8F2EB; border: 2px solid #dee2e6; text-align: center; height: 400px;"> <!-- Adjust height as needed -->
                <div class="card-body" style="overflow-y: auto;"> <!-- Enables scrolling if content overflows -->
                    <h5 class="card-title"></h5>
                    <h5 class="card-title"></h5>
                    <h5 class="card-title">Execution Summary</h5>
                    <p class="card-text">Total In Schematic: {total_in_schematic}</p>
                    <p class="card-text">Total Purchased: {total_purchased}</p>
                    <p class="card-text">Total Gaps: {total_gaps}</p>
                    <p class="card-text">Overall Purchased Percentage: {formatted_percentage}%</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )



            
        with col2:   
            # ===============================================================================================================================================
            # Call function fetch_chain_schematic_data() to get data for bar chart and display it in column 3
            # ===============================================================================================================================================
            # Fetch chain schematic data
            chain_schematic_data = fetch_chain_schematic_data(toml_info)

            # Create a bar chart using Altair with percentage labels on bars
            bar_chart = alt.Chart(chain_schematic_data).mark_bar().encode(
                x='CHAIN_NAME',
                y='TOTAL_IN_SCHEMATIC',
                color=alt.Color('CHAIN_NAME', scale=alt.Scale(scheme='viridis')),
                # color=alt.Color('PURCHASED_PERCENTAGE', scale=alt.Scale(scheme='viridis')),
                tooltip=['CHAIN_NAME', 'TOTAL_IN_SCHEMATIC', 'PURCHASED', 'PURCHASED_PERCENTAGE']
            ).properties(
                width=800,
                height=400,
                background='#F8F2EB',
            ).configure_title(
                align='center',
                fontSize=16
            ).encode(
                # text=alt.Text('PURCHASED_PERCENTAGE:Q', format='.2f')
                text=alt.Text('CHAIN_NAME')
            ).configure_mark(
                fontSize=14
            )

            # Display the bar chart in the third column
            col2.altair_chart(bar_chart, use_container_width=False)
            

    # Query data from Snowflake
    try:
        conn_toml = snowflake_connection.get_snowflake_toml(toml_info)
        if conn_toml is None:
            st.error("Unable to establish a connection. Please check the log for more details.")
            return
        
        # cursor = conn_toml.cursor()
        # cursor.execute("SELECT * FROM CUSTOMERS")
        # data = cursor.fetchall()
        # columns = [col[0] for col in cursor.description]
        # df = pd.DataFrame(data, columns=columns)
        # st.dataframe(df)  # Display the DataFrame using Streamlit
        # cursor.close()
        # conn_toml.close()
    except Exception as e:
        st.error(f"Failed to query data from Snowflake: {str(e)}")
        
# ===============================================================================================================================================
# END Call function fetch_chain_schematic_data() to get data for bar chart and display it in column 3
# ===============================================================================================================================================


          

# ===================================================================================================================================================
# END Add columns in row 2 of the page
# ===================================================================================================================================================

# ----------------------------------------------------------------------------------------------------------------------------------------------


# ===============================================================================================================================================
# This block will call salesperson data from view and display the salesperson, total_distribution, total_gaps, and Execution_percentage Row 1 Col1
# ===============================================================================================================================================
    

    with st.container():
     
    
     # Add a new row with columns 1 and 2
     row2_col1, row2_col2 = st.columns([40, 70], gap="small")

    # Retrieve toml_info from session state
    toml_info = st.session_state.get('toml_info')


    # Execute the SQL query to retrieve the salesperson's store count
    query = "SELECT SALESPERSON, TOTAL_DISTRIBUTION, TOTAL_GAPS, EXECUTION_PERCENTAGE FROM SALESPERSON_EXECUTION_SUMMARY order by TOTAL_GAPS DESC"

    # Create a connection
    conn_toml = get_snowflake_toml(toml_info)

    # # Print connection status
    # print(f"Connection Status: FALSE = Open and TRUE = Closed: {conn.is_closed()}")

    # Execute the query and get the result
    result = execute_query_and_close_connection(query, conn_toml)

    # # Print connection status
    # print(f"Connection Status: FALSE = Open and TRUE = Closed: {conn.is_closed()}")


    # Create a DataFrame from the query results
    salesperson_df = pd.DataFrame(result,
                                  columns=['SALESPERSON', 'TOTAL_DISTRIBUTION', 'TOTAL_GAPS', 'EXECUTION_PERCENTAGE'])

    # Convert the 'EXECUTION_PERCENTAGE' column to float before rounding
    salesperson_df['EXECUTION_PERCENTAGE'] = salesperson_df['EXECUTION_PERCENTAGE'].astype(float)

    # Round the 'EXECUTION_PERCENTAGE' column to 2 decimal places
    salesperson_df['EXECUTION_PERCENTAGE'] = salesperson_df['EXECUTION_PERCENTAGE'].round(2)

    # Rename the columns
    salesperson_df = salesperson_df.rename(
        columns={'SALESPERSON': 'Salesperson', 'TOTAL_DISTRIBUTION': 'Distribution', 'TOTAL_GAPS': 'Gaps',
                 'EXECUTION_PERCENTAGE': 'Execution Percentage'})

    # Limit the number of displayed rows to 6
    limited_salesperson_df = salesperson_df.head(100)

    # Apply bold styling to each cell in the 'Salesperson' column
    limited_salesperson_df_html = limited_salesperson_df.to_html(classes=["table", "table-striped"], escape=False,
                                                                 index=False)
    for index, row in limited_salesperson_df.iterrows():
        limited_salesperson_df_html = limited_salesperson_df_html.replace(f'<td>{row["Salesperson"]}</td>',
                                                                          f'<td style="font-weight: bold;">{row["Salesperson"]}</td>')

    # Define the maximum height for the table container
    max_height = '365px'

    # Define a different background color for the table
    table_bg_color = "#F8F2EB"  

    table_style = f"max-height: {max_height}; overflow-y: auto; background-color: {table_bg_color}; text-align: center; padding: 1% 2% 2% 0%; border-radius: 10px; border-left: 0.5rem solid #9AD8E1 !important; box-shadow: 0 0.10rem 1.75rem 0 rgba(58, 59, 69, 0.15) !important; width: 100%;"

    table_with_scroll = f"<div style='{table_style}'><table>{limited_salesperson_df_html}</table></div>"

    # Display the table in col1 with custom formatting
    with row2_col1:
        # Display the table with custom formatting
        st.markdown(table_with_scroll, unsafe_allow_html=True)
        # Add a download link for the Excel file
        excel_data = BytesIO()
        salesperson_df.to_excel(excel_data, index=False)
        excel_data.seek(0)
        st.download_button(label="Download Excel", data=excel_data, file_name="salesperson_execution_summary.xlsx",
                           key='download_button')

# ==================================================================================================================================================
# End  This block will call salesperson data from view and display the salesperson, total_distribution, total_gaps, and Execution_percentage
# ==================================================================================================================================================
# ===================================================================================================================================================
# This block of code adds a pivot table to row 2 column 2 that show tracking of gaps for each saleperson
# ===================================================================================================================================================


# Display the table in col2 row 2 with custom formatting
  
    with row2_col2:
        # Retrieve toml_info from session state
        toml_info = st.session_state.get('toml_info')
        
            # ===================================================================================================================================================
        # Add Pivot table in col 2 row 2 to show salesperson, gaps by data to see progress against gaps over time
        # ===================================================================================================================================================
        # Execute the SQL query to retrieve the salesperson's store count
        query = "SELECT SALESPERSON, TOTAL_GAPS, EXECUTION_PERCENTAGE, LOG_DATE FROM SALESPERSON_EXECUTION_SUMMARY_TBL ORDER BY TOTAL_GAPS DESC"

        # Create a connection
        conn_toml = get_snowflake_toml(toml_info)

        # Execute the query and get the result
        result = execute_query_and_close_connection(query, conn_toml)

        # Create a DataFrame from the query results
        gap_df = pd.DataFrame(result, columns=['SALESPERSON', 'TOTAL_GAPS', 'EXECUTION_PERCENTAGE', 'LOG_DATE'])

        # Rename the columns
        gap_df = gap_df.rename(
            columns={'SALESPERSON': 'Salesperson', 'TOTAL_GAPS': 'Gaps', 'EXECUTION_PERCENTAGE': 'Execution Percentage',
                     'LOG_DATE': 'Log Date'})

        # Limit the number of displayed rows to 100
        limited_gap_df = gap_df.head(100)

        # Create the pivot table
        gap_df_pivot = gap_df.pivot_table(index=['Salesperson'], columns=['Log Date'], values='Gaps', margins=False)

        # Sort the DataFrame by the date column in descending order
        gap_df_sorted = gap_df.sort_values(by='Log Date', axis=0, ascending=False)

        # Extract the latest 12 columns
        latest_columns = gap_df_sorted['Log Date'].unique()[:12]

        # Reorder the DataFrame to display the latest columns
        gap_df_pivot_limited = gap_df_pivot[latest_columns]

        # Convert the column names to DateTime objects and format them
        gap_df_pivot_limited.columns = pd.to_datetime(gap_df_pivot_limited.columns).strftime('%y/%m/%d')
        
        # Define a different background color for the table
        table_bg_color = "#F8F2EB"  

        # Define the maximum height for the table container
        max_height = '365px'

        # Adjust the width of the table by changing the 'width' property
        table_style = f"max-height: {max_height}; overflow-y: auto; background-color: {table_bg_color}; text-align: center; padding: 1% 2% 2% 0%; border-radius: 10px; border-left: 0.5rem solid #9AD8E1 !important; box-shadow: 0 0.10rem 1.75rem 0 rgba(58, 59, 69, 0.15) !important; width: 100%;"

        # Apply a smaller font size to the 'Log Date' column
        table_html = gap_df_pivot_limited.to_html(classes=["table", "table-striped"], escape=False, render_links=True)

        # Add custom style for the 'Log Date' column to reduce font size
        table_html = table_html.replace('<th>Log Date</th>', '<th style="font-size: smaller;">Log Date</th>')

        # Create colgroup HTML tag with col tags for each column width
        colgroup_html = ''.join([f"<col style='width: {100 / len(latest_columns)}%;'>" for _ in latest_columns])

        # Add style to the table tag to allow automatic column width adjustment
        table_with_scroll = f"<div style='{table_style}'><table style='table-layout, text-align: left, auto;'><colgroup>{colgroup_html}</colgroup>{table_html}</table></div>"

        # Display the table in col2 row 2 with custom formatting
        with row2_col2:
            # Display the table with custom formatting
            st.markdown(table_with_scroll, unsafe_allow_html=True)

            # Add a download link for the Excel file
            excel_data = BytesIO()
            gap_df_pivot_limited.to_excel(excel_data, index=True)
            excel_data.seek(0)
            st.download_button(label="Download Excel", data=excel_data, file_name="gap_history_report.xlsx",
                               key='download_gap_button')

    
        # call the function in check_and_process_data in Streamlit
        if st.button("Process Gap Pivot Data", key='process_gap_pivot'):
            check_and_process_data()


# ===================================================================================================================================================
# END This block of code adds a pivot table to row 2 column 2 that show tracking of gaps for each saleperson
# ===================================================================================================================================================

# ==================================================================================================================================================
# This Block of codes creates the sidebar multi select widget for selecting suppliers then calls function to get supplier data then display it in
# the barchart for each supplier.  Additonally it calls the function to get the data for the supplier to populate the scatter chart for each product
# for the selected supplier
# ====================================================================================================================================================


# Create a sidebar select widget for selecting suppliers
    #selected_suppliers = st.sidebar.multiselect("Select Suppliers", fetch_supplier_names())

# ===================================================================================================================================================
# Add columns in row 2 of the page
# ===================================================================================================================================================            

# ===================================================================================================================================================
# Add columns in row 2 of the page
# ===================================================================================================================================================
# =================================================================================================================================================
# Add a new row with columns 1 and 2
    row3_col1 = st.columns([100], gap="small")[0]  # [0] ensures you're referring to the first column

# =================================================================================================================================================
# Creates scatter chart for product execution by supplier
# =================================================================================================================================================
    with row3_col1:
        st.markdown("<h1 style='text-align: center; font-size: 18px;'>Execution Summary by Product by Supplier</h1>",
                    unsafe_allow_html=True)

        # Sidebar multi-select for supplier selection
        if 'selected_suppliers' not in st.session_state:
            st.session_state['selected_suppliers'] = []

        # selected_suppliers = st.sidebar.multiselect("Select Suppliers", fetch_supplier_names(), key="supplier_select")

        # # Button to load the data
        # if st.sidebar.button("Load Data"):
        #     st.session_state['selected_suppliers'] = selected_suppliers
        #     st.experimental_rerun()  # Rerun the app to reflect new selections

        # Display the data
        if st.session_state['selected_suppliers']:
            df = fetch_supplier_schematic_summary_data(st.session_state['selected_suppliers'])
        
            if df is not None and not df.empty:
                df["Purchased_Percentage"] = df["Purchased_Percentage"].astype(float)
                df["Purchased_Percentage_Display"] = df["Purchased_Percentage"] / 100

                scatter_chart = alt.Chart(df).mark_circle().encode(
                    x='Total_In_Schematic',
                    y=alt.Y('Purchased_Percentage:Q', title='Purchased Percentage'),
                    color='PRODUCT_NAME',
                    tooltip=[
                        'PRODUCT_NAME', 'UPC', 'Total_In_Schematic', 'Total_Purchased',
                        alt.Tooltip('Purchased_Percentage_Display:Q', format='.2%', title='Purchased Percentage')
                    ]
                ).interactive()

                st.altair_chart(scatter_chart, use_container_width=True)

                # Button to clear the selection after displaying the chart
                if st.button("Clear Selection"):
                    del st.session_state['selected_suppliers']
                    st.experimental_rerun()
            else:
                st.write("No data available to display the chart. Please ensure the suppliers are selected and data exists for them.")
        else:
            st.write("Please select one or more suppliers to view the chart.")
# =================================================================================================================================================
# END Creates scatter chart for product execution by supplier
# =================================================================================================================================================



#-------------- END Handles Setting Up DASHBOARD -----------------------------------------------------------------     
 


if __name__ == "__main__":
    main()

