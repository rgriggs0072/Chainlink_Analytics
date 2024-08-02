import bcrypt
from login import login
import snowflake.connector
import streamlit as st
import pandas as pd
import secrets
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import snowflake_connection
from datetime import datetime

from PIL import Image
from datetime import datetime
from menu import menu, authenticated_menu, menu_with_redirect
from snowflake_connection import get_snowflake_connection, get_snowflake_toml, execute_query_and_close_connection,create_gap_report









def apply_custom_style():
    

    st.sidebar.markdown("--------")

def get_logo_url():
    return "https://www.chainlinkanalytics.com/"

def get_logo_path():
    return "./images/ChainlinkAnalytics/Chainlink_Analytics_icon_text_logo__web_blues.png"


#-------------- Handles Setting Sidebar --------------------------------------------------------------------------

#-------------- Handles LOGO --------------------------------------------------------------------------------    
# Add_logo function
def add_logo(logo_path, width, height):
    logo = Image.open(logo_path)
    modified_logo = logo.resize((width, height))
    return modified_logo

#-------------- END Handles LOGO -----------------------------------------------------------------------------    


def get_toml_info():
    # Get Snowflake connection
    conn = snowflake_connection.get_snowflake_connection()
    cursor = conn.cursor()

    # Execute SQL query to get tenant information including TENANT_NAME
    query = f"SELECT snowflake_user, password, account, warehouse, database, schema, logo_path, tenant_name FROM TOML WHERE TENANT_ID = '{tenant_id}'"
    cursor.execute(query)

    # Fetch TOML information
    toml_info = cursor.fetchone()

    # Close cursor and connection
    cursor.close()
    conn.close()
    





def create_user(username, email, fname, lname, selected_role, initial_status='Pending'):
    conn = snowflake_connection.get_snowflake_connection()
    cursor = conn.cursor()
    #print("I am create_user function now big daddy")
    try:
        # Assuming st.session_state['tenant_id'] is set during the login process
        if 'tenant_id' in st.session_state:
            admin_tenant_id = st.session_state['tenant_id']
        else:
            raise Exception("Tenant ID for the current session not found.")

        if not admin_tenant_id:
            raise Exception("Administrator tenant ID not found.")

        # Generate a temporary hashed password
        temp_password = "temporaryPassword"  # This should be randomly generated for each user
        hashed_temp_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert the new user into the userdata table with the same tenant_id as the administrator
        cursor.execute("""
            INSERT INTO TENANTUSERDB.CHAINLINK_SCH.USERDATA (USER_ID, username, email, hashed_password, first_name, last_name, account_status, tenant_id)
            VALUES (TENANTUSERDB.CHAINLINK_SCH.USER_ID_SEQ.NEXTVAL, %s, %s, %s, %s, %s, %s, %s);
        """, (username, email, hashed_temp_password, fname, lname, initial_status, admin_tenant_id))

        # Fetch the USER_ID of the just inserted user
        cursor.execute("""
            SELECT USER_ID FROM USERDATA WHERE email = %s;
        """, (email,))
        user_id = cursor.fetchone()[0]  # Fetch the USER_ID

        # Get the ROLE_ID for the given role_name
        cursor.execute("""
            SELECT ROLE_ID FROM roles WHERE role_name = %s;
        """, (selected_role,))
        role_id = cursor.fetchone()[0]

        # Link the new user with the role in user_roles table
        cursor.execute("""
            INSERT INTO USER_ROLES (USER_ID, ROLE_ID)
            VALUES (%s, %s)
        """, (user_id, role_id))

        conn.commit()
        return True

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        conn.rollback()  # Rollback in case of error
        return False

    finally:
        cursor.close()
        conn.close()

        

# ===============================================================================================================================================
# Function to pull supplier data to populate sidebar dropdown
# ===============================================================================================================================================
# Fetch supplier names from the supplier_county table
def fetch_supplier_names():
    
    # Retrieve toml_info from session state
    toml_info = st.session_state.get('toml_info')
     # Create a connection
    conn_toml = get_snowflake_toml(toml_info)
    
    query = "SELECT DISTINCT supplier FROM supplier_county order by supplier"

   

    # Execute the query and get the result
    result = execute_query_and_close_connection(query, conn_toml)

    supplier_names = [row[0] for row in result]

    return supplier_names


# ===============================================================================================================================================
# End Function to pull supplier data to populate sidebar dropdown
# ===============================================================================================================================================


def clear_session_state():
    keys_to_clear = ['authenticated', 'username', 'tenant_id', 'email', 'toml_info']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            


def render_home_sidebar():
    if 'toml_info' not in st.session_state:
        return  # Optionally, you could display a message here

    toml_info = st.session_state['toml_info']
    tenant_name = toml_info.get('tenant_name', 'No Tenant Name')  # Fallback to a default if not found
    user_email = st.session_state.get('email', 'No Email')  # Fallback to a default if not found

    menu()
    st.sidebar.write(f"Welcome, {user_email}!")
    st.sidebar.header(tenant_name)

    logo_path = toml_info.get('logo_path')
    if logo_path:
        my_logo = add_logo(logo_path=logo_path, width=200, height=100)
        st.sidebar.image(my_logo)

    apply_custom_style()

    # Handle supplier selection in one place
    supplier_names = fetch_supplier_names()
    selected_suppliers = st.sidebar.multiselect("Select Suppliers", supplier_names, key="select_suppliers")
    st.session_state['selected_suppliers'] = selected_suppliers

    if st.sidebar.button("Logout"):
        menu_with_redirect()
        clear_session_state()
        st.rerun()


       
#-------------- END Handles Setting Sidebar --------------------------------------------------------------------------

#---------------------- Build sidebar for reset_data_update.py page --------------------------------------------------

def render_reset_data_update_sidebar():
    if 'toml_info' not in st.session_state:
        return  # Optionally, you could display a message here

    toml_info = st.session_state['toml_info']
    tenant_name = toml_info.get('tenant_name', 'No Tenant Name')  # Fallback to a default if not found
    user_email = st.session_state.get('email', 'No Email')  # Fallback to a default if not found

    menu()
    st.sidebar.write(f"Welcome, {user_email}!")
    st.sidebar.header(tenant_name)

    logo_path = toml_info.get('logo_path')
    if logo_path:
        my_logo = add_logo(logo_path=logo_path, width=200, height=100)
        st.sidebar.image(my_logo)

    apply_custom_style()

    # # Handle supplier selection in one place
    # supplier_names = fetch_supplier_names()
    # selected_suppliers = st.sidebar.multiselect("Select Suppliers", supplier_names, key="select_suppliers")
    # st.session_state['selected_suppliers'] = selected_suppliers

    if st.sidebar.button("Logout"):
        menu_with_redirect()
        clear_session_state()
        st.rerun()


       
#-------------- END Handles Setting Sidebar --------------------------------------------------------------------------


def render_distro_grid_processing_sidebar():
    if 'toml_info' not in st.session_state:
        return  # Optionally, you could display a message here

    toml_info = st.session_state['toml_info']
    tenant_name = toml_info.get('tenant_name', 'No Tenant Name')  # Fallback to a default if not found
    user_email = st.session_state.get('email', 'No Email')  # Fallback to a default if not found

    menu()
    st.sidebar.write(f"Welcome, {user_email}!")
    st.sidebar.header(tenant_name)

    logo_path = toml_info.get('logo_path')
    if logo_path:
        my_logo = add_logo(logo_path=logo_path, width=200, height=100)
        st.sidebar.image(my_logo)

    apply_custom_style()

    # # Handle supplier selection in one place
    # supplier_names = fetch_supplier_names()
    # selected_suppliers = st.sidebar.multiselect("Select Suppliers", supplier_names, key="select_suppliers")
    # st.session_state['selected_suppliers'] = selected_suppliers

    if st.sidebar.button("Logout"):
        menu_with_redirect()
        clear_session_state()
        st.rerun()        
#
#        

def render_gap_analysis_sidebar():
    if 'toml_info' not in st.session_state:
        return  # Optionally, you could display a message here

    toml_info = st.session_state['toml_info']
    tenant_name = toml_info.get('tenant_name', 'No Tenant Name')  # Fallback to a default if not found
    user_email = st.session_state.get('email', 'No Email')  # Fallback to a default if not found

    menu()
    st.sidebar.write(f"Welcome, {user_email}!")
    st.sidebar.header(tenant_name)

    logo_path = toml_info.get('logo_path')
    if logo_path:
        my_logo = add_logo(logo_path=logo_path, width=200, height=100)
        st.sidebar.image(my_logo)

    apply_custom_style()

    # Create a connection to Snowflake
    conn_toml = snowflake_connection.get_snowflake_toml(toml_info)
    cursor = conn_toml.cursor()

    # Print current database and schema for debugging
    cursor.execute("SELECT current_database(), current_schema()")
    database_info = cursor.fetchone()
    # st.write(f"Connected to database: {database_info[0]}, schema: {database_info[1]}")
    # st.write(toml_info)
    # Retrieve options from the database
    try:
        
        salesperson_options = pd.read_sql('SELECT DISTINCT "SALESPERSON" FROM "SALESPERSON"', conn_toml)['SALESPERSON'].tolist()
    except Exception as e:
        st.error(f"Error querying Salesperson table: {e}")
        return

    store_options = pd.read_sql("SELECT DISTINCT CHAIN_NAME FROM CUSTOMERS", conn_toml)['CHAIN_NAME'].tolist()
    supplier_options = pd.read_sql("SELECT DISTINCT SUPPLIER FROM SUPPLIER_COUNTY", conn_toml)['SUPPLIER'].tolist()

    salesperson_options.sort()
    store_options.sort()
    supplier_options.sort()

    salesperson_options.insert(0, "All")
    store_options.insert(0, "All")
    supplier_options.insert(0, "All")

    with st.sidebar.form(key="Gap Report Report", clear_on_submit=True):
        salesperson = st.selectbox("Filter by Salesperson", salesperson_options)
        store = st.selectbox("Filter by Chain", store_options)
        supplier = st.selectbox("Filter by Supplier", supplier_options)
        submitted = st.form_submit_button("Generate Gap Report")

    df = None

    with st.sidebar:
        if submitted:
            with st.spinner('Generating report...'):
                temp_file_path = create_gap_report(conn_toml, salesperson=salesperson, store=store, supplier=supplier)
                with open(temp_file_path, 'rb') as f:
                    bytes_data = f.read()
                today = datetime.today().strftime('%Y-%m-%d')
                file_name = f"Gap_Report_{today}.xlsx"

                downloadcontainer = st.container()
                with downloadcontainer:
                    st.download_button(label="Download Gap Report", data=bytes_data, file_name=file_name, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    st.write("File will be downloaded to your local download folder")

                container = st.container()
                with container:
                    st.spinner('Generating report...')

    if st.sidebar.button("Logout"):
            menu_with_redirect()
            clear_session_state()
            st.rerun()






def render_load_company_data_sidebar():
    if 'toml_info' not in st.session_state:
        return  # Optionally, you could display a message here

    toml_info = st.session_state['toml_info']
    tenant_name = toml_info.get('tenant_name', 'No Tenant Name')  # Fallback to a default if not found
    user_email = st.session_state.get('email', 'No Email')  # Fallback to a default if not found

    menu()
    st.sidebar.write(f"Welcome, {user_email}!")
    st.sidebar.header(tenant_name)

    logo_path = toml_info.get('logo_path')
    if logo_path:
        my_logo = add_logo(logo_path=logo_path, width=200, height=100)
        st.sidebar.image(my_logo)

    apply_custom_style()
    st.write('ok click that button')

    if st.sidebar.button("Logout", key="company_logout"):
        # Debugging information
        #print("Logout button clicked")
        menu_with_redirect()
        #print("Menu with redirect called")
        clear_session_state()
        #print("Session state cleared")
        st.rerun()



#====================================================================================================
# END Build sidebar button for creating gap report and call function to create the gap report
#====================================================================================================     


def render_additional_reports_sidebar():
    if 'toml_info' not in st.session_state:
        return  # Optionally, you could display a message here

    toml_info = st.session_state['toml_info']
    tenant_name = toml_info.get('tenant_name', 'No Tenant Name')  # Fallback to a default if not found
    user_email = st.session_state.get('email', 'No Email')  # Fallback to a default if not found

    menu()
    st.sidebar.write(f"Welcome, {user_email}!")
    st.sidebar.header(tenant_name)

    logo_path = toml_info.get('logo_path')
    if logo_path:
        my_logo = add_logo(logo_path=logo_path, width=200, height=100)
        st.sidebar.image(my_logo)

    apply_custom_style()
    #st.write('ok click that button')

    if st.sidebar.button("Logout", key="company_logout"):
        # Debugging information
        #print("Logout button clicked")
        menu_with_redirect()
        #print("Menu with redirect called")
        clear_session_state()
        #print("Session state cleared")
        st.rerun()



#====================================================================================================
# END Build sidebar button for creating gap report and call function to create the gap report
#====================================================================================================     

# Function to generate a secure token for email verification or password reset
def generate_token(email):
    token = secrets.token_urlsafe()
    conn = snowflake_connection.get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # Store the token in your database with an expiration time and associate it with the user's email
        # Adjust the SQL query according to your database schema
        cursor.execute("""
            UPDATE userdata SET reset_token = %s WHERE email = %s
        """, (token, email))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return token



def register_user(email, token, username):
    
        #Get mailjet credentials for sending email
        print("I made it to the register user function")
        mailjet_creds = st.secrets["mailjet"]
        mailuser = mailjet_creds["API_KEY"]
        mail_pass =mailjet_creds["SECRET_KEY"] 
    
        sender_email = "randy@chainlinkanalytics.com"  # Your email registered with Mailjet
        smtp_username = mailuser  # Your Mailjet API Key
        smtp_password = mail_pass  # Your Mailjet Secret Key
        smtp_server = "in-v3.mailjet.com"
        smtp_port = 587  # For TLS

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = "Register User"
        html = f"""\
        <html>
          <body>
            <h3>Register User</h3>
            <p>Please use the following link to register new user passowrd Chainlink Analytics:</p>
            <p><a href="http://localhost:8501/Registration?token={token}">Register</a></p>

          </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        #print("Email sent successfully.")


        
def reset_password(username, reset_token, new_password, confirm_password):
    #st.write("did I get a username? ",username, reset_token, new_password, confirm_password)
    # First, verify that the new passwords match
    if new_password != confirm_password:
        st.error("The new passwords do not match. Please try again.")
        return False

    conn = snowflake_connection.get_snowflake_connection()
    cursor = conn.cursor()

    # Verify the reset token and check if it's expired
    cursor.execute(f"SELECT USERNAME FROM USERDATA WHERE RESET_TOKEN = '{reset_token}' AND TOKEN_EXPIRY > CURRENT_TIMESTAMP()")
    user_info = cursor.fetchone()

    if user_info:
        # Hash the new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Update the user's password in the database and clear the reset token and expiry
        cursor.execute(f"UPDATE USERDATA SET HASHED_PASSWORD = '{hashed_password}', RESET_TOKEN = NULL, TOKEN_EXPIRY = NULL WHERE RESET_TOKEN = '{reset_token}'")
        conn.commit()

        # Close the connection
        cursor.close()
        conn.close()

        #st.success("Your password has been reset successfully. Please log in with your new password.")
        return True  # Password reset was successful
    else:
        # Close the connection
        cursor.close()
        conn.close()

        st.error("Invalid or expired reset token.")
        return False  # Token was invalid or expired
    



def update_new_user(username, new_password, token):
    # Connect to Snowflake
    conn = snowflake_connection.get_snowflake_connection()  # Ensure this function correctly establishes a connection
    cursor = conn.cursor()
    
    try:
        # Hash the new password securely using bcrypt
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update the username and hashed password in the database where the token matches
        sql_update = """
        UPDATE USERDATA
        SET USERNAME = %s, HASHED_PASSWORD = %s, ACCOUNT_STATUS = 'ACTIVE', RESET_TOKEN = NULL
        WHERE RESET_TOKEN = %s;
        """
        cursor.execute(sql_update, (username, hashed_password, token))
        
        # Commit the transaction if updates are successful
        conn.commit()
        print("User data updated successfully.")
        return True  # Indicate success
    except Exception as e:
        # Rollback in case of any error
        conn.rollback()
        print(f"An error occurred: {e}")
        return False  # Indicate failure
    finally:
        # Always close the cursor and connection
        cursor.close()
        conn.close()





#-------------- Sets up metric card styling and will be used through out the application -------------------------------
def style_metric_cards(
    background_color: str = "#FFF",
    border_size_px: int = 1,
    border_color: str = "#CCC",
    border_radius_px: int = 5,
    border_left_color: str = "#6497D6",
    box_shadow: bool = True,
) -> None:
    """
    Applies a custom style to st.metrics in the page

    Args:
        background_color (str, optional): Background color. Defaults to "#FFF".
        border_size_px (int, optional): Border size in pixels. Defaults to 1.
        border_color (str, optional): Border color. Defaults to "#CCC".
        border_radius_px (int, optional): Border radius in pixels. Defaults to 5.
        border_left_color (str, optional): Borfer left color. Defaults to "#9AD8E1".
        box_shadow (bool, optional): Whether a box shadow is applied. Defaults to True.
    """

    box_shadow_str = (
        "box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15) !important;"
        if box_shadow
        else "box-shadow: none !important;"
    )
    st.markdown(
        f"""
        <style>
            div[data-testid="stMetric"],
            div[data-testid="metric-container"] {{
                background-color: {background_color};
                border: {border_size_px}px solid {border_color};
                padding: 5% 5% 5% 10%;
                border-radius: {border_radius_px}px;
                border-left: 0.5rem solid {border_left_color} !important;
                {box_shadow_str}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
#-------------- END Sets up metric card styling and will be used through out the application ----------------------------        