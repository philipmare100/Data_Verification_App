import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

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

    # Check for the column with Bag ID, Bag Information, or Bag QR Code
    if 'BAG ID.' in df.columns:
        df['Lot ID'], df['Bag ID'] = zip(*df['BAG ID.'].apply(extract_bag_and_lot_id))
    elif 'Bag Information' in df.columns:
        df['Lot ID'], df['Bag ID'] = zip(*df['Bag Information'].apply(extract_bag_and_lot_id))
    elif 'BAG QR CODE' in df.columns:  # Added support for 'BAG QR CODE' column
        df['Lot ID'], df['Bag ID'] = zip(*df['BAG QR CODE'].apply(extract_bag_and_lot_id))
    else:
        st.error("Neither 'BAG ID.', 'Bag Information', nor 'BAG QR CODE' column found!")

    # Check for the column with Dispatch Warehouse or Receiving Warehouse
    if 'DISPATCH WAREHOUSE' in df.columns:
        df['Warehouse'] = df['DISPATCH WAREHOUSE']
    elif 'RECEIVING WAREHOUSE' in df.columns:
        df['Warehouse'] = df['RECEIVING WAREHOUSE']
    else:
        st.warning("Neither 'DISPATCH WAREHOUSE' nor 'RECEIVING WAREHOUSE' column found!")

    ### Part 1: Flagging Duplicates ###
    # Convert "Added Time" to datetime
    df['Added Time'] = pd.to_datetime(df['Added Time'], errors='coerce')
    # Flag duplicates based on Bag ID and keep only the first occurrence for the final duplicate count
    df['Duplicate Flag'] = df.duplicated(subset=['Bag ID'], keep=False)

    # Filter to include only duplicate rows for further analysis
    duplicate_df = df[df['Duplicate Flag']].copy().reset_index()  # Reset index to make row indices accessible as a column

    # Aggregate Seals and Rows for each duplicate Bag ID to show each Bag ID only once in the table
    duplicate_summary = duplicate_df.groupby('Bag ID').agg({
        'Lot ID': 'first',
        'Added Time': 'first',
        'Warehouse': 'first',
        'KICO SEAL NO.': lambda x: ', '.join(x.astype(str)),  # Collect all seals for each duplicate
        'Duplicate Flag': 'first',
        'index': lambda x: ', '.join(x.astype(str))  # Collect row indices as strings
    }).reset_index().rename(columns={'KICO SEAL NO.': 'Seals', 'index': 'Duplicate Rows'})

    # Sort the duplicate_summary by 'Added Time' in descending order
    duplicate_summary = duplicate_summary.sort_values(by='Added Time', ascending=False)

    # Count the number of unique duplicate Bag IDs
    duplicate_count = duplicate_summary['Bag ID'].nunique()

    ### Display Results for Duplicates ###
    # Display the count of duplicates
    st.subheader(f'Total Count of Duplicates: {duplicate_count}')
    st.subheader('Bag and Lot IDs with Duplicates Flagged, Seals, and Duplicate Rows')
    st.write(duplicate_summary[['Lot ID', 'Bag ID', 'Added Time', 'Warehouse', 'Duplicate Flag', 'Seals', 'Duplicate Rows']])

    ### Part 3: Filter for Rows with Missing Lot ID ###
    # Filter for rows where Lot ID is None or NaN
    missing_lot_id_df = df[df['Lot ID'].isnull()].copy()

    # Count the number of rows with missing Lot IDs
    missing_lot_id_count = missing_lot_id_df.shape[0]

    # Sort rows with missing Lot ID by the most recent Added Time
    missing_lot_id_df = missing_lot_id_df.sort_values(by='Added Time', ascending=False)

    # Display the count of rows with missing Lot IDs
    st.subheader(f'Total Count of Bags with Missing Lot ID: {missing_lot_id_count}')

    # Display the table for rows with missing Lot IDs
    st.subheader('Bag and Lot IDs Flagged with Missing Lot ID')
    st.write(missing_lot_id_df[['Lot ID', 'Bag ID', 'Added Time','KICO SEAL NO.']])

    ### Part 4: Flagging Bag IDs Longer Than 15 Characters ###
    # Filter for Bag IDs longer than 15 characters
    long_bag_ids_df = df[df['Bag ID'].apply(lambda x: len(x) > 15 if pd.notnull(x) else False)].copy()

    # Add seal and row index information for Bag IDs longer than 15 characters
    long_bag_ids_info = long_bag_ids_df.groupby('Bag ID').apply(
        lambda x: pd.Series({
            'Seals': ', '.join(x['KICO SEAL NO.'].astype(str)),
            'Long ID Rows': ', '.join(x.index.astype(str))
        })
    ).reset_index()

    # Merge the long ID information into the long_bag_ids_df DataFrame
    long_bag_ids_df = long_bag_ids_df.merge(long_bag_ids_info, on='Bag ID', how='left')

    # Sort by Added Time in descending order
    long_bag_ids_df = long_bag_ids_df.sort_values(by='Added Time', ascending=False)

    # Display the table for Bag IDs longer than 15 characters
    st.subheader('Bag and Lot IDs with IDs Longer than 15 Characters')
    st.write(long_bag_ids_df[['Lot ID', 'Bag ID', 'Added Time', 'Warehouse', 'Seals', 'Long ID Rows']])

    ### Stacked Bar Chart: Duplicates per Week Grouped by Warehouse with Date Ranges ###
    # Convert "Added Time" to datetime if it's not already
    if 'Added Time' in duplicate_df.columns:
        # Set start-of-week dates and end-of-week dates for better labeling
        duplicate_df['Week Start'] = duplicate_df['Added Time'] - pd.to_timedelta(duplicate_df['Added Time'].dt.weekday, unit='D')
        duplicate_df['Week End'] = duplicate_df['Week Start'] + pd.Timedelta(days=6)

        # Create a formatted label for each week range
        duplicate_df['Week Range'] = duplicate_df['Week Start'].dt.strftime('%Y-%m-%d') + ' - ' + duplicate_df['Week End'].dt.strftime('%Y-%m-%d')

        # Count unique duplicates per week and warehouse (no double counting)
        weekly_duplicates = duplicate_df.drop_duplicates(subset=['Bag ID', 'Week Range', 'Warehouse']).groupby(['Week Range', 'Warehouse']).size().unstack(fill_value=0)

        # Plotting the stacked bar chart
        st.subheader("Total Duplicates per Week Grouped by Warehouse (with Date Ranges)")
        plt.figure(figsize=(12, 7))
        weekly_duplicates.plot(kind='bar', stacked=True)
        plt.xlabel("Week (Date Range)")
        plt.ylabel("Total Duplicates")
        plt.title("Total Duplicates per Week Grouped by Warehouse")
        plt.legend(title="Warehouse")
        plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels for readability
        st.pyplot(plt)
