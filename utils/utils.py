# utils/utils.py
import os
import sys
import pandas as pd
from datetime import datetime
import streamlit as st
from google.cloud import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter
from google.oauth2 import service_account
import firebase_admin
from firebase_admin import credentials, firestore, storage
import hashlib

# Define page-to-file mapping and authority-based access
PAGE_CONFIG = {
    "Main": {
        "file": "main.py",
        "authorities": ["Owner", "Admin", "Scouter", "Viewer"]
    },
    "Scouting Form": {
        "file": "pages/1_Scouting_Form.py",
        "authorities": ["Owner", "Admin", "Scouter"]
    },
    "Data Analysis": {
        "file": "pages/2_Data_Analysis.py",
        "authorities": ["Owner", "Admin", "Scouter", "Viewer"]
    },
    "Team Statistics": {
        "file": "pages/3_Team_Statistics.py",
        "authorities": ["Owner", "Admin", "Scouter", "Viewer"]
    },
    "Match Prediction": {
        "file": "pages/4_Match_Prediction.py",
        "authorities": ["Owner", "Admin", "Scouter", "Viewer"]
    },
    "TBA Integration": {
        "file": "pages/5_TBA_Integration.py",
        "authorities": ["Owner", "Admin", "Scouter", "Viewer"]
    },
    "Match Schedule": {
        "file": "pages/6_Match_Schedule.py",
        "authorities": ["Owner", "Admin"]
    },
    "Data Management": {
        "file": "pages/7_Data_Management.py",
        "authorities": ["Owner", "Admin"]
    }
}

def setup_sidebar_navigation():
    """Set up the sidebar navigation for all pages."""
    # Hide Streamlit's default menu, footer, and default sidebar navigation
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Hide the default Streamlit sidebar navigation */
    div[data-testid="stSidebarNav"] {display: none;}
    /* Ensure non-selected pages are not bold */
    div[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] span {
        font-weight: normal !important;
    }
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    with st.sidebar:
        # Only show navigation if the user is logged in
        if "logged_in" in st.session_state and st.session_state.logged_in:
            st.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.authority})")
            if st.button("Logout"):
                # Clear session state
                st.session_state.logged_in = False
                st.session_state.username = None
                st.session_state.authority = None
                st.session_state.active_page = "Main"
                st.session_state.firebase_initialized = False  # Reset Firebase initialization
                st.session_state.firebase_db = None
                st.session_state.firebase_bucket = None
                st.success("Logged out successfully")
                # Redirect to the Main page
                st.switch_page("main.py")

            # Filter pages based on the user's authority
            accessible_pages = [
                page for page, config in PAGE_CONFIG.items()
                if st.session_state.authority in config["authorities"]
            ]

            # Create a list of clickable links for navigation
            if accessible_pages:
                for page in accessible_pages:
                    page_file = PAGE_CONFIG[page]["file"]
                    st.page_link(page_file, label=page)
            else:
                st.warning("You do not have access to any pages.")
                st.session_state.active_page = "Main"
        else:
            # If not logged in, show nothing in the sidebar
            st.write("")

# Global variables for Firestore collections
MATCH_SCOUT_COLLECTION = "match_scout_data"
PIT_SCOUT_COLLECTION = "pit_scout_data"

def get_firebase_instances():
    # Initialize session state keys if they don't exist
    if "firebase_initialized" not in st.session_state:
        st.session_state.firebase_initialized = False
    if "firebase_db" not in st.session_state:
        st.session_state.firebase_db = None
    if "firebase_bucket" not in st.session_state:
        st.session_state.firebase_bucket = None

    # Only initialize if not already initialized
    if not st.session_state.firebase_initialized:
        try:
            # Remove any existing Firebase apps to start fresh
            if firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app())
                st.session_state.firebase_initialized = False
                st.session_state.firebase_db = None
                st.session_state.firebase_bucket = None

            # Determine the bucket name dynamically
            if "firebase" in st.secrets:
                # Running on Streamlit Cloud
                firebase_config = st.secrets["firebase"]
                cred = credentials.Certificate({
                    "type": firebase_config["type"],
                    "project_id": firebase_config["project_id"],
                    "private_key_id": firebase_config["private_key_id"],
                    "private_key": firebase_config["private_key"].replace("\\n", "\n"),
                    "client_email": firebase_config["client_email"],
                    "client_id": firebase_config["client_id"],
                    "auth_uri": firebase_config["auth_uri"],
                    "token_uri": firebase_config["token_uri"],
                    "auth_provider_x509_cert_url": firebase_config["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": firebase_config["client_x509_cert_url"],
                    "universe_domain": "googleapis.com"
                })
                # Use the project_id to construct the default bucket name
                project_id = firebase_config["project_id"]
                default_bucket = f"{project_id}.firebasestorage.app"  # Correct bucket name
                app_options = {
                    "storageBucket": firebase_config.get("storageBucket", default_bucket)
                }
            else:
                # Running locally
                cred = credentials.Certificate("firestore-key.json")
                project_id = "scouting4270"  # Your confirmed project ID
                default_bucket = f"{project_id}.firebasestorage.app"  # Correct bucket name
                app_options = {
                    "storageBucket": default_bucket
                }
            
            # Initialize the Firebase app
            app = firebase_admin.initialize_app(cred, app_options)
            
            # Initialize Firestore and Storage
            db = firestore.client(app=app)
            bucket = storage.bucket(app_options["storageBucket"], app=app)
            
            # Verify bucket access
            try:
                bucket.list_blobs(max_results=1)
            except Exception as e:
                st.error(f"Failed to access the bucket during initialization: {str(e)}")
                raise Exception(f"Failed to access the bucket during initialization: {str(e)}")
            
            # Store in session state
            st.session_state.firebase_db = db
            st.session_state.firebase_bucket = bucket
            st.session_state.firebase_initialized = True
        except Exception as e:
            st.error(f"Failed to initialize Firebase: {str(e)}")
            raise Exception(f"Failed to initialize Firebase: {str(e)}")

    # Verify that the Firestore client is valid
    if st.session_state.firebase_db is None or not hasattr(st.session_state.firebase_db, 'collection'):
        st.error("Firestore client is not properly initialized.")
        raise Exception("Firestore client is not properly initialized.")
    
    if st.session_state.firebase_bucket is None:
        st.error("Firebase Storage bucket is not initialized.")
        raise Exception("Firebase Storage bucket is not initialized.")
    
    return st.session_state.firebase_db, st.session_state.firebase_bucket

def upload_photo_to_storage(file, team_number, match_number=None):
    try:
        db, bucket = get_firebase_instances()  # Ensure Firebase is initialized
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        team_number = str(team_number)
        if match_number is not None:
            match_number = str(match_number)
            file_name = f"robot_photos/team_{team_number}_match_{match_number}_{timestamp}.jpg"
        else:
            file_name = f"robot_photos/team_{team_number}_pit_{timestamp}.jpg"

        blob = bucket.blob(file_name)
        blob.upload_from_file(file, content_type=file.type)
        blob.make_public()
        photo_url = blob.public_url
        return photo_url
    except Exception as e:
        st.error(f"Error uploading photo to Firebase Storage: {str(e)}")
        return None

def save_data(collection_name, data):
    try:
        db, _ = get_firebase_instances()  # Ensure Firebase is initialized
        
        if not isinstance(data, dict):
            st.error(f"Expected data to be a dictionary, got {type(data)}")
            return False, None

        cleaned_data = {}
        for k, v in data.items():
            if isinstance(v, pd.Series):
                if len(v) == 1:
                    v = v.iloc[0]
                else:
                    st.error(f"Value for {k} is a Series with multiple values: {v}")
                    return False, None
            if pd.isna(v):
                cleaned_data[k] = None
            else:
                cleaned_data[k] = v

        if 'timestamp' not in cleaned_data or not cleaned_data['timestamp']:
            cleaned_data['timestamp'] = datetime.now().isoformat()

        if 'team_number' not in cleaned_data or cleaned_data['team_number'] is None:
            st.error("Team number is missing in data.")
            return False, None
        team_number = str(cleaned_data['team_number']).strip()
        if not team_number:
            st.error("Team number is empty.")
            return False, None

        if "drivetrain_type" in cleaned_data:
            if collection_name != PIT_SCOUT_COLLECTION:
                st.warning(f"Expected collection '{PIT_SCOUT_COLLECTION}' for pit data, but got '{collection_name}'. Using '{PIT_SCOUT_COLLECTION}'.")
            collection_name = PIT_SCOUT_COLLECTION
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            doc_id = f"team{team_number}_pit_{timestamp}"
        else:
            if collection_name != MATCH_SCOUT_COLLECTION:
                st.warning(f"Expected collection '{MATCH_SCOUT_COLLECTION}' for match data, but got '{collection_name}'. Using '{MATCH_SCOUT_COLLECTION}'.")
            collection_name = MATCH_SCOUT_COLLECTION
            if 'match_number' not in cleaned_data or cleaned_data['match_number'] is None:
                st.error("Match number is missing in match data.")
                return False, None
            match_number = str(cleaned_data['match_number']).strip()
            if not match_number:
                st.error("Match number is empty.")
                return False, None
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            doc_id = f"team{team_number}_match{match_number}_{timestamp}"

        # Create the document reference and save the data
        doc_ref = db.collection(collection_name).document(doc_id)
        doc_ref.set(cleaned_data)
        return True, doc_id
    except Exception as e:
        st.error(f"Error saving data to Firestore: {str(e)}")
        return False, str(e)

def load_data():
    try:
        db, _ = get_firebase_instances()  # Ensure Firebase is initialized
        docs = db.collection(MATCH_SCOUT_COLLECTION).stream()
        data = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict['doc_id'] = doc.id
            data.append(doc_dict)
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        numeric_cols = [
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
            'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
            'auto_missed_algae_barge', 'auto_missed_algae_processor',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
            'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
            'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
            'teleop_missed_algae_barge', 'teleop_missed_algae_processor'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        if 'robot_photo_url' in df.columns:
            df['robot_photo_url'] = df['robot_photo_url'].astype(str).fillna('')
        return df
    except Exception as e:
        st.error(f"Error loading match data from Firestore: {str(e)}")
        return None

def load_pit_data():
    try:
        db, _ = get_firebase_instances()  # Ensure Firebase is initialized
        docs = db.collection(PIT_SCOUT_COLLECTION).stream()
        data = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict['doc_id'] = doc.id
            data.append(doc_dict)
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        numeric_cols = ['team_number']
        boolean_cols = [
            'can_score_coral_l1', 'can_score_coral_l2', 'can_score_coral_l3', 'can_score_coral_l4',
            'can_score_algae_barge', 'can_score_algae_processor', 'can_remove_algae_l1', 'can_remove_algae_l2'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        for col in boolean_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)
        if 'robot_photo_url' in df.columns:
            # Convert to string and handle None/NaN values
            df['robot_photo_url'] = df['robot_photo_url'].astype(str).replace('nan', '').replace('None', '')
        return df
    except Exception as e:
        st.error(f"Error loading pit data from Firestore: {str(e)}")
        return None

def calculate_match_score(row):
    auto_score = 0
    teleop_score = 0
    endgame_score = 0

    auto_score += row['auto_coral_l1'] * 2 + row['auto_coral_l2'] * 4 + row['auto_coral_l3'] * 6 + row['auto_coral_l4'] * 8
    auto_score += row['auto_algae_barge'] * 2 + row['auto_algae_processor'] * 3 + row['auto_algae_removed'] * 1
    if row['auto_taxi_left']:
        auto_score += 2

    teleop_score += row['teleop_coral_l1'] * 1 + row['teleop_coral_l2'] * 2 + row['teleop_coral_l3'] * 3 + row['teleop_coral_l4'] * 4
    teleop_score += row['teleop_algae_barge'] * 1 + row['teleop_algae_processor'] * 2 + row['teleop_algae_removed'] * 1

    if row['climb_status'] == 'Parked':
        endgame_score = 2
    elif row['climb_status'] == 'Shallow Climb':
        endgame_score = 6
    elif row['climb_status'] == 'Deep Climb':
        endgame_score = 12
    else:
        endgame_score = 0

    total_score = auto_score + teleop_score + endgame_score

    return pd.Series({
        'auto_score': auto_score,
        'teleop_score': teleop_score,
        'endgame_score': endgame_score,
        'total_score': total_score
    })

def calculate_epa(df, team_number):
    if df.empty or 'total_score' not in df.columns:
        return 0.0
    team_data = df[df['team_number'] == team_number]
    if team_data.empty:
        return 0.0
    mean_score = team_data['total_score'].mean()
    return mean_score if not pd.isna(mean_score) else 0.0