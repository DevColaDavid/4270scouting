# app/7_Data_Management.py
import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from io import StringIO
import time
from datetime import datetime

st.set_page_config(page_title="Data Management", page_icon="🔧", layout="wide")

# Password protection
ADMIN_PASSWORD = "scouting4270admin"

# Use session state to track if the user is authenticated
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Data Management - Authentication Required")
    password = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.success("Access granted! You can now manage data.")
            st.rerun()
        else:
            st.error("Incorrect password. Access denied.")
    st.stop()

# Track the active page
if 'active_page' not in st.session_state:
    st.session_state.active_page = None

# Set the active page to "Data Management" when this page is loaded
st.session_state.active_page = "Data Management"

st.title("🔧 Data Management")
st.markdown("Manage scouting data in Firebase: edit, delete, archive, unarchive, inspect errors, or upload new records via CSV.")

# Initialize Firebase
try:
    firebase_creds = {
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"],
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    }
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
except KeyError as e:
    st.error(f"Firebase credentials not found in secrets.toml: {e}")
    st.stop()
except Exception as e:
    st.error(f"Error initializing Firebase: {e}")
    st.stop()

db = firestore.client()

# Define desired column order
desired_columns = [
    'timestamp', 'team_number', 'match_number', 'alliance_color', 'starting_position', 'scouter_name',
    'match_outcome', 'auto_taxi_left', 'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
    'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
    'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
    'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
    'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
    'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed',
    'climb_status', 'defense_rating', 'speed_rating', 'driver_skill_rating', 'primary_role',
    'defense_qa', 'teleop_qa', 'auto_qa', 'comments'
]

# Define required fields for error checking
required_fields = [
    'team_number', 'match_number', 'alliance_color', 'starting_position', 'scouter_name',
    'match_outcome', 'auto_taxi_left', 'climb_status', 'defense_rating', 'speed_rating', 'driver_skill_rating', 'primary_role'
]

# Define numeric fields that should be non-negative integers
numeric_fields = [
    'team_number', 'match_number',
    'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
    'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
    'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
    'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
    'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
    'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed'
]

# Define rating fields that should be between 1 and 5
rating_fields = ['defense_rating', 'speed_rating', 'driver_skill_rating']

# Function to fetch match data (optimized polling every 30 seconds, fetching all data)
def fetch_match_data(for_selection=False, force_refresh=False):
    # Initialize match_data in session state if not present
    if 'match_data' not in st.session_state:
        st.session_state.match_data = pd.DataFrame()
    
    # Initialize last fetch time if not present
    if 'last_fetch_time' not in st.session_state:
        st.session_state.last_fetch_time = 0
    
    # Only fetch if we're on the Data Management page or if force_refresh is True
    if st.session_state.active_page != "Data Management" and not force_refresh:
        return st.session_state.match_data if not for_selection else st.session_state.match_data.copy()

    # Fetch data if 30 seconds have passed, cache is empty, or force_refresh is True
    current_time = time.time()
    if force_refresh or current_time - st.session_state.last_fetch_time >= 30 or st.session_state.match_data.empty:
        try:
            # Fetch all documents, optimize by selecting only necessary fields
            docs = db.collection('scouting_data')\
                     .select(desired_columns + ['doc_id'])\
                     .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                     .get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.match_data = pd.DataFrame(data)
            st.session_state.last_fetch_time = current_time
            st.session_state.fetch_log = f"Data fetched at {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}: {len(data)} documents"
        except Exception as e:
            st.error(f"Error fetching data from Firestore: {e}")
            st.session_state.match_data = pd.DataFrame()

    if for_selection:
        return st.session_state.match_data.copy()
    return st.session_state.match_data

# Function to fetch edit history
def fetch_edit_history():
    try:
        docs = db.collection('edit_history').order_by('edit_timestamp', direction=firestore.Query.DESCENDING).get()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['history_id'] = doc.id
            data.append(doc_data)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching edit history from Firestore: {e}")
        return pd.DataFrame()

# Function to delete edit history records from Firestore
def delete_edit_history(history_ids):
    try:
        for history_id in history_ids:
            db.collection('edit_history').document(history_id).delete()
            st.success(f"Successfully deleted edit history record {history_id}.")
    except Exception as e:
        st.error(f"Error deleting edit history records: {e}")

# Function to delete all edit history records from Firestore
def delete_all_edit_history():
    try:
        docs = db.collection('edit_history').get()
        history_ids = [doc.id for doc in docs]
        if not history_ids:
            st.info("No edit history records to delete.")
            return
        for history_id in history_ids:
            db.collection('edit_history').document(history_id).delete()
        st.success(f"Successfully deleted all {len(history_ids)} edit history records.")
    except Exception as e:
        st.error(f"Error deleting all edit history records: {e}")

# Function to fetch all archived match data from Firestore with caching
def fetch_archived_match_data(for_selection=False):
    if 'archived_match_data' not in st.session_state:
        try:
            docs = db.collection('archived_scouting_data').get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.archived_match_data = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching archived data from Firestore: {e}")
            st.session_state.archived_match_data = pd.DataFrame()
    if for_selection:
        return st.session_state.archived_match_data.copy()
    return st.session_state.archived_match_data

# Function to fetch doc IDs for the edit dropdown
def fetch_doc_ids_for_edit():
    if 'doc_ids_for_edit' not in st.session_state:
        try:
            docs = db.collection('scouting_data').select(['team_number', 'match_number']).get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            df = pd.DataFrame(data)
            if df.empty:
                # If no documents are found, return an empty result
                st.session_state.doc_ids_for_edit = {'df': pd.DataFrame(), 'labels': [], 'mapping': {}}
            else:
                labels = [f"Team {row['team_number']} - Match {row['match_number']}" for _, row in df.iterrows()]
                mapping = dict(zip(labels, df['doc_id']))
                st.session_state.doc_ids_for_edit = {'df': df, 'labels': labels, 'mapping': mapping}
        except Exception as e:
            st.error(f"Error fetching doc IDs for edit: {e}")
            st.session_state.doc_ids_for_edit = {'df': pd.DataFrame(), 'labels': [], 'mapping': {}}
    return st.session_state.doc_ids_for_edit

# Function to fetch a single record
def fetch_single_record(doc_id):
    try:
        doc = db.collection('scouting_data').document(doc_id).get()
        if doc.exists:
            record = doc.to_dict()
            record['doc_id'] = doc.id
            return pd.DataFrame([record])
        else:
            st.error(f"Record {doc_id} not found.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching record {doc_id}: {e}")
        return pd.DataFrame()

# Function to update a match record in Firestore by deleting and recreating
def update_match_data(doc_id, updated_data):
    try:
        # Step 1: Fetch the original record and save it to edit_history
        original_doc = db.collection('scouting_data').document(doc_id).get()
        if original_doc.exists:
            edit_timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
            edit_history_data = {
                'original_doc_id': doc_id,
                'original_data': original_doc.to_dict(),
                'edit_timestamp': edit_timestamp
            }
            db.collection('edit_history').document(f"edit_{doc_id}_{edit_timestamp}").set(edit_history_data)
        else:
            st.warning(f"Original record {doc_id} not found in scouting_data. Proceeding with new record creation.")

        # Step 2: Delete the existing record
        db.collection('scouting_data').document(doc_id).delete()
        
        # Step 3: Generate a new document ID
        team_number = updated_data['team_number']
        match_number = updated_data['match_number']
        timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        new_doc_id = f"team{team_number}_match{match_number}_{timestamp}"
        
        # Step 4: Create a new record with the new ID
        updated_data['timestamp'] = timestamp
        db.collection('scouting_data').document(new_doc_id).set(updated_data)
        
        # Step 5: Clear the edit dropdown cache to refresh the list
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        
        # Step 6: Clear the match data cache and force a refresh
        if 'match_data' in st.session_state:
            del st.session_state.match_data
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.success(f"Record successfully updated! Old record {doc_id} deleted, new record created with ID {new_doc_id}. Edit history recorded.")
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error updating record {doc_id}: {e}")

# Function to delete match records from Firestore
def delete_match_data(doc_ids):
    try:
        for doc_id in doc_ids:
            db.collection('scouting_data').document(doc_id).delete()
            st.success(f"Successfully deleted record {doc_id}. The table will update automatically.")
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        if 'match_data' in st.session_state:
            del st.session_state.match_data
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error deleting records: {e}")

# Function to delete all match records from Firestore
def delete_all_match_data():
    try:
        docs = db.collection('scouting_data').get()
        doc_ids = [doc.id for doc in docs]
        if not doc_ids:
            st.info("No records to delete.")
            return
        for doc_id in doc_ids:
            db.collection('scouting_data').document(doc_id).delete()
        st.success(f"Successfully deleted all {len(doc_ids)} records. The table will update automatically.")
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        if 'match_data' in st.session_state:
            st.session_state.match_data = pd.DataFrame()
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error deleting all records: {e}")

# Function to archive match records
def archive_match_data(doc_ids):
    try:
        for doc_id in doc_ids:
            doc_ref = db.collection('scouting_data').document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection('archived_scouting_data').document(doc_id).set(doc_data)
                doc_ref.delete()
                st.success(f"Successfully archived record {doc_id}. The table will update automatically.")
            else:
                st.error(f"Record {doc_id} not found.")
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        try:
            docs = db.collection('archived_scouting_data').get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.archived_match_data = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching fresh archived data: {e}")
            st.session_state.archived_match_data = pd.DataFrame()
        if 'match_data' in st.session_state:
            del st.session_state.match_data
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error archiving records: {e}")

# Function to archive all match records
def archive_all_match_data():
    try:
        docs = db.collection('scouting_data').get()
        doc_ids = [doc.id for doc in docs]
        if not doc_ids:
            st.info("No records to archive.")
            return
        for doc_id in doc_ids:
            doc_ref = db.collection('scouting_data').document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection('archived_scouting_data').document(doc_id).set(doc_data)
                doc_ref.delete()
        st.success(f"Successfully archived all {len(doc_ids)} records. The table will update automatically.")
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        try:
            docs = db.collection('archived_scouting_data').get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.archived_match_data = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching fresh archived data: {e}")
            st.session_state.archived_match_data = pd.DataFrame()
        if 'match_data' in st.session_state:
            st.session_state.match_data = pd.DataFrame()
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error archiving all records: {e}")

# Function to unarchive match records
def unarchive_match_data(doc_ids):
    try:
        for doc_id in doc_ids:
            doc_ref = db.collection('archived_scouting_data').document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection('scouting_data').document(doc_id).set(doc_data)
                doc_ref.delete()
                st.success(f"Successfully unarchived record {doc_id}. The table will update automatically.")
            else:
                st.error(f"Archived record {doc_id} not found.")
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        try:
            docs = db.collection('archived_scouting_data').get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.archived_match_data = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching fresh archived data: {e}")
            st.session_state.archived_match_data = pd.DataFrame()
        if 'match_data' in st.session_state:
            del st.session_state.match_data
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error unarchiving records: {e}")

# Function to unarchive all match records
def unarchive_all_match_data():
    try:
        docs = db.collection('archived_scouting_data').get()
        doc_ids = [doc.id for doc in docs]
        if not doc_ids:
            st.info("No archived records to unarchive.")
            return
        for doc_id in doc_ids:
            doc_ref = db.collection('archived_scouting_data').document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection('scouting_data').document(doc_id).set(doc_data)
                doc_ref.delete()
        st.success(f"Successfully unarchived all {len(doc_ids)} records. The table will update automatically.")
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        try:
            docs = db.collection('archived_scouting_data').get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.archived_match_data = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching fresh archived data: {e}")
            st.session_state.archived_match_data = pd.DataFrame()
        if 'match_data' in st.session_state:
            st.session_state.match_data = pd.DataFrame()
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error unarchiving all records: {e}")

# Function to upload a new match record to Firestore
def upload_match_data(new_data):
    try:
        doc_id = new_data.get('doc_id', None)
        if doc_id:
            db.collection('scouting_data').document(doc_id).set(new_data)
        else:
            db.collection('scouting_data').add(new_data)
        if 'doc_ids_for_edit' in st.session_state:
            del st.session_state.doc_ids_for_edit
        if 'match_data' in st.session_state:
            del st.session_state.match_data
        st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
        st.rerun()  # Trigger immediate refresh
    except Exception as e:
        st.error(f"Error uploading match data: {e}")

# Function to inspect errors in the data
def inspect_errors(data):
    if data.empty:
        return pd.DataFrame(columns=['doc_id', 'Error Type', 'Field', 'Details'])

    errors = []
    
    for field in required_fields:
        if field in data.columns:
            missing = data[field].isna() | (data[field] == "")
            for idx, is_missing in missing.items():
                if is_missing:
                    errors.append({
                        'doc_id': data.iloc[idx]['doc_id'],
                        'Error Type': 'Missing Value',
                        'Field': field,
                        'Details': 'Field is empty or NaN'
                    })

    for field in numeric_fields:
        if field in data.columns:
            non_numeric = pd.to_numeric(data[field], errors='coerce').isna() & data[field].notna()
            for idx, is_invalid in non_numeric.items():
                if is_invalid:
                    errors.append({
                        'doc_id': data.iloc[idx]['doc_id'],
                        'Error Type': 'Invalid Data Type',
                        'Field': field,
                        'Details': f'Value "{data.iloc[idx][field]}" is not a number'
                    })
            data[field] = pd.to_numeric(data[field], errors='coerce')
            negative = data[field] < 0
            for idx, is_negative in negative.items():
                if is_negative and pd.notna(data.iloc[idx][field]):
                    errors.append({
                        'doc_id': data.iloc[idx]['doc_id'],
                        'Error Type': 'Out of Range',
                        'Field': field,
                        'Details': f'Value {data.iloc[idx][field]} is negative'
                    })

    for field in rating_fields:
        if field in data.columns:
            data[field] = pd.to_numeric(data[field], errors='coerce')
            out_of_range = (data[field] < 1) | (data[field] > 5)
            for idx, is_invalid in out_of_range.items():
                if is_invalid and pd.notna(data.iloc[idx][field]):
                    errors.append({
                        'doc_id': data.iloc[idx]['doc_id'],
                        'Error Type': 'Out of Range',
                        'Field': field,
                        'Details': f'Value {data.iloc[idx][field]} is not between 1 and 5'
                    })

    if 'team_number' in data.columns and 'match_number' in data.columns:
        duplicates = data.duplicated(subset=['team_number', 'match_number'], keep=False)
        for idx, is_duplicate in duplicates.items():
            if is_duplicate:
                errors.append({
                    'doc_id': data.iloc[idx]['doc_id'],
                    'Error Type': 'Duplicate Record',
                    'Field': 'team_number, match_number',
                    'Details': f"Duplicate entry for Team {data.iloc[idx]['team_number']} in Match {data.iloc[idx]['match_number']}"
                })

    return pd.DataFrame(errors)

# Tabs for different data management actions
tabs = st.tabs(["View Data", "Edit Data", "Delete Data", "Archive Data", "Upload Data", "Unarchive Data", "Inspect Errors", "Edit History"])

# Tab 1: View Data with 30-Second Polling and Manual Refresh
with tabs[0]:
    st.subheader("View Match Data")
    st.markdown("Data refreshes every 30 seconds to ensure all scouting data is displayed. Use the button below to refresh manually.")

    # Manual refresh button
    if st.button("Refresh Now", key="manual_refresh"):
        fetch_match_data(force_refresh=True)
        st.rerun()

    # Fetch data
    with st.spinner("Loading match data..."):
        match_data = fetch_match_data()

    # Display the data
    if not match_data.empty:
        display_columns = [col for col in desired_columns if col in match_data.columns and col != 'doc_id']
        st.dataframe(match_data[display_columns], use_container_width=True)

        csv = match_data[display_columns].to_csv(index=False)
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name="match_data.csv",
            mime="text/csv",
            key="download_csv"
        )
    else:
        st.info("No match data available in the scouting_data collection.")
    
    # Display fetch log
    if 'fetch_log' in st.session_state:
        st.write(f"{st.session_state.fetch_log}")

    # Display static countdown to next refresh
    if 'last_fetch_time' in st.session_state:
        time_since_last_fetch = time.time() - st.session_state.last_fetch_time
        time_until_next_fetch = max(0, 30 - time_since_last_fetch)
        st.write(f"Next refresh in {int(time_until_next_fetch)} seconds")

    # Schedule the next refresh (only if on Data Management page)
    if st.session_state.active_page == "Data Management":
        time_since_last_fetch = time.time() - st.session_state.last_fetch_time
        if time_since_last_fetch >= 30:
            st.rerun()

# Tab 2: Edit Data
with tabs[1]:
    st.subheader("Edit Match Data")
    doc_data = fetch_doc_ids_for_edit()
    labels = doc_data['labels']
    label_to_doc_id = doc_data['mapping']
    if labels:
        selected_label = st.selectbox("Select Record to Edit", options=labels, key="edit_select")
        selected_doc_id = label_to_doc_id[selected_label]
        selected_record_df = fetch_single_record(selected_doc_id)
        if not selected_record_df.empty:
            selected_record = selected_record_df.iloc[0]
            with st.form("edit_form"):
                st.markdown("### Match Information")
                col1, col2, col3 = st.columns(3)
                with col1:
                    team_number = st.number_input(
                        "Team Number",
                        min_value=1,
                        value=int(selected_record.get('team_number', 1)),
                        step=1,
                        key=f"edit_team_number_{selected_doc_id}"
                    )
                    match_number = st.number_input(
                        "Match Number",
                        min_value=1,
                        value=int(selected_record.get('match_number', 1)),
                        step=1,
                        key=f"edit_match_number_{selected_doc_id}"
                    )
                with col2:
                    alliance_color_value = selected_record.get('alliance_color', "Red")
                    alliance_color_options = ["Red", "Blue"]
                    if alliance_color_value not in alliance_color_options:
                        alliance_color_value = "Red"
                    alliance_color = st.selectbox(
                        "Alliance Color",
                        options=alliance_color_options,
                        index=alliance_color_options.index(alliance_color_value),
                        key=f"edit_alliance_color_{selected_doc_id}"
                    )
                    starting_position_value = selected_record.get('starting_position', "Left")
                    starting_position_options = ["Left", "Center", "Right"]
                    if starting_position_value not in starting_position_options:
                        starting_position_value = "Left"
                    starting_position = st.selectbox(
                        "Starting Position",
                        options=starting_position_options,
                        index=starting_position_options.index(starting_position_value),
                        key=f"edit_starting_position_{selected_doc_id}"
                    )
                with col3:
                    scouter_name = st.text_input(
                        "Scouter Name",
                        value=str(selected_record.get('scouter_name', "")),
                        key=f"edit_scouter_name_{selected_doc_id}"
                    )

                st.markdown("### Match Outcome")
                match_outcome_value = selected_record.get('match_outcome', "Won")
                match_outcome_options = ["Won", "Lost", "Tie"]
                if match_outcome_value not in match_outcome_options:
                    match_outcome_value = "Won"
                match_outcome = st.selectbox(
                    "Match Outcome",
                    options=match_outcome_options,
                    index=match_outcome_options.index(match_outcome_value),
                    key=f"edit_match_outcome_{selected_doc_id}"
                )

                st.markdown("### Autonomous Period")
                col1, col2, col3 = st.columns([1, 2, 2])
                with col1:
                    st.markdown("**Mobility**")
                    auto_taxi_left = st.checkbox(
                        "Taxi Auto Off the Starting Line",
                        value=bool(selected_record.get('auto_taxi_left', False)),
                        key=f"edit_auto_taxi_left_{selected_doc_id}"
                    )
                with col2:
                    st.markdown("**Coral Scored**")
                    auto_coral_l1 = st.number_input(
                        "Coral Scored on L1",
                        min_value=0,
                        value=int(selected_record.get('auto_coral_l1', 0)),
                        step=1,
                        key=f"edit_auto_coral_l1_{selected_doc_id}"
                    )
                    auto_coral_l2 = st.number_input(
                        "Coral Scored on L2",
                        min_value=0,
                        value=int(selected_record.get('auto_coral_l2', 0)),
                        step=1,
                        key=f"edit_auto_coral_l2_{selected_doc_id}"
                    )
                    auto_coral_l3 = st.number_input(
                        "Coral Scored on L3",
                        min_value=0,
                        value=int(selected_record.get('auto_coral_l3', 0)),
                        step=1,
                        key=f"edit_auto_coral_l3_{selected_doc_id}"
                    )
                    auto_coral_l4 = st.number_input(
                        "Coral Scored on L4",
                        min_value=0,
                        value=int(selected_record.get('auto_coral_l4', 0)),
                        step=1,
                        key=f"edit_auto_coral_l4_{selected_doc_id}"
                    )
                with col3:
                    st.markdown("**Coral Missed**")
                    auto_missed_coral_l1 = st.number_input(
                        "Coral Missed on L1",
                        min_value=0,
                        value=int(selected_record.get('auto_missed_coral_l1', 0)),
                        step=1,
                        key=f"edit_auto_missed_coral_l1_{selected_doc_id}"
                    )
                    auto_missed_coral_l2 = st.number_input(
                        "Coral Missed on L2",
                        min_value=0,
                        value=int(selected_record.get('auto_missed_coral_l2', 0)),
                        step=1,
                        key=f"edit_auto_missed_coral_l2_{selected_doc_id}"
                    )
                    auto_missed_coral_l3 = st.number_input(
                        "Coral Missed on L3",
                        min_value=0,
                        value=int(selected_record.get('auto_missed_coral_l3', 0)),
                        step=1,
                        key=f"edit_auto_missed_coral_l3_{selected_doc_id}"
                    )
                    auto_missed_coral_l4 = st.number_input(
                        "Coral Missed on L4",
                        min_value=0,
                        value=int(selected_record.get('auto_missed_coral_l4', 0)),
                        step=1,
                        key=f"edit_auto_missed_coral_l4_{selected_doc_id}"
                    )

                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown("**Algae Scored**")
                    auto_algae_barge = st.number_input(
                        "Algae Scored on Barge",
                        min_value=0,
                        value=int(selected_record.get('auto_algae_barge', 0)),
                        step=1,
                        key=f"edit_auto_algae_barge_{selected_doc_id}"
                    )
                    auto_algae_processor = st.number_input(
                        "Algae Scored on Processor",
                        min_value=0,
                        value=int(selected_record.get('auto_algae_processor', 0)),
                        step=1,
                        key=f"edit_auto_algae_processor_{selected_doc_id}"
                    )
                with col2:
                    st.markdown("**Algae Missed**")
                    auto_missed_algae_barge = st.number_input(
                        "Algae Missed on Barge",
                        min_value=0,
                        value=int(selected_record.get('auto_missed_algae_barge', 0)),
                        step=1,
                        key=f"edit_auto_missed_algae_barge_{selected_doc_id}"
                    )
                    auto_missed_algae_processor = st.number_input(
                        "Algae Missed on Processor",
                        min_value=0,
                        value=int(selected_record.get('auto_missed_algae_processor', 0)),
                        step=1,
                        key=f"edit_auto_missed_algae_processor_{selected_doc_id}"
                    )
                with col3:
                    st.markdown("**Algae Removed**")
                    auto_algae_removed = st.number_input(
                        "Algae Removed from Reef",
                        min_value=0,
                        value=int(selected_record.get('auto_algae_removed', 0)),
                        step=1,
                        key=f"edit_auto_algae_removed_{selected_doc_id}"
                    )

                st.markdown("### Teleop Period")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Coral Scored**")
                    teleop_coral_l1 = st.number_input(
                        "Coral Scored on L1",
                        min_value=0,
                        value=int(selected_record.get('teleop_coral_l1', 0)),
                        step=1,
                        key=f"edit_teleop_coral_l1_{selected_doc_id}"
                    )
                    teleop_coral_l2 = st.number_input(
                        "Coral Scored on L2",
                        min_value=0,
                        value=int(selected_record.get('teleop_coral_l2', 0)),
                        step=1,
                        key=f"edit_teleop_coral_l2_{selected_doc_id}"
                    )
                    teleop_coral_l3 = st.number_input(
                        "Coral Scored on L3",
                        min_value=0,
                        value=int(selected_record.get('teleop_coral_l3', 0)),
                        step=1,
                        key=f"edit_teleop_coral_l3_{selected_doc_id}"
                    )
                    teleop_coral_l4 = st.number_input(
                        "Coral Scored on L4",
                        min_value=0,
                        value=int(selected_record.get('teleop_coral_l4', 0)),
                        step=1,
                        key=f"edit_teleop_coral_l4_{selected_doc_id}"
                    )
                with col2:
                    st.markdown("**Coral Missed**")
                    teleop_missed_coral_l1 = st.number_input(
                        "Coral Missed on L1",
                        min_value=0,
                        value=int(selected_record.get('teleop_missed_coral_l1', 0)),
                        step=1,
                        key=f"edit_teleop_missed_coral_l1_{selected_doc_id}"
                    )
                    teleop_missed_coral_l2 = st.number_input(
                        "Coral Missed on L2",
                        min_value=0,
                        value=int(selected_record.get('teleop_missed_coral_l2', 0)),
                        step=1,
                        key=f"edit_teleop_missed_coral_l2_{selected_doc_id}"
                    )
                    teleop_missed_coral_l3 = st.number_input(
                        "Coral Missed on L3",
                        min_value=0,
                        value=int(selected_record.get('teleop_missed_coral_l3', 0)),
                        step=1,
                        key=f"edit_teleop_missed_coral_l3_{selected_doc_id}"
                    )
                    teleop_missed_coral_l4 = st.number_input(
                        "Coral Missed on L4",
                        min_value=0,
                        value=int(selected_record.get('teleop_missed_coral_l4', 0)),
                        step=1,
                        key=f"edit_teleop_missed_coral_l4_{selected_doc_id}"
                    )

                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown("**Algae Scored**")
                    teleop_algae_barge = st.number_input(
                        "Algae Scored on Barge",
                        min_value=0,
                        value=int(selected_record.get('teleop_algae_barge', 0)),
                        step=1,
                        key=f"edit_teleop_algae_barge_{selected_doc_id}"
                    )
                    teleop_algae_processor = st.number_input(
                        "Algae Scored on Processor",
                        min_value=0,
                        value=int(selected_record.get('teleop_algae_processor', 0)),
                        step=1,
                        key=f"edit_teleop_algae_processor_{selected_doc_id}"
                    )
                with col2:
                    st.markdown("**Algae Missed**")
                    teleop_missed_algae_barge = st.number_input(
                        "Algae Missed on Barge",
                        min_value=0,
                        value=int(selected_record.get('teleop_algae_barge', 0)),
                        step=1,
                        key=f"edit_teleop_missed_algae_barge_{selected_doc_id}"
                    )
                    teleop_missed_algae_processor = st.number_input(
                        "Algae Missed on Processor",
                        min_value=0,
                        value=int(selected_record.get('teleop_algae_processor', 0)),
                        step=1,
                        key=f"edit_teleop_missed_algae_processor_{selected_doc_id}"
                    )
                with col3:
                    st.markdown("**Algae Removed**")
                    teleop_algae_removed = st.number_input(
                        "Algae Removed from Reef",
                        min_value=0,
                        value=int(selected_record.get('teleop_algae_removed', 0)),
                        step=1,
                        key=f"edit_teleop_algae_removed_{selected_doc_id}"
                    )

                st.markdown("### Endgame")
                climb_status_value = selected_record.get('climb_status', "None")
                climb_status_options = ["None", "Parked", "Shallow Climb", "Deep Climb"]
                if climb_status_value not in climb_status_options:
                    climb_status_value = "None"
                climb_status = st.selectbox(
                    "Climb Status",
                    options=climb_status_options,
                    index=climb_status_options.index(climb_status_value),
                    key=f"edit_climb_status_{selected_doc_id}"
                )

                st.markdown("### Performance Ratings")
                col1, col2, col3 = st.columns(3)
                with col1:
                    defense_rating = st.slider(
                        "Defense Rating",
                        min_value=1,
                        max_value=5,
                        value=int(selected_record.get('defense_rating', 3)),
                        step=1,
                        key=f"edit_defense_rating_{selected_doc_id}"
                    )
                with col2:
                    speed_rating = st.slider(
                        "Speed Rating",
                        min_value=1,
                        max_value=5,
                        value=int(selected_record.get('speed_rating', 3)),
                        step=1,
                        key=f"edit_speed_rating_{selected_doc_id}"
                    )
                with col3:
                    driver_skill_rating = st.slider(
                        "Driver Skill Rating",
                        min_value=1,
                        max_value=5,
                        value=int(selected_record.get('driver_skill_rating', 3)),
                        step=1,
                        key=f"edit_driver_skill_rating_{selected_doc_id}"
                    )

                st.markdown("### Strategy")
                primary_role_value = selected_record.get('primary_role', "Offense")
                primary_role_options = ["Offense", "Defense", "Both", "Neither"]
                if primary_role_value not in primary_role_options:
                    primary_role_value = "Offense"
                primary_role = st.selectbox(
                    "Primary Role",
                    options=primary_role_options,
                    index=primary_role_options.index(primary_role_value),
                    key=f"edit_primary_role_{selected_doc_id}"
                )

                st.markdown("### Qualitative Analysis")
                col1, col2 = st.columns(2)
                with col1:
                    defense_qa = st.text_area(
                        "Defense Q/A",
                        value=str(selected_record.get('defense_qa', "")),
                        help="How did they play defense, push power or speed? (if not defense put N/A)",
                        key=f"edit_defense_qa_{selected_doc_id}"
                    )
                    teleop_qa = st.text_area(
                        "Teleop Q/A",
                        value=str(selected_record.get('teleop_qa', "")),
                        help="How are they scoring (ground/station), speed, skill?",
                        key=f"edit_teleop_qa_{selected_doc_id}"
                    )
                with col2:
                    auto_qa = st.text_area(
                        "Autonomous Q/A",
                        value=str(selected_record.get('auto_qa', "")),
                        help="Speed, Path, Accuracy",
                        key=f"edit_auto_qa_{selected_doc_id}"
                    )
                    comments = st.text_area(
                        "Additional Comments",
                        value=str(selected_record.get('comments', "")),
                        key=f"edit_comments_{selected_doc_id}"
                    )

                if st.form_submit_button("Update Record"):
                    updated_data = {
                        'team_number': team_number,
                        'match_number': match_number,
                        'alliance_color': alliance_color,
                        'scouter_name': scouter_name,
                        'starting_position': starting_position,
                        'match_outcome': match_outcome,
                        'auto_taxi_left': auto_taxi_left,
                        'auto_coral_l1': auto_coral_l1,
                        'auto_coral_l2': auto_coral_l2,
                        'auto_coral_l3': auto_coral_l3,
                        'auto_coral_l4': auto_coral_l4,
                        'auto_missed_coral_l1': auto_missed_coral_l1,
                        'auto_missed_coral_l2': auto_missed_coral_l2,
                        'auto_missed_coral_l3': auto_missed_coral_l3,
                        'auto_missed_coral_l4': auto_missed_coral_l4,
                        'auto_algae_barge': auto_algae_barge,
                        'auto_algae_processor': auto_algae_processor,
                        'auto_missed_algae_barge': auto_missed_algae_barge,
                        'auto_missed_algae_processor': auto_missed_algae_processor,
                        'auto_algae_removed': auto_algae_removed,
                        'teleop_coral_l1': teleop_coral_l1,
                        'teleop_coral_l2': teleop_coral_l2,
                        'teleop_coral_l3': teleop_coral_l3,
                        'teleop_coral_l4': teleop_coral_l4,
                        'teleop_missed_coral_l1': teleop_missed_coral_l1,
                        'teleop_missed_coral_l2': teleop_missed_coral_l2,
                        'teleop_missed_coral_l3': teleop_missed_coral_l3,
                        'teleop_missed_coral_l4': teleop_missed_coral_l4,
                        'teleop_algae_barge': teleop_algae_barge,
                        'teleop_algae_processor': teleop_algae_processor,
                        'teleop_missed_algae_barge': teleop_missed_algae_barge,
                        'teleop_missed_algae_processor': teleop_missed_algae_processor,
                        'teleop_algae_removed': teleop_algae_removed,
                        'climb_status': climb_status,
                        'defense_rating': defense_rating,
                        'speed_rating': speed_rating,
                        'driver_skill_rating': driver_skill_rating,
                        'primary_role': primary_role,
                        'defense_qa': defense_qa,
                        'teleop_qa': teleop_qa,
                        'auto_qa': auto_qa,
                        'comments': comments
                    }
                    update_match_data(selected_doc_id, updated_data)
        else:
            st.info("Selected record not found.")
    else:
        st.info("No match data available to edit.")

# Tab 3: Delete Data
with tabs[2]:
    st.subheader("Delete Match Data")
    match_data = fetch_match_data(for_selection=True)
    if not match_data.empty:
        doc_ids = match_data['doc_id'].tolist()
        selected_doc_ids = st.multiselect("Select Records to Delete", options=doc_ids, key="delete_select")
        if st.button("Delete Selected Records", key="delete_button"):
            if selected_doc_ids:
                delete_match_data(selected_doc_ids)
            else:
                st.warning("Please select at least one record to delete.")
        
        st.markdown("---")
        st.markdown("### Delete All Records")
        st.warning("This action will permanently delete all records in the scouting_data collection. This cannot be undone.")
        confirm_delete_all = st.checkbox("I understand that this action cannot be undone.", key="confirm_delete_all")
        if st.button("Delete All Records", key="delete_all_button"):
            if confirm_delete_all:
                delete_all_match_data()
            else:
                st.warning("Please confirm that you understand this action cannot be undone.")
    else:
        st.info("No match data available to delete.")

# Tab 4: Archive Data
with tabs[3]:
    st.subheader("Archive Match Data")
    match_data = fetch_match_data(for_selection=True)
    if not match_data.empty:
        doc_ids = match_data['doc_id'].tolist()
        selected_doc_ids = st.multiselect("Select Records to Archive", options=doc_ids, key="archive_select")
        if st.button("Archive Selected Records", key="archive_button"):
            if selected_doc_ids:
                archive_match_data(selected_doc_ids)
            else:
                st.warning("Please select at least one record to archive.")
        
        st.markdown("---")
        st.markdown("### Archive All Records")
        st.warning("This action will move all records from scouting_data to archived_scouting_data.")
        confirm_archive_all = st.checkbox("I understand that this will archive all records.", key="confirm_archive_all")
        if st.button("Archive All Records", key="archive_all_button"):
            if confirm_archive_all:
                archive_all_match_data()
            else:
                st.warning("Please confirm that you understand this action.")
    else:
        st.info("No match data available to archive.")

# Tab 5: Upload Data
with tabs[4]:
    st.subheader("Upload New Match Data via CSV")
    st.markdown("Upload a CSV file containing match data. The CSV should include all required fields matching the scouting form structure.")
    
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded_file is not None:
        csv_data = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded data:")
        display_columns = [col for col in desired_columns if col in csv_data.columns]
        st.dataframe(csv_data[display_columns], use_container_width=True)

        if st.button("Upload CSV to Firestore"):
            batch = db.batch()
            for i, row in csv_data.iterrows():
                new_data = row.to_dict()
                for field in numeric_fields:
                    if field in new_data and pd.notna(new_data[field]):
                        new_data[field] = int(new_data[field])
                if 'auto_taxi_left' in new_data:
                    new_data['auto_taxi_left'] = bool(new_data['auto_taxi_left'])
                doc_ref = db.collection('scouting_data').document()
                batch.set(doc_ref, new_data)
            batch.commit()
            if 'doc_ids_for_edit' in st.session_state:
                del st.session_state.doc_ids_for_edit
            if 'match_data' in st.session_state:
                del st.session_state.match_data
            st.session_state.last_fetch_time = 0  # Reset the timer to force immediate fetch
            st.rerun()

# Tab 6: Unarchive Data
with tabs[5]:
    st.subheader("Unarchive Match Data")
    archived_data = fetch_archived_match_data(for_selection=True)
    if not archived_data.empty:
        doc_ids = archived_data['doc_id'].tolist()
        display_columns = [col for col in desired_columns if col in archived_data.columns and col != 'doc_id']
        st.dataframe(archived_data[display_columns], use_container_width=True)
        
        selected_doc_ids = st.multiselect("Select Records to Unarchive", options=doc_ids, key="unarchive_select")
        if st.button("Unarchive Selected Records", key="unarchive_button"):
            if selected_doc_ids:
                unarchive_match_data(selected_doc_ids)
            else:
                st.warning("Please select at least one record to unarchive.")
        
        st.markdown("---")
        st.markdown("### Unarchive All Records")
        st.warning("This action will move all records from archived_scouting_data back to scouting_data.")
        confirm_unarchive_all = st.checkbox("I understand that this will unarchive all records.", key="confirm_unarchive_all")
        if st.button("Unarchive All Records", key="unarchive_all_button"):
            if confirm_unarchive_all:
                unarchive_all_match_data()
            else:
                st.warning("Please confirm that you understand this action.")
    else:
        st.info("No archived data available to unarchive.")

# Tab 7: Inspect Errors
with tabs[6]:
    st.subheader("Inspect Errors in Match Data")
    st.markdown("This section identifies potential errors in the scouting data, such as missing values, invalid data types, out-of-range values, and duplicates.")
    match_data = fetch_match_data()
    if not match_data.empty:
        errors_df = inspect_errors(match_data)
        if not errors_df.empty:
            st.dataframe(errors_df, use_container_width=True)
            csv = errors_df.to_csv(index=False)
            st.download_button(
                label="Download Errors as CSV",
                data=csv,
                file_name="data_errors.csv",
                mime="text/csv",
                key="download_errors_csv"
            )
        else:
            st.success("No errors found in the data.")
    else:
        st.info("No match data available to inspect.")

# Tab 8: Edit History
with tabs[7]:
    st.subheader("Edit History")
    st.markdown("View and manage the history of edits made to scouting data records.")
    edit_history = fetch_edit_history()
    if not edit_history.empty:
        flattened_data = []
        for _, row in edit_history.iterrows():
            record = {
                'History ID': row['history_id'],
                'Original Document ID': row['original_doc_id'],
                'Edit Timestamp': row['edit_timestamp']
            }
            original_data = row['original_data']
            for key, value in original_data.items():
                record[key] = value
            flattened_data.append(record)
        history_df = pd.DataFrame(flattened_data)
        display_columns = ['History ID', 'Original Document ID', 'Edit Timestamp'] + [col for col in desired_columns if col in history_df.columns]
        st.dataframe(history_df[display_columns], use_container_width=True)

        csv = history_df[display_columns].to_csv(index=False)
        st.download_button(
            label="Download Edit History as CSV",
            data=csv,
            file_name="edit_history.csv",
            mime="text/csv",
            key="download_edit_history_csv"
        )

        # Delete Edit History Records
        st.markdown("---")
        st.subheader("Delete Edit History Records")
        history_ids = history_df['History ID'].tolist()
        selected_history_ids = st.multiselect("Select Edit History Records to Delete", options=history_ids, key="delete_history_select")
        if st.button("Delete Selected Edit History Records", key="delete_history_button"):
            if selected_history_ids:
                delete_edit_history(selected_history_ids)
                st.rerun()
            else:
                st.warning("Please select at least one edit history record to delete.")
        
        st.markdown("---")
        st.markdown("### Delete All Edit History Records")
        st.warning("This action will permanently delete all edit history records. This cannot be undone.")
        confirm_delete_all_history = st.checkbox("I understand that this action cannot be undone.", key="confirm_delete_all_history")
        if st.button("Delete All Edit History Records", key="delete_all_history_button"):
            if confirm_delete_all_history:
                delete_all_edit_history()
                st.rerun()
            else:
                st.warning("Please confirm that you understand this action cannot be undone.")
    else:
        st.info("No edit history available.")
        