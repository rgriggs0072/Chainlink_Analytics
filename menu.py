import streamlit as st


def authenticated_menu():
    
     # Show a navigation menu for authenticated users
     st.sidebar.page_link("Chainlink_Main.py", label="Chainlink Main")
     if "user" in st.session_state['roles']:
        st.sidebar.page_link("pages/load_company_data.py", label="Load Company Data")
        st.sidebar.page_link("pages/gap_data_analysis.py", label="Gap Data Analysis")
        st.sidebar.page_link("pages/reset_data_update.py", label="Reset Data Update")
        st.sidebar.page_link("pages/distro_grid_processing.py", label="Distro Grid Processing")
        st.sidebar.page_link("pages/additional_reports.py", label="Additional Reports")
        
    
        #st.write("I am testing session state ", st.session_state['authenticated'])
     if "admin" in st.session_state['roles']:
        st.sidebar.page_link("pages/admin.py", label="Manage Users")
        st.sidebar.page_link("pages/load_company_data.py", label="Load Company Data")
        st.sidebar.page_link("pages/gap_data_analysis.py", label="Gap Data Analysis")
        st.sidebar.page_link("pages/reset_data_update.py", label="Reset Data Update")
        st.sidebar.page_link("pages/distro_grid_processing.py", label="Distro Grid Processing")
        st.sidebar.page_link("pages/additional_reports.py", label="Additional Reports")
        
        #st.write("I want to show the admin page")
        # st.sidebar.page_link(
            # "pages/super-admin.py",
            # label="Manage admin access",
            # disabled=st.session_state.role != "super-admin",
        # )


def unauthenticated_menu():
    # Show a navigation menu for unauthenticated users
    st.sidebar.page_link("Chainlink_Main.py", label="Chainlink Main")
    #st.write("i am good")

def menu():
    # Determine if a user is logged in or not, then show the correct
    # navigation menu
    
    if "authenticated" not in st.session_state or not st.session_state.get("authenticated"):
        
        unauthenticated_menu()
        return
    #st.write("I am here in the menu() function big daddy ",st.session_state.get("authenticated"))
    authenticated_menu()



    
def menu_with_redirect():
    # Redirect users to the main page if not logged in, otherwise continue to render the navigation menu
   # print(st.session_state, 'am I here in redirect?')
    if not st.session_state.get("authenticated", False):
       # print("Redirecting to Chainlink_Main.py")
        st.switch_page("Chainlink_Main.py")
        st.rerun()