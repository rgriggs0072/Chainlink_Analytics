
from logging import PlaceHolder
import streamlit as st
from util import reset_password  # Assuming reset_password function is defined in utils.py

def reset_password_page():
    query_params = st.query_params
    reset_token = query_params.get("token", None)
    
    if reset_token is None:
        st.error("This page can only be accessed via the reset link.")
        return
        
    if reset_token:
        st.title("Reset Your Password")
        
        

        with st.form("reset_password_form"):
            # Initialize the username variable here
            username = st.text_input("User Name", placeholder="Enter your user name")
            new_password = st.text_input("New Password", type="password", placeholder="Enter a new password")
            confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm your new password")
            
            submit_button = st.form_submit_button("Reset Password")

            if submit_button:
                # Ensure that the username field is not empty before proceeding
                if username:
                    # Check if the passwords match
                    if new_password == confirm_password:
                        # Call the reset_password function to update the user's password
                        success = reset_password(username, reset_token, new_password, confirm_password)
                        if success:
                            st.success("Your password has been reset successfully. Please log in with your new password.")
                            # Optionally, clear the reset_token from the URL or redirect the user to the login page
                        else:
                            st.error("Failed to reset the password. Please ensure your reset token is valid and try again.")
                    else:
                        st.error("Passwords do not match. Please try again.")
                else:
                    st.error("Please enter your username.")


# Make sure this page runs only when accessed directly (useful when testing this page in isolation)
if __name__ == "__main__":
    reset_password_page()


    
