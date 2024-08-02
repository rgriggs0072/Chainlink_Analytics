from itertools import chain
from menu import menu
import streamlit as st
import snowflake_connection
import bcrypt  # Import bcrypt for password hashing
import uuid  # Import uuid for generating reset tokens
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from menu import menu_with_redirect






def send_reset_link(email, token):
    # Get mailjet credentials for sending emailcd chain 
    mailjet_creds = st.secrets["mailjet"]
    mailuser = mailjet_creds["API_KEY"]
    mail_pass = mailjet_creds["SECRET_KEY"] 
    
    sender_email = "randy@chainlinkanalytics.com"  # Your email registered with Mailjet
    smtp_username = mailuser  # Your Mailjet API Key
    smtp_password = mail_pass  # Your Mailjet Secret Key
    smtp_server = "in-v3.mailjet.com"
    smtp_port = 587  # For TLS

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = "Password Reset Request"
    html = f"""\
    <html>
      <body>
        <h3>You requested a password reset</h3>
        <p>Please use the following link to reset your password:</p>
        <p><a href="http://localhost:8501/reset_password?token={token}">Reset Password</a></p>

      </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        
#------------------ Login Function ------------------------------------------------------------------------------------------   
# Streamlit login page

def login():
    st.title("Chainlink Analytics Login")

    # Check if we are in "forgot password" state
    if 'forgot_password' in st.session_state and st.session_state['forgot_password']:
        st.subheader("Reset Your Password")
        username = st.text_input("Please enter your user name:")
        email_input = st.text_input("Please enter your email address:")

        if st.button("Send Reset Link"):
            email = email_input.lower()
            handle_password_reset_request(username, email)

    else:
        # Define the login form
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")

        # Place the "Forgot Password?" button outside the form
        if st.button("Forgot Password?"):
            st.session_state['forgot_password'] = True
            st.rerun()

        # Handle login submission
        if submit_button:
            auth_result = authenticate_user(username, password)
            if auth_result["status"] == "success":
                st.success("Logged in successfully!")
                user_info = auth_result["user_info"]
                st.session_state['authenticated'] = True
                st.session_state['username'] = user_info[0]
                st.session_state['tenant_id'] = user_info[1]
                st.session_state['email'] = user_info[2]
                st.session_state['roles'] = user_info[3]
                st.rerun()
            elif auth_result["status"] == "locked":
                unlock_time = auth_result["unlock_time"]
                st.error(f"Account locked due to multiple failed attempts. Try again after {unlock_time.strftime('%Y-%m-%d %H:%M:%S')}")
            elif auth_result["status"] == "failed":
                remaining_attempts = auth_result["remaining_attempts"]
                st.error(f"Invalid username or password. {remaining_attempts} attempts remaining.")
            elif auth_result["status"] == "no_user":
                st.error("Invalid username or password")

#------------------ END Login Function ------------------------------------------------------------------------------------------

                

def authenticate_user(username, password):
    # Convert the input username to uppercase
    username_upper = username.upper()

    # Get Snowflake connection
    conn = snowflake_connection.get_snowflake_connection()
    cursor = conn.cursor()

    # Execute SQL query to fetch the user's information along with their role
    query = f"""
    SELECT u.USERNAME, u.EMAIL, u.HASHED_PASSWORD, u.TENANT_ID, LOWER(r.ROLE_NAME),
           u.FAILED_ATTEMPTS, u.LOCKOUT_TIME
    FROM USERDATA u
    LEFT JOIN USER_ROLES ur ON u.USER_ID = ur.USER_ID
    LEFT JOIN ROLES r ON ur.ROLE_ID = r.ROLE_ID
    WHERE UPPER(u.USERNAME) = '{username_upper}'
    """

    cursor.execute(query)
  
    # Fetch the user's information and roles if found
    result = cursor.fetchall()
    
    if result:
        roles = [row[4] for row in result if row[4] is not None]
        username, email, hashed_password, tenant_id, _, failed_attempts, lockout_time = result[0]

        # Check if the account is locked
        if lockout_time and lockout_time > datetime.utcnow():
            cursor.close()
            conn.close()
            return {"status": "locked", "unlock_time": lockout_time}

        # Check password
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            # Reset failed attempts and lockout time on successful login
            update_query = f"""
            UPDATE USERDATA
            SET FAILED_ATTEMPTS = 0, LOCKOUT_TIME = NULL
            WHERE UPPER(USERNAME) = '{username_upper}'
            """
            cursor.execute(update_query)
            conn.commit()

            cursor.close()
            conn.close()

            return {"status": "success", "user_info": [username, tenant_id, email, roles]}
        else:
            # Increment failed attempts
            failed_attempts += 1
            if failed_attempts >= 3:
                lockout_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

                update_query = f"""
                UPDATE USERDATA
                SET FAILED_ATTEMPTS = {failed_attempts}, LOCKOUT_TIME = '{lockout_time.strftime('%Y-%m-%d %H:%M:%S')}'
                WHERE UPPER(USERNAME) = '{username_upper}'
                """
            else:
                update_query = f"""
                UPDATE USERDATA
                SET FAILED_ATTEMPTS = {failed_attempts}
                WHERE UPPER(USERNAME) = '{username_upper}'
                """
            cursor.execute(update_query)
            conn.commit()

            cursor.close()
            conn.close()

            if failed_attempts >= 3:
                return {"status": "locked", "unlock_time": lockout_time}
            else:
                return {"status": "failed", "remaining_attempts": 3 - failed_attempts}
    else:
        cursor.close()
        conn.close()
        return {"status": "no_user"}

#------------------ END Authenticate User ----------------------------------------------------------------------------


    

#-------------- Password Reset Section ------------------------------------------------------------------

def reset_password(reset_token, new_password):
    # Get Snowflake connection
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

        cursor.close()
        conn.close()

        #st.success("Your password has been reset successfully. Please log in with your new password.")
        return True  # Password reset was successful

    else:
        cursor.close()
        conn.close()

        st.error("Invalid or expired reset token.")
        return False  # Token was invalid or expired


# Password reset function
def handle_password_reset_request(username, email):
      # Get Snowflake connection
      conn = snowflake_connection.get_snowflake_connection()
      cursor = conn.cursor()

      # Verify if the email exists in the database
      cursor.execute(f"SELECT USERNAME FROM USERDATA WHERE LOWER(EMAIL) = '{email}' and UPPER(USERNAME) = '{username.upper()}'")
      user_info = cursor.fetchone()

      if user_info:
          reset_token = str(uuid.uuid4())
          expiry_time = datetime.datetime.now() + datetime.timedelta(hours=1)


          # Store the reset token and expiry time in the database
          cursor.execute(f"UPDATE USERDATA SET RESET_TOKEN = '{reset_token}', TOKEN_EXPIRY = '{expiry_time}' WHERE EMAIL = '{email}' and UPPER(USERNAME) = '{username.upper()}'")
          conn.commit()

          # Send the reset link via email
          send_reset_link(email, reset_token)

          st.success("A password reset link has been sent to your email.")
      else:
          st.error("Email address not found.")

      # Cleanup
      cursor.close()
      conn.close()

  

