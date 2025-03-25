# app/7_Data_Management.py
import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore, storage
from io import StringIO
import time
from datetime import datetime
import hashlib
from utils.utils import setup_sidebar_navigation
import requests

st.set_page_config(page_title="Data Management", page_icon="🔧", layout="wide", initial_sidebar_state="collapsed")

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in to access this page.")
    st.stop()

# Set up the sidebar navigation
setup_sidebar_navigation()

# Check user authority
allowed_authorities = ["Admin", "Owner"]
if st.session_state.get("authority") not in allowed_authorities:
    st.error("You do not have the required authority to access this page. Required: Admin or Owner.")
    st.stop()

# Track the active page
if 'active_page' not in st.session_state:
    st.session_state.active_page = None

# Set the active page to "Data Management" when this page is loaded
st.session_state.active_page = "Data Management"

st.title("🔧 Data Management")
st.info(f"Welcome, {st.session_state.username}! Manage scouting data, users, and robot photos in Firebase.")

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
        firebase_admin.initialize_app(cred, {
            'storageBucket': f"{st.secrets['firebase']['project_id']}.appspot.com"
        })
except KeyError as e:
    st.error(f"Firebase credentials not found in secrets.toml: {e}")
    st.stop()
except Exception as e:
    st.error(f"Error initializing Firebase: {e}")
    st.stop()

db = firestore.client()
bucket = storage.bucket()

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Define collection names
MATCH_SCOUT_COLLECTION = "match_scout_data"
PIT_SCOUT_COLLECTION = "pit_scout_data"
ARCHIVED_MATCH_SCOUT_COLLECTION = "archived_match_scout_data"
ARCHIVED_PIT_SCOUT_COLLECTION = "archived_pit_scout_data"
EDIT_HISTORY_COLLECTION = "edit_history"

# Define desired column order for match data
match_desired_columns = [
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

# Define desired column order for pit data
pit_desired_columns = [
    'timestamp', 'team_number', 'scouter_name', 'drivetrain_type',
    'can_score_coral_l1', 'can_score_coral_l2', 'can_score_coral_l3', 'can_score_coral_l4',
    'can_score_algae_barge', 'can_score_algae_processor', 'can_remove_algae_l1', 'can_remove_algae_l2',
    'endgame_capability', 'preferred_role', 'auto_strategy',
    'robot_strengths', 'robot_weaknesses', 'team_comments', 'scouter_notes',
    'robot_photo_url'
]

# Define required fields for error checking
match_required_fields = [
    'team_number', 'match_number', 'alliance_color', 'starting_position', 'scouter_name',
    'match_outcome', 'auto_taxi_left', 'climb_status', 'defense_rating', 'speed_rating', 'driver_skill_rating', 'primary_role'
]

pit_required_fields = [
    'team_number', 'scouter_name', 'drivetrain_type', 'endgame_capability', 'preferred_role'
]

# Define numeric fields that should be non-negative integers
match_numeric_fields = [
    'team_number', 'match_number',
    'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
    'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
    'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
    'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
    'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
    'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed'
]

pit_numeric_fields = [
    'team_number'
]

# Define rating fields that should be between 1 and 5
match_rating_fields = ['defense_rating', 'speed_rating', 'driver_skill_rating']
pit_rating_fields = []

# Function to fetch match data
def fetch_match_data(for_selection=False, force_refresh=False):
    if 'match_data' not in st.session_state:
        st.session_state.match_data = pd.DataFrame()
    
    if 'last_match_fetch_time' not in st.session_state:
        st.session_state.last_match_fetch_time = 0
    
    if st.session_state.active_page != "Data Management" and not force_refresh:
        return st.session_state.match_data if not for_selection else st.session_state.match_data.copy()

    current_time = time.time()
    if force_refresh or current_time - st.session_state.last_match_fetch_time >= 30 or st.session_state.match_data.empty:
        try:
            docs = db.collection(MATCH_SCOUT_COLLECTION)\
                     .select(match_desired_columns + ['doc_id'])\
                     .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                     .get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.match_data = pd.DataFrame(data)
            st.session_state.last_match_fetch_time = current_time
            st.session_state.match_fetch_log = f"Match data fetched at {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}: {len(data)} documents"
        except Exception as e:
            st.error(f"Error fetching match data from Firestore: {e}")
            st.session_state.match_data = pd.DataFrame()

    if for_selection:
        return st.session_state.match_data.copy()
    return st.session_state.match_data

# Function to fetch pit data
def fetch_pit_data(for_selection=False, force_refresh=False):
    if 'pit_data' not in st.session_state:
        st.session_state.pit_data = pd.DataFrame()
    
    if 'last_pit_fetch_time' not in st.session_state:
        st.session_state.last_pit_fetch_time = 0
    
    if st.session_state.active_page != "Data Management" and not force_refresh:
        return st.session_state.pit_data if not for_selection else st.session_state.pit_data.copy()

    current_time = time.time()
    if force_refresh or current_time - st.session_state.last_pit_fetch_time >= 30 or st.session_state.pit_data.empty:
        try:
            docs = db.collection(PIT_SCOUT_COLLECTION)\
                     .select(pit_desired_columns + ['doc_id'])\
                     .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                     .get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.pit_data = pd.DataFrame(data)
            st.session_state.last_pit_fetch_time = current_time
            st.session_state.pit_fetch_log = f"Pit data fetched at {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}: {len(data)} documents"
        except Exception as e:
            st.error(f"Error fetching pit data from Firestore: {e}")
            st.session_state.pit_data = pd.DataFrame()

    if for_selection:
        return st.session_state.pit_data.copy()
    return st.session_state.pit_data

# Function to fetch edit history
def fetch_edit_history(collection_type="match"):
    try:
        docs = db.collection(EDIT_HISTORY_COLLECTION)\
                 .where('collection_type', '==', collection_type)\
                 .order_by('edit_timestamp', direction=firestore.Query.DESCENDING).get()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['history_id'] = doc.id
            data.append(doc_data)
        return pd.DataFrame(data)
    except Exception as e:
        if "The query requires an index" in str(e):
            st.error(f"Error fetching edit history: Firestore requires a composite index for this query. Please create the index using the link provided in the error message: {str(e)}")
        else:
            st.error(f"Error fetching edit history from Firestore: {e}")
        return pd.DataFrame()

# Function to delete edit history records from Firestore
def delete_edit_history(history_ids):
    try:
        for history_id in history_ids:
            db.collection(EDIT_HISTORY_COLLECTION).document(history_id).delete()
            st.success(f"Successfully deleted edit history record {history_id}.")
    except Exception as e:
        st.error(f"Error deleting edit history records: {e}")

# Function to delete all edit history records from Firestore
def delete_all_edit_history(collection_type):
    try:
        docs = db.collection(EDIT_HISTORY_COLLECTION).where('collection_type', '==', collection_type).get()
        history_ids = [doc.id for doc in docs]
        if not history_ids:
            st.info(f"No edit history records to delete for {collection_type} data.")
            return
        for history_id in history_ids:
            db.collection(EDIT_HISTORY_COLLECTION).document(history_id).delete()
        st.success(f"Successfully deleted all {len(history_ids)} edit history records for {collection_type} data.")
    except Exception as e:
        st.error(f"Error deleting all edit history records: {e}")

# Function to fetch all archived match data from Firestore with caching
def fetch_archived_match_data(for_selection=False):
    if 'archived_match_data' not in st.session_state:
        try:
            docs = db.collection(ARCHIVED_MATCH_SCOUT_COLLECTION).get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.archived_match_data = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching archived match data from Firestore: {e}")
            st.session_state.archived_match_data = pd.DataFrame()
    if for_selection:
        return st.session_state.archived_match_data.copy()
    return st.session_state.archived_match_data

# Function to fetch all archived pit data from Firestore with caching
def fetch_archived_pit_data(for_selection=False):
    if 'archived_pit_data' not in st.session_state:
        try:
            docs = db.collection(ARCHIVED_PIT_SCOUT_COLLECTION).get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            st.session_state.archived_pit_data = pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching archived pit data from Firestore: {e}")
            st.session_state.archived_pit_data = pd.DataFrame()
    if for_selection:
        return st.session_state.archived_pit_data.copy()
    return st.session_state.archived_pit_data

# Function to fetch doc IDs for the edit dropdown
def fetch_doc_ids_for_edit(collection, label_fields):
    cache_key = f"doc_ids_for_edit_{collection}"
    if cache_key not in st.session_state:
        try:
            docs = db.collection(collection).select(label_fields).get()
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['doc_id'] = doc.id
                data.append(doc_data)
            df = pd.DataFrame(data)
            if df.empty:
                st.session_state[cache_key] = {'df': pd.DataFrame(), 'labels': [], 'mapping': {}}
            else:
                if collection == MATCH_SCOUT_COLLECTION:
                    labels = [f"Team {row['team_number']} - Match {row['match_number']}" for _, row in df.iterrows()]
                else:  # PIT_SCOUT_COLLECTION
                    labels = [f"Team {row['team_number']}" for _, row in df.iterrows()]
                mapping = dict(zip(labels, df['doc_id']))
                st.session_state[cache_key] = {'df': df, 'labels': labels, 'mapping': mapping}
        except Exception as e:
            st.error(f"Error fetching doc IDs for edit from {collection}: {e}")
            st.session_state[cache_key] = {'df': pd.DataFrame(), 'labels': [], 'mapping': {}}
    return st.session_state[cache_key]

# Function to fetch a single record
def fetch_single_record(collection, doc_id):
    try:
        doc = db.collection(collection).document(doc_id).get()
        if doc.exists:
            record = doc.to_dict()
            record['doc_id'] = doc.id
            return pd.DataFrame([record])
        else:
            st.error(f"Record {doc_id} not found in {collection}.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching record {doc_id} from {collection}: {e}")
        return pd.DataFrame()

# Function to update a record in Firestore by deleting and recreating
def update_data(collection, doc_id, updated_data, collection_type):
    try:
        original_doc = db.collection(collection).document(doc_id).get()
        if original_doc.exists:
            edit_timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
            edit_history_data = {
                'collection_type': collection_type,
                'original_doc_id': doc_id,
                'original_data': original_doc.to_dict(),
                'edit_timestamp': edit_timestamp
            }
            db.collection(EDIT_HISTORY_COLLECTION).document(f"edit_{doc_id}_{edit_timestamp}").set(edit_history_data)
        else:
            st.warning(f"Original record {doc_id} not found in {collection}. Proceeding with new record creation.")

        db.collection(collection).document(doc_id).delete()
        
        team_number = updated_data['team_number']
        timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        if collection == MATCH_SCOUT_COLLECTION:
            match_number = updated_data['match_number']
            new_doc_id = f"team{team_number}_match{match_number}_{timestamp}"
        else:  # PIT_SCOUT_COLLECTION
            new_doc_id = f"team{team_number}_pit_{timestamp}"
        
        updated_data['timestamp'] = timestamp
        db.collection(collection).document(new_doc_id).set(updated_data)
        
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        
        if collection == MATCH_SCOUT_COLLECTION:
            if 'match_data' in st.session_state:
                del st.session_state.match_data
            st.session_state.last_match_fetch_time = 0
        else:
            if 'pit_data' in st.session_state:
                del st.session_state.pit_data
            st.session_state.last_pit_fetch_time = 0
        st.success(f"Record successfully updated! Old record {doc_id} deleted, new record created with ID {new_doc_id}. Edit history recorded.")
        st.rerun()
    except Exception as e:
        st.error(f"Error updating record {doc_id} in {collection}: {e}")

# Function to delete records from Firestore
def delete_data(collection, doc_ids, data_type):
    try:
        for doc_id in doc_ids:
            db.collection(collection).document(doc_id).delete()
            st.success(f"Successfully deleted {data_type} record {doc_id}. The table will update automatically.")
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        if collection == MATCH_SCOUT_COLLECTION:
            if 'match_data' in st.session_state:
                del st.session_state.match_data
            st.session_state.last_match_fetch_time = 0
        else:
            if 'pit_data' in st.session_state:
                del st.session_state.pit_data
            st.session_state.last_pit_fetch_time = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error deleting {data_type} records: {e}")

# Function to delete all records from Firestore
def delete_all_data(collection, data_type):
    try:
        docs = db.collection(collection).get()
        doc_ids = [doc.id for doc in docs]
        if not doc_ids:
            st.info(f"No {data_type} records to delete.")
            return
        for doc_id in doc_ids:
            db.collection(collection).document(doc_id).delete()
        st.success(f"Successfully deleted all {len(doc_ids)} {data_type} records. The table will update automatically.")
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        if collection == MATCH_SCOUT_COLLECTION:
            if 'match_data' in st.session_state:
                st.session_state.match_data = pd.DataFrame()
            st.session_state.last_match_fetch_time = 0
        else:
            if 'pit_data' in st.session_state:
                st.session_state.pit_data = pd.DataFrame()
            st.session_state.last_pit_fetch_time = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error deleting all {data_type} records: {e}")

# Function to archive records
def archive_data(collection, archived_collection, doc_ids, data_type):
    try:
        for doc_id in doc_ids:
            doc_ref = db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection(archived_collection).document(doc_id).set(doc_data)
                doc_ref.delete()
                st.success(f"Successfully archived {data_type} record {doc_id}. The table will update automatically.")
            else:
                st.error(f"{data_type} record {doc_id} not found.")
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        if collection == MATCH_SCOUT_COLLECTION:
            try:
                docs = db.collection(ARCHIVED_MATCH_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_match_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived match data: {e}")
                st.session_state.archived_match_data = pd.DataFrame()
            if 'match_data' in st.session_state:
                del st.session_state.match_data
            st.session_state.last_match_fetch_time = 0
        else:
            try:
                docs = db.collection(ARCHIVED_PIT_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_pit_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived pit data: {e}")
                st.session_state.archived_pit_data = pd.DataFrame()
            if 'pit_data' in st.session_state:
                del st.session_state.pit_data
            st.session_state.last_pit_fetch_time = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error archiving {data_type} records: {e}")

# Function to archive all records
def archive_all_data(collection, archived_collection, data_type):
    try:
        docs = db.collection(collection).get()
        doc_ids = [doc.id for doc in docs]
        if not doc_ids:
            st.info(f"No {data_type} records to archive.")
            return
        for doc_id in doc_ids:
            doc_ref = db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection(archived_collection).document(doc_id).set(doc_data)
                doc_ref.delete()
        st.success(f"Successfully archived all {len(doc_ids)} {data_type} records. The table will update automatically.")
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        if collection == MATCH_SCOUT_COLLECTION:
            try:
                docs = db.collection(ARCHIVED_MATCH_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_match_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived match data: {e}")
                st.session_state.archived_match_data = pd.DataFrame()
            if 'match_data' in st.session_state:
                st.session_state.match_data = pd.DataFrame()
            st.session_state.last_match_fetch_time = 0
        else:
            try:
                docs = db.collection(ARCHIVED_PIT_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_pit_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived pit data: {e}")
                st.session_state.archived_pit_data = pd.DataFrame()
            if 'pit_data' in st.session_state:
                st.session_state.pit_data = pd.DataFrame()
            st.session_state.last_pit_fetch_time = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error archiving all {data_type} records: {e}")

# Function to unarchive records
def unarchive_data(collection, archived_collection, doc_ids, data_type):
    try:
        for doc_id in doc_ids:
            doc_ref = db.collection(archived_collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection(collection).document(doc_id).set(doc_data)
                doc_ref.delete()
                st.success(f"Successfully unarchived {data_type} record {doc_id}. The table will update automatically.")
            else:
                st.error(f"Archived {data_type} record {doc_id} not found.")
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        if collection == MATCH_SCOUT_COLLECTION:
            try:
                docs = db.collection(ARCHIVED_MATCH_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_match_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived match data: {e}")
                st.session_state.archived_match_data = pd.DataFrame()
            if 'match_data' in st.session_state:
                del st.session_state.match_data
            st.session_state.last_match_fetch_time = 0
        else:
            try:
                docs = db.collection(ARCHIVED_PIT_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_pit_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived pit data: {e}")
                st.session_state.archived_pit_data = pd.DataFrame()
            if 'pit_data' in st.session_state:
                del st.session_state.pit_data
            st.session_state.last_pit_fetch_time = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error unarchiving {data_type} records: {e}")

# Function to unarchive all records
def unarchive_all_data(collection, archived_collection, data_type):
    try:
        docs = db.collection(archived_collection).get()
        doc_ids = [doc.id for doc in docs]
        if not doc_ids:
            st.info(f"No archived {data_type} records to unarchive.")
            return
        for doc_id in doc_ids:
            doc_ref = db.collection(archived_collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                db.collection(collection).document(doc_id).set(doc_data)
                doc_ref.delete()
        st.success(f"Successfully unarchived all {len(doc_ids)} {data_type} records. The table will update automatically.")
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        if collection == MATCH_SCOUT_COLLECTION:
            try:
                docs = db.collection(ARCHIVED_MATCH_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_match_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived match data: {e}")
                st.session_state.archived_match_data = pd.DataFrame()
            if 'match_data' in st.session_state:
                st.session_state.match_data = pd.DataFrame()
            st.session_state.last_match_fetch_time = 0
        else:
            try:
                docs = db.collection(ARCHIVED_PIT_SCOUT_COLLECTION).get()
                data = []
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['doc_id'] = doc.id
                    data.append(doc_data)
                st.session_state.archived_pit_data = pd.DataFrame(data)
            except Exception as e:
                st.error(f"Error fetching fresh archived pit data: {e}")
                st.session_state.archived_pit_data = pd.DataFrame()
            if 'pit_data' in st.session_state:
                st.session_state.pit_data = pd.DataFrame()
            st.session_state.last_pit_fetch_time = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error unarchiving all {data_type} records: {e}")

# Function to upload a new robot photo to Firebase Storage
def upload_robot_photo(file, team_number):
    try:
        # Define the path in Firebase Storage
        blob_path = f"robot_photos/team_{team_number}.jpg"
        blob = bucket.blob(blob_path)
        
        # Upload the file
        blob.upload_from_file(file, content_type=file.type)
        
        # Make the file publicly accessible
        blob.make_public()
        
        # Get the public URL
        photo_url = blob.public_url
        return photo_url
    except Exception as e:
        st.error(f"Error uploading robot photo for team {team_number}: {e}")
        return None

# Function to delete a robot photo from Firebase Storage
def delete_robot_photo(team_number):
    try:
        blob_path = f"robot_photos/team_{team_number}.jpg"
        blob = bucket.blob(blob_path)
        if blob.exists():
            blob.delete()
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting robot photo for team {team_number}: {e}")
        return False

# Function to update the robot_photo_url in Firestore
def update_robot_photo_url(collection, doc_id, photo_url):
    try:
        # If photo_url is None, empty, or not a string, set it to None in Firestore
        if not photo_url or not isinstance(photo_url, str) or not photo_url.strip():
            photo_url = None
        db.collection(collection).document(doc_id).update({
            'robot_photo_url': photo_url
        })
        # Refresh the pit data cache
        if 'pit_data' in st.session_state:
            del st.session_state.pit_data
        st.session_state.last_pit_fetch_time = 0
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        return True
    except Exception as e:
        st.error(f"Error updating robot photo URL for document {doc_id}: {e}")
        return False

# Function to upload a new record to Firestore
def upload_data(collection, new_data):
    try:
        doc_id = new_data.get('doc_id', None)
        # Remove robot_photo_url from new_data if present (it should be managed separately)
        if 'robot_photo_url' in new_data:
            del new_data['robot_photo_url']
        if doc_id:
            db.collection(collection).document(doc_id).set(new_data)
        else:
            db.collection(collection).add(new_data)
        if f"doc_ids_for_edit_{collection}" in st.session_state:
            del st.session_state[f"doc_ids_for_edit_{collection}"]
        if collection == MATCH_SCOUT_COLLECTION:
            if 'match_data' in st.session_state:
                del st.session_state.match_data
            st.session_state.last_match_fetch_time = 0
        else:
            if 'pit_data' in st.session_state:
                del st.session_state.pit_data
            st.session_state.last_pit_fetch_time = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error uploading data to {collection}: {e}")

# Function to inspect errors in the data
def inspect_errors(data, required_fields, numeric_fields, rating_fields, duplicate_fields):
    if data.empty:
        return pd.DataFrame(columns=['doc_id', 'Error Type', 'Field', 'Details'])

    errors = []
    
    # Check for missing required fields
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

    # Check numeric fields
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

    # Check rating fields
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

    # Check for duplicates
    if duplicate_fields and all(field in data.columns for field in duplicate_fields):
        duplicates = data.duplicated(subset=duplicate_fields, keep=False)
        for idx, is_duplicate in duplicates.items():
            if is_duplicate:
                details = f"Duplicate entry for {', '.join(f'{field}: {data.iloc[idx][field]}' for field in duplicate_fields)}"
                errors.append({
                    'doc_id': data.iloc[idx]['doc_id'],
                    'Error Type': 'Duplicate Record',
                    'Field': ', '.join(duplicate_fields),
                    'Details': details
                })

    return pd.DataFrame(errors)

# User Management Functions
def fetch_users():
    try:
        docs = db.collection('users').get()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['user_id'] = doc.id
            data.append(doc_data)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching users from Firestore: {e}")
        return pd.DataFrame()

def add_user(username, password, authority):
    try:
        existing_user = db.collection('users').where('username', '==', username).limit(1).get()
        if existing_user:
            st.error(f"Username '{username}' already exists. Please choose a different username.")
            return False
        user_data = {
            "username": username,
            "password": hash_password(password),
            "authority": authority
        }
        db.collection('users').document(f"user_{username}").set(user_data)
        st.success(f"User '{username}' added successfully!")
        return True
    except Exception as e:
        st.error(f"Error adding user: {e}")
        return False

def update_user(user_id, username, password, authority):
    try:
        existing_user = db.collection('users').where('username', '==', username).get()
        for user in existing_user:
            if user.id != user_id:
                st.error(f"Username '{username}' is already taken by another user. Please choose a different username.")
                return False
        user_data = {
            "username": username,
            "authority": authority
        }
        if password:
            user_data["password"] = hash_password(password)
        db.collection('users').document(user_id).update(user_data)
        st.success(f"User '{username}' updated successfully!")
        return True
    except Exception as e:
        st.error(f"Error updating user: {e}")
        return False

def delete_users(user_ids):
    try:
        for user_id in user_ids:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists and user_doc.to_dict()['username'] == st.session_state.username:
                st.error("You cannot delete your own account while logged in.")
                continue
            db.collection('users').document(user_id).delete()
            st.success(f"Successfully deleted user with ID {user_id}.")
    except Exception as e:
        st.error(f"Error deleting users: {e}")

# Main tabs for Match Scouting and Pit Scouting
main_tabs = st.tabs(["Match Scouting Data", "Pit Scouting Data", "User Management"])

# Match Scouting Data Management
with main_tabs[0]:
    st.header("Match Scouting Data Management")
    match_tabs = st.tabs([
        "View Match Data", "Edit Match Data", "Delete Match Data", "Archive Match Data",
        "Upload Match Data", "Unarchive Match Data", "Inspect Match Errors", "Match Edit History"
    ])

    # Tab 1: View Match Data
    with match_tabs[0]:
        st.subheader("View Match Data")
        st.markdown("Data refreshes every 30 seconds to ensure all scouting data is displayed. Use the button below to refresh manually.")

        if st.button("Refresh Match Data Now", key="manual_refresh_match"):
            fetch_match_data(force_refresh=True)
            st.rerun()

        with st.spinner("Loading match data..."):
            match_data = fetch_match_data()

        if not match_data.empty:
            display_columns = [col for col in match_desired_columns if col in match_data.columns and col != 'doc_id']
            st.dataframe(match_data[display_columns], use_container_width=True)

            csv = match_data[display_columns].to_csv(index=False)
            st.download_button(
                label="Download Match Data as CSV",
                data=csv,
                file_name="match_data.csv",
                mime="text/csv",
                key="download_match_csv"
            )
        else:
            st.info(f"No match data available in the {MATCH_SCOUT_COLLECTION} collection.")
        
        if 'match_fetch_log' in st.session_state:
            st.write(f"{st.session_state.match_fetch_log}")

        if 'last_match_fetch_time' in st.session_state:
            time_since_last_fetch = time.time() - st.session_state.last_match_fetch_time
            time_until_next_fetch = max(0, 30 - time_since_last_fetch)
            st.write(f"Next refresh in {int(time_until_next_fetch)} seconds")

        if st.session_state.active_page == "Data Management":
            time_since_last_fetch = time.time() - st.session_state.last_match_fetch_time
            if time_since_last_fetch >= 30:
                st.rerun()

    # Tab 2: Edit Match Data
    with match_tabs[1]:
        st.subheader("Edit Match Data")
        doc_data = fetch_doc_ids_for_edit(MATCH_SCOUT_COLLECTION, ['team_number', 'match_number'])
        labels = doc_data['labels']
        label_to_doc_id = doc_data['mapping']
        if labels:
            selected_label = st.selectbox("Select Match Record to Edit", options=labels, key="edit_match_select")
            selected_doc_id = label_to_doc_id[selected_label]
            selected_record_df = fetch_single_record(MATCH_SCOUT_COLLECTION, selected_doc_id)
            if not selected_record_df.empty:
                selected_record = selected_record_df.iloc[0]
                with st.form("edit_match_form"):
                    st.markdown("### Match Information")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        team_number = st.number_input(
                            "Team Number",
                            min_value=1,
                            value=int(selected_record.get('team_number', 1)),
                            step=1,
                            key=f"edit_match_team_number_{selected_doc_id}"
                        )
                        match_number = st.number_input(
                            "Match Number",
                            min_value=1,
                            value=int(selected_record.get('match_number', 1)),
                            step=1,
                            key=f"edit_match_match_number_{selected_doc_id}"
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
                            key=f"edit_match_alliance_color_{selected_doc_id}"
                        )
                        starting_position_value = selected_record.get('starting_position', "Left")
                        starting_position_options = ["Left", "Center", "Right"]
                        if starting_position_value not in starting_position_options:
                            starting_position_value = "Left"
                        starting_position = st.selectbox(
                            "Starting Position",
                            options=starting_position_options,
                            index=starting_position_options.index(starting_position_value),
                            key=f"edit_match_starting_position_{selected_doc_id}"
                        )
                    with col3:
                        scouter_name = st.text_input(
                            "Scouter Name",
                            value=str(selected_record.get('scouter_name', "")),
                            key=f"edit_match_scouter_name_{selected_doc_id}"
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
                        key=f"edit_match_match_outcome_{selected_doc_id}"
                    )

                    st.markdown("### Autonomous Period")
                    col1, col2, col3 = st.columns([1, 2, 2])
                    with col1:
                        st.markdown("**Mobility**")
                        auto_taxi_left = st.checkbox(
                            "Taxi Auto Off the Starting Line",
                            value=bool(selected_record.get('auto_taxi_left', False)),
                            key=f"edit_match_auto_taxi_left_{selected_doc_id}"
                        )
                    with col2:
                        st.markdown("**Coral Scored**")
                        auto_coral_l1 = st.number_input(
                            "Coral Scored on L1",
                            min_value=0,
                            value=int(selected_record.get('auto_coral_l1', 0)),
                            step=1,
                            key=f"edit_match_auto_coral_l1_{selected_doc_id}"
                        )
                        auto_coral_l2 = st.number_input(
                            "Coral Scored on L2",
                            min_value=0,
                            value=int(selected_record.get('auto_coral_l2', 0)),
                            step=1,
                            key=f"edit_match_auto_coral_l2_{selected_doc_id}"
                        )
                        auto_coral_l3 = st.number_input(
                            "Coral Scored on L3",
                            min_value=0,
                            value=int(selected_record.get('auto_coral_l3', 0)),
                            step=1,
                            key=f"edit_match_auto_coral_l3_{selected_doc_id}"
                        )
                        auto_coral_l4 = st.number_input(
                            "Coral Scored on L4",
                            min_value=0,
                            value=int(selected_record.get('auto_coral_l4', 0)),
                            step=1,
                            key=f"edit_match_auto_coral_l4_{selected_doc_id}"
                        )
                    with col3:
                        st.markdown("**Coral Missed**")
                        auto_missed_coral_l1 = st.number_input(
                            "Coral Missed on L1",
                            min_value=0,
                            value=int(selected_record.get('auto_missed_coral_l1', 0)),
                            step=1,
                            key=f"edit_match_auto_missed_coral_l1_{selected_doc_id}"
                        )
                        auto_missed_coral_l2 = st.number_input(
                            "Coral Missed on L2",
                            min_value=0,
                            value=int(selected_record.get('auto_missed_coral_l2', 0)),
                            step=1,
                            key=f"edit_match_auto_missed_coral_l2_{selected_doc_id}"
                        )
                        auto_missed_coral_l3 = st.number_input(
                            "Coral Missed on L3",
                            min_value=0,
                            value=int(selected_record.get('auto_missed_coral_l3', 0)),
                            step=1,
                            key=f"edit_match_auto_missed_coral_l3_{selected_doc_id}"
                        )
                        auto_missed_coral_l4 = st.number_input(
                            "Coral Missed on L4",
                            min_value=0,
                            value=int(selected_record.get('auto_missed_coral_l4', 0)),
                            step=1,
                            key=f"edit_match_auto_missed_coral_l4_{selected_doc_id}"
                        )

                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown("**Algae Scored**")
                        auto_algae_barge = st.number_input(
                            "Algae Scored on Barge",
                            min_value=0,
                            value=int(selected_record.get('auto_algae_barge', 0)),
                            step=1,
                            key=f"edit_match_auto_algae_barge_{selected_doc_id}"
                        )
                        auto_algae_processor = st.number_input(
                            "Algae Scored on Processor",
                            min_value=0,
                            value=int(selected_record.get('auto_algae_processor', 0)),
                            step=1,
                            key=f"edit_match_auto_algae_processor_{selected_doc_id}"
                        )
                    with col2:
                        st.markdown("**Algae Missed**")
                        auto_missed_algae_barge = st.number_input(
                            "Algae Missed on Barge",
                            min_value=0,
                            value=int(selected_record.get('auto_missed_algae_barge', 0)),
                            step=1,
                            key=f"edit_match_auto_missed_algae_barge_{selected_doc_id}"
                        )
                        auto_missed_algae_processor = st.number_input(
                            "Algae Missed on Processor",
                            min_value=0,
                            value=int(selected_record.get('auto_missed_algae_processor', 0)),
                            step=1,
                            key=f"edit_match_auto_missed_algae_processor_{selected_doc_id}"
                        )
                    with col3:
                        st.markdown("**Algae Removed**")
                        auto_algae_removed = st.number_input(
                            "Algae Removed from Reef",
                            min_value=0,
                            value=int(selected_record.get('auto_algae_removed', 0)),
                            step=1,
                            key=f"edit_match_auto_algae_removed_{selected_doc_id}"
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
                            key=f"edit_match_teleop_coral_l1_{selected_doc_id}"
                        )
                        teleop_coral_l2 = st.number_input(
                            "Coral Scored on L2",
                            min_value=0,
                            value=int(selected_record.get('teleop_coral_l2', 0)),
                            step=1,
                            key=f"edit_match_teleop_coral_l2_{selected_doc_id}"
                        )
                        teleop_coral_l3 = st.number_input(
                            "Coral Scored on L3",
                            min_value=0,
                            value=int(selected_record.get('teleop_coral_l3', 0)),
                            step=1,
                            key=f"edit_match_teleop_coral_l3_{selected_doc_id}"
                        )
                        teleop_coral_l4 = st.number_input(
                            "Coral Scored on L4",
                            min_value=0,
                            value=int(selected_record.get('teleop_coral_l4', 0)),
                            step=1,
                            key=f"edit_match_teleop_coral_l4_{selected_doc_id}"
                        )
                    with col2:
                        st.markdown("**Coral Missed**")
                        teleop_missed_coral_l1 = st.number_input(
                            "Coral Missed on L1",
                            min_value=0,
                            value=int(selected_record.get('teleop_missed_coral_l1', 0)),
                            step=1,
                            key=f"edit_match_teleop_missed_coral_l1_{selected_doc_id}"
                        )
                        teleop_missed_coral_l2 = st.number_input(
                            "Coral Missed on L2",
                            min_value=0,
                            value=int(selected_record.get('teleop_missed_coral_l2', 0)),
                            step=1,
                            key=f"edit_match_teleop_missed_coral_l2_{selected_doc_id}"
                        )
                        teleop_missed_coral_l3 = st.number_input(
                            "Coral Missed on L3",
                            min_value=0,
                            value=int(selected_record.get('teleop_missed_coral_l3', 0)),
                            step=1,
                            key=f"edit_match_teleop_missed_coral_l3_{selected_doc_id}"
                        )
                        teleop_missed_coral_l4 = st.number_input(
                            "Coral Missed on L4",
                            min_value=0,
                            value=int(selected_record.get('teleop_missed_coral_l4', 0)),
                            step=1,
                            key=f"edit_match_teleop_missed_coral_l4_{selected_doc_id}"
                        )

                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown("**Algae Scored**")
                        teleop_algae_barge = st.number_input(
                            "Algae Scored on Barge",
                            min_value=0,
                            value=int(selected_record.get('teleop_algae_barge', 0)),
                            step=1,
                            key=f"edit_match_teleop_algae_barge_{selected_doc_id}"
                        )
                        teleop_algae_processor = st.number_input(
                            "Algae Scored on Processor",
                            min_value=0,
                            value=int(selected_record.get('teleop_algae_processor', 0)),
                            step=1,
                            key=f"edit_match_teleop_algae_processor_{selected_doc_id}"
                        )
                    with col2:
                        st.markdown("**Algae Missed**")
                        teleop_missed_algae_barge = st.number_input(
                            "Algae Missed on Barge",
                            min_value=0,
                            value=int(selected_record.get('teleop_algae_barge', 0)),
                            step=1,
                            key=f"edit_match_teleop_missed_algae_barge_{selected_doc_id}"
                        )
                        teleop_missed_algae_processor = st.number_input(
                            "Algae Missed on Processor",
                            min_value=0,
                            value=int(selected_record.get('teleop_algae_processor', 0)),
                            step=1,
                            key=f"edit_match_teleop_missed_algae_processor_{selected_doc_id}"
                        )
                    with col3:
                        st.markdown("**Algae Removed**")
                        teleop_algae_removed = st.number_input(
                            "Algae Removed from Reef",
                            min_value=0,
                            value=int(selected_record.get('teleop_algae_removed', 0)),
                            step=1,
                            key=f"edit_match_teleop_algae_removed_{selected_doc_id}"
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
                        key=f"edit_match_climb_status_{selected_doc_id}"
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
                            key=f"edit_match_defense_rating_{selected_doc_id}"
                        )
                    with col2:
                        speed_rating = st.slider(
                            "Speed Rating",
                            min_value=1,
                            max_value=5,
                            value=int(selected_record.get('speed_rating', 3)),
                            step=1,
                            key=f"edit_match_speed_rating_{selected_doc_id}"
                        )
                    with col3:
                        driver_skill_rating = st.slider(
                            "Driver Skill Rating",
                            min_value=1,
                            max_value=5,
                            value=int(selected_record.get('driver_skill_rating', 3)),
                            step=1,
                            key=f"edit_match_driver_skill_rating_{selected_doc_id}"
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
                        key=f"edit_match_primary_role_{selected_doc_id}"
                    )

                    st.markdown("### Qualitative Analysis")
                    col1, col2 = st.columns(2)
                    with col1:
                        defense_qa = st.text_area(
                            "Defense Q/A",
                            value=str(selected_record.get('defense_qa', "")),
                            help="How did they play defense, push power or speed? (if not defense put N/A)",
                            key=f"edit_match_defense_qa_{selected_doc_id}"
                        )
                        teleop_qa = st.text_area(
                            "Teleop Q/A",
                            value=str(selected_record.get('teleop_qa', "")),
                            help="How are they scoring (ground/station), speed, skill?",
                            key=f"edit_match_teleop_qa_{selected_doc_id}"
                        )
                    with col2:
                        auto_qa = st.text_area(
                            "Autonomous Q/A",
                            value=str(selected_record.get('auto_qa', "")),
                            help="Speed, Path, Accuracy",
                            key=f"edit_match_auto_qa_{selected_doc_id}"
                        )
                        comments = st.text_area(
                            "Additional Comments",
                            value=str(selected_record.get('comments', "")),
                            key=f"edit_match_comments_{selected_doc_id}"
                        )

                    if st.form_submit_button("Update Match Record"):
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
                        update_data(MATCH_SCOUT_COLLECTION, selected_doc_id, updated_data, "match")
            else:
                st.info("Selected match record not found.")
        else:
            st.info("No match data available to edit.")

    # Tab 3: Delete Match Data
    with match_tabs[2]:
        st.subheader("Delete Match Data")
        match_data = fetch_match_data(for_selection=True)
        if not match_data.empty:
            doc_ids = match_data['doc_id'].tolist()
            selected_doc_ids = st.multiselect("Select Match Records to Delete", options=doc_ids, key="delete_match_select")
            if st.button("Delete Selected Match Records", key="delete_match_button"):
                if selected_doc_ids:
                    delete_data(MATCH_SCOUT_COLLECTION, selected_doc_ids, "match")
                else:
                    st.warning("Please select at least one match record to delete.")
            
            st.markdown("---")
            st.markdown("### Delete All Match Records")
            st.warning(f"This action will permanently delete all records in the {MATCH_SCOUT_COLLECTION} collection. This cannot be undone.")
            confirm_delete_all = st.checkbox("I understand that this action cannot be undone.", key="confirm_delete_all_match")
            if st.button("Delete All Match Records", key="delete_all_match_button"):
                if confirm_delete_all:
                    delete_all_data(MATCH_SCOUT_COLLECTION, "match")
                else:
                    st.warning("Please confirm that you understand this action cannot be undone.")
        else:
            st.info("No match data available to delete.")

    # Tab 4: Archive Match Data
    with match_tabs[3]:
        st.subheader("Archive Match Data")
        match_data = fetch_match_data(for_selection=True)
        if not match_data.empty:
            doc_ids = match_data['doc_id'].tolist()
            selected_doc_ids = st.multiselect("Select Match Records to Archive", options=doc_ids, key="archive_match_select")
            if st.button("Archive Selected Match Records", key="archive_match_button"):
                if selected_doc_ids:
                    archive_data(MATCH_SCOUT_COLLECTION, ARCHIVED_MATCH_SCOUT_COLLECTION, selected_doc_ids, "match")
                else:
                    st.warning("Please select at least one match record to archive.")
            
            st.markdown("---")
            st.markdown("### Archive All Match Records")
            st.warning(f"This action will move all records from {MATCH_SCOUT_COLLECTION} to {ARCHIVED_MATCH_SCOUT_COLLECTION}.")
            confirm_archive_all = st.checkbox("I understand that this will archive all match records.", key="confirm_archive_all_match")
            if st.button("Archive All Match Records", key="archive_all_match_button"):
                if confirm_archive_all:
                    archive_all_data(MATCH_SCOUT_COLLECTION, ARCHIVED_MATCH_SCOUT_COLLECTION, "match")
                else:
                    st.warning("Please confirm that you understand this action.")
        else:
            st.info("No match data available to archive.")

    # Tab 5: Upload Match Data
    with match_tabs[4]:
        st.subheader("Upload New Match Data via CSV")
        st.markdown(f"Upload a CSV file containing match data. The CSV should include all required fields matching the scouting form structure.")
        
        uploaded_file = st.file_uploader("Upload a CSV file for Match Data", type=["csv"], key="upload_match_csv")
        if uploaded_file is not None:
            csv_data = pd.read_csv(uploaded_file)
            st.write("Preview of uploaded match data:")
            display_columns = [col for col in match_desired_columns if col in csv_data.columns]
            st.dataframe(csv_data[display_columns], use_container_width=True)

            if st.button("Upload Match CSV to Firestore", key="upload_match_button"):
                batch = db.batch()
                for i, row in csv_data.iterrows():
                    new_data = row.to_dict()
                    for field in match_numeric_fields:
                        if field in new_data and pd.notna(new_data[field]):
                            new_data[field] = int(new_data[field])
                    if 'auto_taxi_left' in new_data:
                        new_data['auto_taxi_left'] = bool(new_data['auto_taxi_left'])
                    doc_ref = db.collection(MATCH_SCOUT_COLLECTION).document()
                    batch.set(doc_ref, new_data)
                batch.commit()
                if f"doc_ids_for_edit_{MATCH_SCOUT_COLLECTION}" in st.session_state:
                    del st.session_state[f"doc_ids_for_edit_{MATCH_SCOUT_COLLECTION}"]
                if 'match_data' in st.session_state:
                    del st.session_state.match_data
                st.session_state.last_match_fetch_time = 0
                st.rerun()

    # Tab 6: Unarchive Match Data
    with match_tabs[5]:
        st.subheader("Unarchive Match Data")
        archived_data = fetch_archived_match_data(for_selection=True)
        if not archived_data.empty:
            doc_ids = archived_data['doc_id'].tolist()
            display_columns = [col for col in match_desired_columns if col in archived_data.columns and col != 'doc_id']
            st.dataframe(archived_data[display_columns], use_container_width=True)
            
            selected_doc_ids = st.multiselect("Select Match Records to Unarchive", options=doc_ids, key="unarchive_match_select")
            if st.button("Unarchive Selected Match Records", key="unarchive_match_button"):
                if selected_doc_ids:
                    unarchive_data(MATCH_SCOUT_COLLECTION, ARCHIVED_MATCH_SCOUT_COLLECTION, selected_doc_ids, "match")
                else:
                    st.warning("Please select at least one match record to unarchive.")
            
            st.markdown("---")
            st.markdown("### Unarchive All Match Records")
            st.warning(f"This action will move all records from {ARCHIVED_MATCH_SCOUT_COLLECTION} back to {MATCH_SCOUT_COLLECTION}.")
            confirm_unarchive_all = st.checkbox("I understand that this will unarchive all match records.", key="confirm_unarchive_all_match")
            if st.button("Unarchive All Match Records", key="unarchive_all_match_button"):
                if confirm_unarchive_all:
                    unarchive_all_data(MATCH_SCOUT_COLLECTION, ARCHIVED_MATCH_SCOUT_COLLECTION, "match")
                else:
                    st.warning("Please confirm that you understand this action.")
        else:
            st.info("No archived match data available to unarchive.")

    # Tab 7: Inspect Match Errors
    with match_tabs[6]:
        st.subheader("Inspect Errors in Match Data")
        st.markdown("This section identifies potential errors in the match scouting data, such as missing values, invalid data types, out-of-range values, and duplicates.")
        match_data = fetch_match_data()
        if not match_data.empty:
            errors_df = inspect_errors(
                match_data,
                match_required_fields,
                match_numeric_fields,
                match_rating_fields,
                duplicate_fields=['team_number', 'match_number']
            )
            if not errors_df.empty:
                st.dataframe(errors_df, use_container_width=True)
                csv = errors_df.to_csv(index=False)
                st.download_button(
                    label="Download Match Errors as CSV",
                    data=csv,
                    file_name="match_data_errors.csv",
                    mime="text/csv",
                    key="download_match_errors_csv"
                )
            else:
                st.success("No errors found in the match data.")
        else:
            st.info("No match data available to inspect.")

    # Tab 8: Match Edit History
    with match_tabs[7]:
        st.subheader("Match Edit History")
        st.markdown("View and manage the history of edits made to match scouting data records.")
        edit_history = fetch_edit_history(collection_type="match")
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
            display_columns = ['History ID', 'Original Document ID', 'Edit Timestamp'] + [col for col in match_desired_columns if col in history_df.columns]
            st.dataframe(history_df[display_columns], use_container_width=True)

            csv = history_df[display_columns].to_csv(index=False)
            st.download_button(
                label="Download Match Edit History as CSV",
                data=csv,
                file_name="match_edit_history.csv",
                mime="text/csv",
                key="download_match_edit_history_csv"
            )

            st.markdown("---")
            st.subheader("Delete Match Edit History Records")
            history_ids = history_df['History ID'].tolist()
            selected_history_ids = st.multiselect("Select Match Edit History Records to Delete", options=history_ids, key="delete_match_history_select")
            if st.button("Delete Selected Match Edit History Records", key="delete_match_history_button"):
                if selected_history_ids:
                    delete_edit_history(selected_history_ids)
                    st.rerun()
                else:
                    st.warning("Please select at least one match edit history record to delete.")
            
            st.markdown("---")
            st.markdown("### Delete All Match Edit History Records")
            st.warning("This action will permanently delete all match edit history records. This cannot be undone.")
            confirm_delete_all_history = st.checkbox("I understand that this action cannot be undone.", key="confirm_delete_all_match_history")
            if st.button("Delete All Match Edit History Records", key="delete_all_match_history_button"):
                if confirm_delete_all_history:
                    delete_all_edit_history("match")
                    st.rerun()
                else:
                    st.warning("Please confirm that you understand this action cannot be undone.")
        else:
            st.info("No match edit history available.")

# Pit Scouting Data Management
with main_tabs[1]:
    st.header("Pit Scouting Data Management")
    pit_tabs = st.tabs([
        "View Pit Data", "Edit Pit Data", "Delete Pit Data", "Archive Pit Data",
        "Upload Pit Data", "Unarchive Pit Data", "Inspect Pit Errors", "Pit Edit History",
        "Manage Robot Photos"
    ])

    # Tab 1: View Pit Data
    with pit_tabs[0]:
        st.subheader("View Pit Data")
        st.markdown("Data refreshes every 30 seconds to ensure all pit scouting data is displayed. Use the button below to refresh manually.")

        if st.button("Refresh Pit Data Now", key="manual_refresh_pit"):
            fetch_pit_data(force_refresh=True)
            st.rerun()

        with st.spinner("Loading pit data..."):
            pit_data = fetch_pit_data()

        if not pit_data.empty:
            display_columns = [col for col in pit_desired_columns if col in pit_data.columns and col != 'doc_id']
            st.dataframe(pit_data[display_columns], use_container_width=True)

            csv = pit_data[display_columns].to_csv(index=False)
            st.download_button(
                label="Download Pit Data as CSV",
                data=csv,
                file_name="pit_data.csv",
                mime="text/csv",
                key="download_pit_csv"
            )
        else:
            st.info(f"No pit data available in the {PIT_SCOUT_COLLECTION} collection.")
        
        if 'pit_fetch_log' in st.session_state:
            st.write(f"{st.session_state.pit_fetch_log}")

        if 'last_pit_fetch_time' in st.session_state:
            time_since_last_fetch = time.time() - st.session_state.last_pit_fetch_time
            time_until_next_fetch = max(0, 30 - time_since_last_fetch)
            st.write(f"Next refresh in {int(time_until_next_fetch)} seconds")

        if st.session_state.active_page == "Data Management":
            time_since_last_fetch = time.time() - st.session_state.last_pit_fetch_time
            if time_since_last_fetch >= 30:
                st.rerun()

    # Tab 2: Edit Pit Data
    with pit_tabs[1]:
        st.subheader("Edit Pit Data")
        doc_data = fetch_doc_ids_for_edit(PIT_SCOUT_COLLECTION, ['team_number'])
        labels = doc_data['labels']
        label_to_doc_id = doc_data['mapping']
        if labels:
            selected_label = st.selectbox("Select Pit Record to Edit", options=labels, key="edit_pit_select")
            selected_doc_id = label_to_doc_id[selected_label]
            selected_record_df = fetch_single_record(PIT_SCOUT_COLLECTION, selected_doc_id)
            if not selected_record_df.empty:
                selected_record = selected_record_df.iloc[0]
                with st.form("edit_pit_form"):
                    st.markdown("### Team Information")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        team_number = st.number_input(
                            "Team Number",
                            min_value=1,
                            value=int(selected_record.get('team_number', 1)),
                            step=1,
                            key=f"edit_pit_team_number_{selected_doc_id}"
                        )
                    with col2:
                        scouter_name = st.text_input(
                            "Scouter Name",
                            value=str(selected_record.get('scouter_name', "")),
                            key=f"edit_pit_scouter_name_{selected_doc_id}"
                        )
                    with col3:
                        pass

                    st.markdown("### Robot Specifications")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        drivetrain_type_value = selected_record.get('drivetrain_type', "Tank")
                        drivetrain_type_options = ["Tank", "Swerve", "Mecanum", "Other"]
                        if drivetrain_type_value not in drivetrain_type_options:
                            drivetrain_type_value = "Tank"
                        drivetrain_type = st.selectbox(
                            "Drivetrain Type",
                            options=drivetrain_type_options,
                            index=drivetrain_type_options.index(drivetrain_type_value),
                            key=f"edit_pit_drivetrain_type_{selected_doc_id}"
                        )
                    with col2:
                        pass
                    with col3:
                        pass

                    st.markdown("### Capabilities")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Coral Scoring**")
                        can_score_coral_l1 = st.checkbox(
                            "Can Score Coral on L1",
                            value=bool(selected_record.get('can_score_coral_l1', False)),
                            key=f"edit_pit_can_score_coral_l1_{selected_doc_id}"
                        )
                        can_score_coral_l2 = st.checkbox(
                            "Can Score Coral on L2",
                            value=bool(selected_record.get('can_score_coral_l2', False)),
                            key=f"edit_pit_can_score_coral_l2_{selected_doc_id}"
                        )
                        can_score_coral_l3 = st.checkbox(
                            "Can Score Coral on L3",
                            value=bool(selected_record.get('can_score_coral_l3', False)),
                            key=f"edit_pit_can_score_coral_l3_{selected_doc_id}"
                        )
                        can_score_coral_l4 = st.checkbox(
                            "Can Score Coral on L4",
                            value=bool(selected_record.get('can_score_coral_l4', False)),
                            key=f"edit_pit_can_score_coral_l4_{selected_doc_id}"
                        )
                    with col2:
                        st.markdown("**Algae Management**")
                        can_score_algae_barge = st.checkbox(
                            "Can Score Algae on Barge",
                            value=bool(selected_record.get('can_score_algae_barge', False)),
                            key=f"edit_pit_can_score_algae_barge_{selected_doc_id}"
                        )
                        can_score_algae_processor = st.checkbox(
                            "Can Score Algae on Processor",
                            value=bool(selected_record.get('can_score_algae_processor', False)),
                            key=f"edit_pit_can_score_algae_processor_{selected_doc_id}"
                        )
                        can_remove_algae_l1 = st.checkbox(
                            "Can Remove Algae from Level 1",
                            value=bool(selected_record.get('can_remove_algae_l1', False)),
                            key=f"edit_pit_can_remove_algae_l1_{selected_doc_id}"
                        )
                        can_remove_algae_l2 = st.checkbox(
                            "Can Remove Algae from Level 2",
                            value=bool(selected_record.get('can_remove_algae_l2', False)),
                            key=f"edit_pit_can_remove_algae_l2_{selected_doc_id}"
                        )

                    col1, col2, col3 = st.columns([1, 2, 2])
                    with col1:
                        endgame_capability_value = selected_record.get('endgame_capability', "None")
                        endgame_capability_options = ["None", "Shallow Climb", "Deep Climb", "Both Shallow and Deep Climb"]
                        if endgame_capability_value not in endgame_capability_options:
                            endgame_capability_value = "None"
                        endgame_capability = st.selectbox(
                            "Endgame Capability",
                            options=endgame_capability_options,
                            index=endgame_capability_options.index(endgame_capability_value),
                            key=f"edit_pit_endgame_capability_{selected_doc_id}"
                        )
                    with col2:
                        pass
                    with col3:
                        pass

                    st.markdown("### Strategy")
                    col1, col2 = st.columns(2)
                    with col1:
                        preferred_role_value = selected_record.get('preferred_role', "Offense")
                        preferred_role_options = ["Offense", "Defense", "Both", "Neither"]
                        if preferred_role_value not in preferred_role_options:
                            preferred_role_value = "Offense"
                        preferred_role = st.selectbox(
                            "Preferred Role",
                            options=preferred_role_options,
                            index=preferred_role_options.index(preferred_role_value),
                            key=f"edit_pit_preferred_role_{selected_doc_id}"
                        )
                    with col2:
                        auto_strategy = st.text_area(
                            "Autonomous Strategy",
                            value=str(selected_record.get('auto_strategy', "")),
                            help="Describe the team's autonomous strategy (e.g., paths, scoring priorities).",
                            key=f"edit_pit_auto_strategy_{selected_doc_id}"
                        )

                    st.markdown("### Robot Photo")
                    current_photo_url = selected_record.get('robot_photo_url', None)
                    if current_photo_url and isinstance(current_photo_url, str) and current_photo_url.strip():
                        try:
                            # Check if the URL is accessible
                            response = requests.head(current_photo_url, timeout=5)
                            if response.status_code == 200:
                                st.image(current_photo_url, caption=f"Current Robot Photo for Team {selected_record['team_number']}", width=300)
                            else:
                                st.warning(f"Cannot display current photo for Team {selected_record['team_number']}. URL is inaccessible (Status Code: {response.status_code}).")
                        except requests.exceptions.RequestException as e:
                            st.warning(f"Cannot display current photo for Team {selected_record['team_number']}. Error accessing URL: {e}")
                        except Exception as e:
                            st.warning(f"Cannot display current photo for Team {selected_record['team_number']}. Error: {e}")
                    else:
                        st.info(f"No robot photo available for Team {selected_record['team_number']}.")
                    new_robot_photo = st.file_uploader(
                        "Upload New Robot Photo (replaces existing photo if any)",
                        type=["jpg", "jpeg", "png"],
                        key=f"edit_pit_robot_photo_{selected_doc_id}"
                    )

                    st.markdown("### Notes")
                    col1, col2 = st.columns(2)
                    with col1:
                        robot_strengths = st.text_area(
                            "Robot Strengths",
                            value=str(selected_record.get('robot_strengths', "")),
                            help="What does this robot do well?",
                            key=f"edit_pit_robot_strengths_{selected_doc_id}"
                        )
                        robot_weaknesses = st.text_area(
                            "Robot Weaknesses",
                            value=str(selected_record.get('robot_weaknesses', "")),
                            help="What are the robot’s limitations or weaknesses?",
                            key=f"edit_pit_robot_weaknesses_{selected_doc_id}"
                        )
                    with col2:
                        team_comments = st.text_area(
                            "Team Comments",
                            value=str(selected_record.get('team_comments', "")),
                            help="Any comments from the team about their robot or strategy?",
                            key=f"edit_pit_team_comments_{selected_doc_id}"
                        )
                        scouter_notes = st.text_area(
                            "Scouter Notes",
                            value=str(selected_record.get('scouter_notes', "")),
                            help="Additional observations or notes from the scouter.",
                            key=f"edit_pit_scouter_notes_{selected_doc_id}"
                        )

                    if st.form_submit_button("Update Pit Record"):
                        updated_data = {
                            'team_number': team_number,
                            'scouter_name': scouter_name,
                            'drivetrain_type': drivetrain_type,
                            'can_score_coral_l1': can_score_coral_l1,
                            'can_score_coral_l2': can_score_coral_l2,
                            'can_score_coral_l3': can_score_coral_l3,
                            'can_score_coral_l4': can_score_coral_l4,
                            'can_score_algae_barge': can_score_algae_barge,
                            'can_score_algae_processor': can_score_algae_processor,
                            'can_remove_algae_l1': can_remove_algae_l1,
                            'can_remove_algae_l2': can_remove_algae_l2,
                            'endgame_capability': endgame_capability,
                            'preferred_role': preferred_role,
                            'auto_strategy': auto_strategy,
                            'robot_strengths': robot_strengths,
                            'robot_weaknesses': robot_weaknesses,
                            'team_comments': team_comments,
                            'scouter_notes': scouter_notes
                        }
                        # Handle photo upload if a new photo is provided
                        if new_robot_photo:
                            photo_url = upload_robot_photo(new_robot_photo, team_number)
                            if photo_url:
                                updated_data['robot_photo_url'] = photo_url
                                st.success(f"Robot photo updated successfully for team {team_number}!")
                            else:
                                st.warning("Photo upload failed. The record will be updated without a new photo.")
                        update_data(PIT_SCOUT_COLLECTION, selected_doc_id, updated_data, "pit")
            else:
                st.info("Selected pit record not found.")
        else:
            st.info("No pit data available to edit.")

        # Tab 3: Delete Pit Data
        with pit_tabs[2]:
            st.subheader("Delete Pit Data")
            pit_data = fetch_pit_data(for_selection=True)
            if not pit_data.empty:
                doc_ids = pit_data['doc_id'].tolist()
                selected_doc_ids = st.multiselect("Select Pit Records to Delete", options=doc_ids, key="delete_pit_select")
                if st.button("Delete Selected Pit Records", key="delete_pit_button"):
                    if selected_doc_ids:
                        # Track whether all deletions were successful
                        all_photos_deleted = True
                        # Delete associated robot photos
                        for doc_id in selected_doc_ids:
                            row = pit_data[pit_data['doc_id'] == doc_id].iloc[0]
                            team_number = row['team_number']
                            # Check if the record has a robot photo
                            photo_url = row.get('robot_photo_url', None)
                            if photo_url:
                                if delete_robot_photo(team_number):
                                    st.success(f"Successfully deleted robot photo for Team {team_number}.")
                                else:
                                    st.error(f"Failed to delete robot photo for Team {team_number}.")
                                    all_photos_deleted = False
                            else:
                                st.info(f"No robot photo to delete for Team {team_number}.")
                        
                        # Proceed with record deletion only if photo deletion was successful (or if there were no photos)
                        if all_photos_deleted:
                            delete_data(PIT_SCOUT_COLLECTION, selected_doc_ids, "pit")
                        else:
                            st.warning("Some robot photos could not be deleted. Pit records were not deleted to prevent data inconsistency.")
                    else:
                        st.warning("Please select at least one pit record to delete.")
                
                st.markdown("---")
                st.markdown("### Delete All Pit Records")
                st.warning(f"This action will permanently delete all records in the {PIT_SCOUT_COLLECTION} collection, including associated robot photos. This cannot be undone.")
                confirm_delete_all = st.checkbox("I understand that this action cannot be undone.", key="confirm_delete_all_pit")
                if st.button("Delete All Pit Records", key="delete_all_pit_button"):
                    if confirm_delete_all:
                        # Track whether all deletions were successful
                        all_photos_deleted = True
                        # Delete all robot photos
                        for _, row in pit_data.iterrows():
                            team_number = row['team_number']
                            photo_url = row.get('robot_photo_url', None)
                            if photo_url:
                                if delete_robot_photo(team_number):
                                    st.success(f"Successfully deleted robot photo for Team {team_number}.")
                                else:
                                    st.error(f"Failed to delete robot photo for Team {team_number}.")
                                    all_photos_deleted = False
                            else:
                                st.info(f"No robot photo to delete for Team {team_number}.")
                        
                        # Proceed with record deletion only if photo deletion was successful
                        if all_photos_deleted:
                            delete_all_data(PIT_SCOUT_COLLECTION, "pit")
                        else:
                            st.warning("Some robot photos could not be deleted. Pit records were not deleted to prevent data inconsistency.")
                    else:
                        st.warning("Please confirm that you understand this action cannot be undone.")
            else:
                st.info("No pit data available to delete.")

        # Tab 4: Archive Pit Data
        with pit_tabs[3]:
            st.subheader("Archive Pit Data")
            pit_data = fetch_pit_data(for_selection=True)
            if not pit_data.empty:
                doc_ids = pit_data['doc_id'].tolist()
                selected_doc_ids = st.multiselect("Select Pit Records to Archive", options=doc_ids, key="archive_pit_select")
                if st.button("Archive Selected Pit Records", key="archive_pit_button"):
                    if selected_doc_ids:
                        archive_data(PIT_SCOUT_COLLECTION, ARCHIVED_PIT_SCOUT_COLLECTION, selected_doc_ids, "pit")
                    else:
                        st.warning("Please select at least one pit record to archive.")
                
                st.markdown("---")
                st.markdown("### Archive All Pit Records")
                st.warning(f"This action will move all records from {PIT_SCOUT_COLLECTION} to {ARCHIVED_PIT_SCOUT_COLLECTION}.")
                confirm_archive_all = st.checkbox("I understand that this will archive all pit records.", key="confirm_archive_all_pit")
                if st.button("Archive All Pit Records", key="archive_all_pit_button"):
                    if confirm_archive_all:
                        archive_all_data(PIT_SCOUT_COLLECTION, ARCHIVED_PIT_SCOUT_COLLECTION, "pit")
                    else:
                        st.warning("Please confirm that you understand this action.")
            else:
                st.info("No pit data available to archive.")

        # Tab 5: Upload Pit Data
        with pit_tabs[4]:
            st.subheader("Upload New Pit Data via CSV")
            st.markdown(f"Upload a CSV file containing pit data. The CSV should include all required fields matching the pit scouting form structure. Note: Robot photos must be uploaded separately.")
            
            uploaded_file = st.file_uploader("Upload a CSV file for Pit Data", type=["csv"], key="upload_pit_csv")
            if uploaded_file is not None:
                csv_data = pd.read_csv(uploaded_file)
                st.write("Preview of uploaded pit data:")
                display_columns = [col for col in pit_desired_columns if col in csv_data.columns]
                st.dataframe(csv_data[display_columns], use_container_width=True)

                if st.button("Upload Pit CSV to Firestore", key="upload_pit_button"):
                    batch = db.batch()
                    for i, row in csv_data.iterrows():
                        new_data = row.to_dict()
                        for field in pit_numeric_fields:
                            if field in new_data and pd.notna(new_data[field]):
                                new_data[field] = int(new_data[field])
                        for field in ['can_score_coral_l1', 'can_score_coral_l2', 'can_score_coral_l3', 'can_score_coral_l4',
                                    'can_score_algae_barge', 'can_score_algae_processor', 'can_remove_algae_l1', 'can_remove_algae_l2']:
                            if field in new_data:
                                new_data[field] = bool(new_data[field])
                        doc_ref = db.collection(PIT_SCOUT_COLLECTION).document()
                        batch.set(doc_ref, new_data)
                    batch.commit()
                    if f"doc_ids_for_edit_{PIT_SCOUT_COLLECTION}" in st.session_state:
                        del st.session_state[f"doc_ids_for_edit_{PIT_SCOUT_COLLECTION}"]
                    if 'pit_data' in st.session_state:
                        del st.session_state.pit_data
                    st.session_state.last_pit_fetch_time = 0
                    st.rerun()

        # Tab 6: Unarchive Pit Data
        with pit_tabs[5]:
            st.subheader("Unarchive Pit Data")
            archived_data = fetch_archived_pit_data(for_selection=True)
            if not archived_data.empty:
                doc_ids = archived_data['doc_id'].tolist()
                display_columns = [col for col in pit_desired_columns if col in archived_data.columns and col != 'doc_id']
                st.dataframe(archived_data[display_columns], use_container_width=True)
                
                selected_doc_ids = st.multiselect("Select Pit Records to Unarchive", options=doc_ids, key="unarchive_pit_select")
                if st.button("Unarchive Selected Pit Records", key="unarchive_pit_button"):
                    if selected_doc_ids:
                        unarchive_data(PIT_SCOUT_COLLECTION, ARCHIVED_PIT_SCOUT_COLLECTION, selected_doc_ids, "pit")
                    else:
                        st.warning("Please select at least one pit record to unarchive.")
                
                st.markdown("---")
                st.markdown("### Unarchive All Pit Records")
                st.warning(f"This action will move all records from {ARCHIVED_PIT_SCOUT_COLLECTION} back to {PIT_SCOUT_COLLECTION}.")
                confirm_unarchive_all = st.checkbox("I understand that this will unarchive all pit records.", key="confirm_unarchive_all_pit")
                if st.button("Unarchive All Pit Records", key="unarchive_all_pit_button"):
                    if confirm_unarchive_all:
                        unarchive_all_data(PIT_SCOUT_COLLECTION, ARCHIVED_PIT_SCOUT_COLLECTION, "pit")
                    else:
                        st.warning("Please confirm that you understand this action.")
            else:
                st.info("No archived pit data available to unarchive.")

        # Tab 7: Inspect Pit Errors
        with pit_tabs[6]:
            st.subheader("Inspect Errors in Pit Data")
            st.markdown("This section identifies potential errors in the pit scouting data, such as missing values, invalid data types, out-of-range values, and duplicates.")
            pit_data = fetch_pit_data()
            if not pit_data.empty:
                errors_df = inspect_errors(
                    pit_data,
                    pit_required_fields,
                    pit_numeric_fields,
                    pit_rating_fields,
                    duplicate_fields=['team_number']
                )
                if not errors_df.empty:
                    st.dataframe(errors_df, use_container_width=True)
                    csv = errors_df.to_csv(index=False)
                    st.download_button(
                        label="Download Pit Errors as CSV",
                        data=csv,
                        file_name="pit_data_errors.csv",
                        mime="text/csv",
                        key="download_pit_errors_csv"
                    )
                else:
                    st.success("No errors found in the pit data.")
            else:
                st.info("No pit data available to inspect.")

        # Tab 8: Pit Edit History
        with pit_tabs[7]:
            st.subheader("Pit Edit History")
            st.markdown("View and manage the history of edits made to pit scouting data records.")
            edit_history = fetch_edit_history(collection_type="pit")
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
                display_columns = ['History ID', 'Original Document ID', 'Edit Timestamp'] + [col for col in pit_desired_columns if col in history_df.columns]
                st.dataframe(history_df[display_columns], use_container_width=True)

                csv = history_df[display_columns].to_csv(index=False)
                st.download_button(
                    label="Download Pit Edit History as CSV",
                    data=csv,
                    file_name="pit_edit_history.csv",
                    mime="text/csv",
                    key="download_pit_edit_history_csv"
                )

                st.markdown("---")
                st.subheader("Delete Pit Edit History Records")
                history_ids = history_df['History ID'].tolist()
                selected_history_ids = st.multiselect("Select Pit Edit History Records to Delete", options=history_ids, key="delete_pit_history_select")
                if st.button("Delete Selected Pit Edit History Records", key="delete_pit_history_button"):
                    if selected_history_ids:
                        delete_edit_history(selected_history_ids)
                        st.rerun()
                    else:
                        st.warning("Please select at least one pit edit history record to delete.")
                
                st.markdown("---")
                st.markdown("### Delete All Pit Edit History Records")
                st.warning("This action will permanently delete all pit edit history records. This cannot be undone.")
                confirm_delete_all_history = st.checkbox("I understand that this action cannot be undone.", key="confirm_delete_all_pit_history")
                if st.button("Delete All Pit Edit History Records", key="delete_all_pit_history_button"):
                    if confirm_delete_all_history:
                        delete_all_edit_history("pit")
                        st.rerun()
                    else:
                        st.warning("Please confirm that you understand this action cannot be undone.")
            else:
                st.info("No pit edit history available.")

        # Tab 9: Manage Robot Photos
        with pit_tabs[8]:
            st.subheader("Manage Robot Photos")
            st.markdown("View, update, or delete robot photos for each team. Photos are stored in Firebase Storage, and their URLs are linked in the pit scouting data.")

            # Fetch pit data to get team numbers and photo URLs
            pit_data = fetch_pit_data()
            if not pit_data.empty:
                # Create a DataFrame with team numbers, doc_ids, and photo URLs
                photo_data = pit_data[['team_number', 'doc_id', 'robot_photo_url']].copy()
                photo_data = photo_data.sort_values('team_number')

                # Display the data with photo previews
                st.markdown("### Robot Photos Overview")
                for idx, row in photo_data.iterrows():
                    team_number = row['team_number']
                    doc_id = row['doc_id']
                    photo_url = row.get('robot_photo_url', None)

                    st.markdown(f"#### Team {team_number}")
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if photo_url and isinstance(photo_url, str) and photo_url.strip():
                            try:
                                # Check if the URL is accessible
                                response = requests.head(photo_url, timeout=5)
                                if response.status_code == 200:
                                    st.image(photo_url, caption=f"Robot Photo for Team {team_number}", width=200)
                                else:
                                    st.warning(f"Cannot display photo for Team {team_number}. URL is inaccessible (Status Code: {response.status_code}).")
                            except requests.exceptions.RequestException as e:
                                st.warning(f"Cannot display photo for Team {team_number}. Error accessing URL: {e}")
                            except Exception as e:
                                st.warning(f"Cannot display photo for Team {team_number}. Error: {e}")
                        else:
                            st.info(f"No photo available for Team {team_number}.")
                    with col2:
                        # Option to upload a new photo
                        new_photo = st.file_uploader(
                            f"Upload New Photo for Team {team_number}",
                            type=["jpg", "jpeg", "png"],
                            key=f"upload_photo_team_{team_number}"
                        )
                        if st.button(f"Update Photo for Team {team_number}", key=f"update_photo_team_{team_number}"):
                            if new_photo:
                                # Delete the existing photo if it exists
                                if photo_url and isinstance(photo_url, str) and photo_url.strip():
                                    delete_robot_photo(team_number)
                                # Upload the new photo
                                new_photo_url = upload_robot_photo(new_photo, team_number)
                                if new_photo_url:
                                    # Update the Firestore record
                                    if update_robot_photo_url(PIT_SCOUT_COLLECTION, doc_id, new_photo_url):
                                        st.success(f"Successfully updated robot photo for Team {team_number}!")
                                        st.rerun()
                                else:
                                    st.error("Failed to upload the new photo.")
                            else:
                                st.warning("Please upload a photo to update.")

                        # Option to delete the photo
                        if photo_url and isinstance(photo_url, str) and photo_url.strip():
                            if st.button(f"Delete Photo for Team {team_number}", key=f"delete_photo_team_{team_number}"):
                                # Delete from Firebase Storage
                                if delete_robot_photo(team_number):
                                    # Update Firestore to remove the photo URL
                                    if update_robot_photo_url(PIT_SCOUT_COLLECTION, doc_id, None):
                                        st.success(f"Successfully deleted robot photo for Team {team_number}!")
                                        st.rerun()
                                    else:
                                        st.error("Photo deleted from storage, but failed to update the record.")
                                else:
                                    st.error("Failed to delete the photo from storage.")
            else:
                st.info("No pit data available to manage robot photos.")

    # User Management
    with main_tabs[2]:
        st.header("User Management")
        user_tabs = st.tabs(["View Users", "Add User", "Edit User", "Delete Users"])

        # Tab 1: View Users
        with user_tabs[0]:
            st.subheader("View Users")
            users_df = fetch_users()
            if not users_df.empty:
                display_columns = ['username', 'authority', 'user_id']
                st.dataframe(users_df[display_columns], use_container_width=True)
            else:
                st.info("No users found in the database.")

        # Tab 2: Add User
        with user_tabs[1]:
            st.subheader("Add New User")
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_authority = st.selectbox("Authority", options=["Scouter", "Admin", "Owner"])
                if st.form_submit_button("Add User"):
                    if new_username and new_password:
                        add_user(new_username, new_password, new_authority)
                    else:
                        st.warning("Please provide both a username and password.")

        # Tab 3: Edit User
        with user_tabs[2]:
            st.subheader("Edit User")
            users_df = fetch_users()
            if not users_df.empty:
                user_ids = users_df['user_id'].tolist()
                selected_user_id = st.selectbox("Select User to Edit", options=user_ids, format_func=lambda x: users_df[users_df['user_id'] == x]['username'].iloc[0], key="edit_user_select")
                selected_user = users_df[users_df['user_id'] == selected_user_id].iloc[0]
                with st.form("edit_user_form"):
                    edit_username = st.text_input("Username", value=selected_user['username'], key="edit_user_username")
                    edit_password = st.text_input("New Password (leave blank to keep unchanged)", type="password", key="edit_user_password")
                    edit_authority = st.selectbox("Authority", options=["Scouter", "Admin", "Owner"], index=["Scouter", "Admin", "Owner"].index(selected_user['authority']), key="edit_user_authority")
                    if st.form_submit_button("Update User"):
                        if edit_username:
                            update_user(selected_user_id, edit_username, edit_password, edit_authority)
                        else:
                            st.warning("Username cannot be empty.")
            else:
                st.info("No users available to edit.")

        # Tab 4: Delete Users
        with user_tabs[3]:
            st.subheader("Delete Users")
            users_df = fetch_users()
            if not users_df.empty:
                user_ids = users_df['user_id'].tolist()
                selected_user_ids = st.multiselect("Select Users to Delete", options=user_ids, format_func=lambda x: users_df[users_df['user_id'] == x]['username'].iloc[0], key="delete_user_select")
                if st.button("Delete Selected Users", key="delete_user_button"):
                    if selected_user_ids:
                        delete_users(selected_user_ids)
                    else:
                        st.warning("Please select at least one user to delete.")
            else:
                st.info("No users available to delete.")