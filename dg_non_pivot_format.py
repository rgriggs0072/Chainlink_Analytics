from openpyxl import workbook
import streamlit as st
import pandas as pd




# def format_non_pivot_table(workbook, stream):
#     # Convert the worksheet to a DataFrame
#     df = pd.DataFrame(workbook.active.values)

#     # Iterate over each row to check store name, store number, and UPC
#     for index, row in df.iterrows():
#         store_name = row[0]
#         store_number = row[1]
#         upc = row[2]

#         # Check if any value is missing
#         if pd.isna(store_name) or pd.isna(store_number) or pd.isna(upc):
#             st.warning(f"Please ensure there is a value for store name, store number, and UPC in row {index + 1}.")
#             return None  # Return None to indicate an issue

#     # If everything is valid, you can continue processing the workbook
#     return workbook



# import pandas as pd
# import streamlit as st

# def format_non_pivot_table(workbook, stream):
#     # Convert the worksheet to a DataFrame
#     df = pd.DataFrame(workbook.active.values)

#     # Initialize list to collect rows with missing values
#     rows_with_missing_values = []

#     # Iterate over each row to check store name, store number, and UPC
#     for index, row in df.iterrows():
#         missing_columns = []
#         for col_idx, value in enumerate(row):
#             if pd.isna(value):
#                 # Determine the column name based on the column index
#                 column_name = None  # Initialize column_name variable
#                 if col_idx == 0:
#                     column_name = "STORE NAME"
#                 elif col_idx == 1:
#                     column_name = "STORE NUMBER"
#                 elif col_idx == 2:
#                     column_name = "UPC"

#                 if column_name is not None:
#                     missing_columns.append(column_name)

#         if missing_columns:
#             missing_columns_str = ", ".join(missing_columns)
#             rows_with_missing_values.append((index + 1, missing_columns_str))

#     if rows_with_missing_values:
#         for row_index, missing_columns_str in rows_with_missing_values:
#             st.warning(f"Please ensure there is a value for {missing_columns_str} in row {row_index}.")
#         return None  # Return None to indicate an issue

#     # If everything is valid, you can continue processing the workbook
#     return workbook


import pandas as pd
import streamlit as st

def format_non_pivot_table(workbook, stream, selected_option):
    # Convert the worksheet to a DataFrame
    df = pd.DataFrame(workbook.active.values)

    # Initialize list to collect rows with missing values
    rows_with_missing_values = []

    # Iterate over each row to check for missing values in specific columns
    for index, row in df.iterrows():
        missing_columns = []
        for col_idx, value in enumerate(row):
            if pd.isna(value):
                column_name = None
                if col_idx == 0:
                    column_name = "STORE NAME"
                elif col_idx == 1:
                    column_name = "STORE NUMBER"
                elif col_idx == 2:
                    column_name = "UPC"

                if column_name:
                    missing_columns.append(column_name)

        if missing_columns:
            missing_columns_str = ", ".join(missing_columns)
            rows_with_missing_values.append(f"Row {index + 1}: {missing_columns_str}")


    # Display warnings in a modal-like section
    if rows_with_missing_values:
        with st.expander("Warning! Missing Values Detected", expanded=True):
            for warning in rows_with_missing_values:
                # Use st.error to make the warning messages red
                st.error(warning)
            
            if st.button("Acknowledge and Continue", key="acknowledge_warnings"):
                # This could reset a session state variable or perform some action to acknowledge the warnings
                st.session_state['acknowledged_warnings'] = True
                # Optionally rerun the app to refresh the state after acknowledgment
                st.experimental_rerun()

    # If everything is valid, you can continue processing the workbook
    return workbook

# Example usage within Streamlit
if 'acknowledged_warnings' not in st.session_state:
    st.session_state['acknowledged_warnings'] = False

if not st.session_state['acknowledged_warnings']:
    # Call your function here, assuming you have the 'workbook' and 'stream' variables set up
    # format_non_pivot_table(workbook, stream)
    pass  # Replace this with your actual function call
else:
    # Proceed with the rest of your Streamlit app
    st.write("Warnings acknowledged. Continuing with the app...")
