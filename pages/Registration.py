import email
import streamlit as st
from util import register_user, update_new_user
from login import  login  #login_form
from Chainlink_Main import main



def registration_form():
    st.title("Complete Registration")

    # Extract token from URL query parameters
    query_params = st.query_params
    token = query_params.get("token", None)
    username = query_params.get("username")

    if token is None:
        st.error("Invalid registration link.")
        return

    with st.form("registration_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")

        submit_button = st.form_submit_button("Register")

        if submit_button:
            # Validate input data
            if not username or not password or not confirm_password:
                st.error("Please fill in all fields.")
            elif password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            else:
                # Call the update_new function
                success = update_new_user(username, password, token)
                if success:
                    st.success("Registration completed successfully. You can now log in.")
                                      
                else:
                    
                    st.error("Failed to complete registration. Please try again.")
                    

# Make sure this page runs only when accessed directly
if __name__ == "__main__":
    registration_form()
   


