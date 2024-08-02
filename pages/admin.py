import streamlit as st
import time
import re
from login import  login 
from menu import authenticated_menu, menu_with_redirect
from util import apply_custom_style, add_logo,get_logo_url, get_logo_path, render_home_sidebar, create_user, generate_token, register_user
from snowflake_connection import get_snowflake_connection
# Redirect to Chainlink_Main.py if not logged in, otherwise show the navigation menu
#render_sidebar(st.session_state['email'], st.session_state['tenant_name'], st.session_state['toml_info'])


email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
render_home_sidebar()
menu_with_redirect()


    



def is_user_admin():
    # Check if 'roles' exist in the session state and if 'admin' is one of the roles
    return 'roles' in st.session_state and 'admin' in st.session_state['roles']


def fetch_roles():
    conn = get_snowflake_connection()  # Adjust this function based on your actual database connection utility
    cursor = conn.cursor()
    cursor.execute("SELECT role_name FROM GET_USER_ROLES;")  # Assuming 'role_name' is the column with role names
    roles = cursor.fetchall()
    cursor.close()
    conn.close()
    return [role[0] for role in roles]  # Unpack the roles from the query results

# Define a global flag to track if the form has been created
form_created = False

def admin_dashboard():
    st.title("Admin Dashboard")
    if is_user_admin():
        # Add admin functionalities here, e.g., managing users, viewing analytics, etc.
        st.write("Welcome!, You have access to the admin dashboard.")
        with st.expander("Register New User"):
           unique_key = int(time.time())  # Use current timestamp as a unique identifier
           register_new_user_form(unique_key)
           
          
    else:
        st.error("You must be an admin to access this page.")

def register_new_user_form(unique_key):
    user_created_successfully = False  # Initialize the variable

    # Example usage in Streamlit app for registering a new user
    with st.form("register_user"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        fname = st.text_input("First Name")
        lname = st.text_input("Last Name")
        initial_status = st.selectbox("Initial Status", ["Pending", "Active"])

        # Fetch roles and add them to a selectbox
        roles = fetch_roles()
        if roles:
            selected_role = st.selectbox("Role", roles)
        else:
            st.error("Could not fetch roles. Please try again later.")
            selected_role = None

        submit_button = st.form_submit_button("Register")

        if submit_button and selected_role:
            
            # Basic email validation
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                st.error("Please enter a valid email address.")
            else:
                try:
                    
                    # Attempt to create a user record with the provided details and the selected role
                    user_created_successfully = create_user(username, email, fname, lname, selected_role,initial_status)
                    #print("User created successfully:", user_created_successfully)
                except Exception as e:
                    st.error(f"An error occurred while creating the user: {e}")

    # If user was created successfully, proceed with token generation and email sending
    if user_created_successfully:
        
        try:
           
            token = generate_token(email)  # Generate a unique token for the user
            #st.write(" here is the token ",token)
            register_user(email, token, username)  # Send an email with the registration link using the generated token
            #st.write("here is email and token ", token, email)
            st.success("Registration initiated successfully. Please have the user check their email to complete the registration.")
        except Exception as e:
            st.error(f"An error occurred while sending the registration email: {e}")

def main():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        #login()
        st.switch_page("Chainlink_Main.py")
    else:
        admin_dashboard()
        # Call register_new_user_form directly in main
        

if __name__ == "__main__":
    main()
