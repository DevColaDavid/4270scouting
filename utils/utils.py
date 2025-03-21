# utils/utils.py
import os
import pandas as pd
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
from datetime import datetime

# Firestore client (will be initialized lazily)
db = None

# Firestore collection for scouting data
COLLECTION_NAME = "scouting_data"

# Initialize Firestore
def initialize_firestore():
    global db
    if db is not None:
        return None  # Already initialized, no error

    try:
        # On Streamlit Community Cloud, use secrets
        if "firebase" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(st.secrets["firebase"])
            db = firestore.Client(credentials=creds, project=st.secrets["firebase"]["project_id"])
            return None  # Success
        else:
            # Locally, use the JSON key file
            if not os.path.exists("firestore-key.json"):
                return "firestore-key.json not found. Please ensure the file exists in the project directory."
            db = firestore.Client.from_service_account_json("firestore-key.json")
            return None  # Success
    except Exception as e:
        return f"Error initializing Firestore: {str(e)}"

def load_data():
    try:
        # Initialize Firestore if not already initialized
        error = initialize_firestore()
        if error:
            st.error(error)
            return pd.DataFrame()

        if db is None:
            st.error("Firestore database not initialized.")
            return pd.DataFrame()

        # Fetch all documents from the scouting_data collection
        docs = db.collection(COLLECTION_NAME).stream()
        data = []
        for doc in docs:
            doc_dict = doc.to_dict()
            doc_dict["id"] = doc.id  # Include the document ID if needed
            data.append(doc_dict)

        # Define expected columns with default values
        expected_columns = {
            'team_number': 0,
            'match_number': 0,
            'alliance_color': '',
            'scouter_name': '',
            'starting_position': '',
            'auto_taxi_left': False,  # New field
            'auto_coral_l1': 0,
            'auto_coral_l2': 0,
            'auto_coral_l3': 0,
            'auto_coral_l4': 0,
            'auto_missed_coral_l1': 0,
            'auto_missed_coral_l2': 0,
            'auto_missed_coral_l3': 0,
            'auto_missed_coral_l4': 0,
            'auto_algae_barge': 0,
            'auto_algae_processor': 0,
            'auto_missed_algae_barge': 0,
            'auto_missed_algae_processor': 0,
            'auto_algae_removed': 0,
            'teleop_coral_l1': 0,
            'teleop_coral_l2': 0,
            'teleop_coral_l3': 0,
            'teleop_coral_l4': 0,
            'teleop_missed_coral_l1': 0,
            'teleop_missed_coral_l2': 0,
            'teleop_missed_coral_l3': 0,
            'teleop_missed_coral_l4': 0,
            'teleop_algae_barge': 0,
            'teleop_algae_processor': 0,
            'teleop_missed_algae_barge': 0,
            'teleop_missed_algae_processor': 0,
            'teleop_algae_removed': 0,
            'climb_status': 'No Climb',
            'defense_rating': 0.0,
            'speed_rating': 0.0,
            'driver_skill_rating': 0.0,
            'defense_qa': '',
            'teleop_qa': '',
            'auto_qa': '',
            'comments': '',
            'match_result': '',
            'timestamp': ''
        }

        if not data:
            # Return an empty DataFrame with all expected columns
            return pd.DataFrame(columns=list(expected_columns.keys()))

        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(data)

        # Ensure all expected columns are present, fill missing ones with defaults
        for col, default in expected_columns.items():
            if col not in df.columns:
                df[col] = default

        # Convert numeric columns to appropriate types
        numeric_cols = [
            'team_number', 'match_number',
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
            'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
            'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
            'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed',
            'defense_rating', 'speed_rating', 'driver_skill_rating'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Ensure boolean columns are boolean
        boolean_cols = ['auto_taxi_left']
        for col in boolean_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)

        # Ensure string columns are strings
        string_cols = [
            'alliance_color', 'scouter_name', 'starting_position', 'climb_status',
            'defense_qa', 'teleop_qa', 'auto_qa', 'comments', 'match_result', 'timestamp'
        ]
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')

        return df[list(expected_columns.keys())]

    except Exception as e:
        st.error(f"Error loading data from Firestore: {str(e)}")
        return pd.DataFrame()

def save_data(match_data):
    """
    Save match data to Firestore without checking for duplicates.
    Returns: (success, message)
    """
    try:
        # Initialize Firestore if not already initialized
        error = initialize_firestore()
        if error:
            st.error(error)
            return False, None

        if db is None:
            st.error("Firestore database not initialized.")
            return False, None

        # Ensure match_data is a dictionary
        if not isinstance(match_data, dict):
            st.error(f"Expected match_data to be a dictionary, got {type(match_data)}")
            return False, None

        # Convert match_data values to a Firestore-compatible format
        cleaned_data = {}
        for k, v in match_data.items():
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

        # Add a timestamp if not present
        if 'timestamp' not in cleaned_data or not cleaned_data['timestamp']:
            cleaned_data['timestamp'] = datetime.now().isoformat()

        # Ensure team_number and match_number are present and valid
        if 'team_number' not in cleaned_data or cleaned_data['team_number'] is None:
            st.error("Team number is missing in match data.")
            return False, None
        if 'match_number' not in cleaned_data or cleaned_data['match_number'] is None:
            st.error("Match number is missing in match data.")
            return False, None

        team_number = str(cleaned_data['team_number']).strip()
        match_number = str(cleaned_data['match_number']).strip()
        if not team_number or not match_number:
            st.error("Team number or match number is empty.")
            return False, None

        # Create a unique document ID using team_number, match_number, and timestamp
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        doc_id = f"team{team_number}_match{match_number}_{timestamp}"

        # Save the data with the custom document ID
        db.collection(COLLECTION_NAME).document(doc_id).set(cleaned_data)
        return True, doc_id

    except Exception as e:
        st.error(f"Error saving data to Firestore: {str(e)}")
        return False, str(e)

def calculate_match_score(row):
    # Auto Score
    auto_score = (
        (row['auto_coral_l1'] * 2) +
        (row['auto_coral_l2'] * 4) +
        (row['auto_coral_l3'] * 6) +
        (row['auto_coral_l4'] * 8) +
        (row['auto_algae_barge'] * 2) +
        (row['auto_algae_processor'] * 3) +
        (row['auto_algae_removed'] * 1)
    )
    # Add points for taxiing
    if row['auto_taxi_left']:
        auto_score += 2  # 2 points for leaving starting position

    # Teleop Score
    teleop_score = (
        (row['teleop_coral_l1'] * 1) +
        (row['teleop_coral_l2'] * 2) +
        (row['teleop_coral_l3'] * 3) +
        (row['teleop_coral_l4'] * 4) +
        (row['teleop_algae_barge'] * 1) +
        (row['teleop_algae_processor'] * 2) +
        (row['teleop_algae_removed'] * 1)
    )

    # Endgame Score
    endgame_score = 0
    if row['climb_status'] == 'Parked':
        endgame_score = 2  # 2 points for parking
    elif row['climb_status'] == 'Shallow Climb':
        endgame_score = 5
    elif row['climb_status'] == 'Deep Climb':
        endgame_score = 10

    total_score = auto_score + teleop_score + endgame_score

    return pd.Series({
        'auto_score': auto_score,
        'teleop_score': teleop_score,
        'endgame_score': endgame_score,
        'total_score': total_score
    })