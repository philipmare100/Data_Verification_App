import streamlit as st
import pandas as pd


# Function to extract the Bag ID and Lot ID from the string
def extract_bag_and_lot_id(bag_code):
    bag_id = None
    lot_id = None
    if isinstance(bag_code, str):
        # Extract Bag ID
        if "Bag=" in bag_code:
            bag_id = bag_code.split('Bag=')[-1].split(',')[0]
        else:
            bag_id = bag_code

        # Extract Lot ID
        if "Lot=" in bag_code:
            lot_id = bag_code.split('Lot=')[-1].split(',')[0]

    return lot_id, bag_id


# Streamlit app
st.title('Warehouse and Bag ID Flagging for Dispatch and Receiving')

# File uploader widget for the user to upload the dataset
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

if uploaded_file:
    # Load the Excel file, skipping the first row to use row 2 as headers
    df = pd.read_excel(uploaded_file, skiprows=1)

    # Display the uploaded data for reference
    st.subheader('Uploaded Data')
    st.write(df)

    # Check for the column with Bag ID or Bag Information
    if 'BAG ID.' in df.columns:
        df['Lot ID'], df['Bag ID'] = zip(*df['BAG ID.'].apply(extract_bag_and_lot_id))
    elif 'Bag Information' in df.columns:
        df['Lot ID'], df['Bag ID'] = zip(*df['Bag Information'].apply(extract_bag_and_lot_id))
    else:
        st.error("Neither 'BAG ID.' nor 'Bag Information' column found!")

    # Check for the column with Dispatch Warehouse or Receiving Warehouse
    if 'DISPATCH WAREHOUSE' in df.columns:
        df['Warehouse'] = df['DISPATCH WAREHOUSE']
    elif 'RECEIVING WAREHOUSE' in df.columns:
        df['Warehouse'] = df['RECEIVING WAREHOUSE']
    else:
        st.warning("Neither 'DISPATCH WAREHOUSE' nor 'RECEIVING WAREHOUSE' column found!")

    ### Part 1: Flagging Duplicates ###
    # Flag duplicates based on Bag ID
    df['Duplicate Flag'] = df['Bag ID'].duplicated(keep=False)

    # Identify duplicate Bag IDs and the rows in which they occur
    duplicate_rows = df[df['Bag ID'].duplicated(keep=False)].groupby('Bag ID').apply(
        lambda x: ', '.join(map(str, x.index))).reset_index(name='Duplicate Rows')

    # Merge the duplicate rows information back into the dataframe
    df = df.merge(duplicate_rows, on='Bag ID', how='left')

    # Filter the dataset to show only the duplicates
    duplicate_df = df[df['Duplicate Flag']]

    # Count the number of duplicates
    duplicate_count = duplicate_df['Bag ID'].nunique()

    ### Part 2: Flagging Bag IDs Longer Than 15 Characters ###
    # Flag Bag IDs that are longer than 15 characters
    df['Bag ID Length Flag'] = df['Bag ID'].apply(lambda x: len(x) > 15)

    # Filter the dataset to show only the Bag IDs that are longer than 15 characters
    flagged_df = df[df['Bag ID Length Flag']]

    # Count the number of flagged Bag IDs
    flagged_count = flagged_df.shape[0]

    ### Display Results ###

    # 1. Display the count of duplicates
    st.subheader(f'Total Count of Duplicates: {duplicate_count}')
    # Display the duplicates: Bag ID, Lot ID, Warehouse, Duplicate Flag, and Duplicate Rows
    st.subheader('Bag and Lot IDs with Duplicates Flagged and Duplicate Rows')
    st.write(duplicate_df[['Lot ID', 'Bag ID', 'Warehouse', 'Duplicate Flag', 'Duplicate Rows']])

    # 2. Display the count of flagged Bag IDs longer than 15 characters
    st.subheader(f'Total Count of Bag IDs Longer than 15 Characters: {flagged_count}')
    # Display the flagged Bag IDs
    st.subheader('Flagged Bag IDs (Longer than 15 Characters)')
    st.write(flagged_df[['Lot ID', 'Bag ID', 'Warehouse', 'Bag ID Length Flag']])

    ### Download Buttons ###
    # Download option for duplicates
    st.download_button("Download Duplicate Bag and Lot IDs with Rows",
                       data=duplicate_df[['Lot ID', 'Bag ID', 'Warehouse', 'Duplicate Flag', 'Duplicate Rows']].to_csv(
                           index=False),
                       file_name="duplicate_bag_lot_ids_with_rows.csv")

    # Download option for flagged Bag IDs (longer than 15 characters)
    st.download_button("Download Flagged Bag IDs",
                       data=flagged_df[['Lot ID', 'Bag ID', 'Warehouse', 'Bag ID Length Flag']].to_csv(index=False),
                       file_name="flagged_bag_ids.csv")
