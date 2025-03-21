# utils/utils.py
import pandas as pd
import streamlit as st
import os
from google.cloud import firestore
from google.oauth2 import service_account

# Initialize Firestore
def initialize_firestore():
    try:
        # On Streamlit Community Cloud, use secrets
        if "firebase" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(st.secrets["firebase"])
            db = firestore.Client(credentials=creds, project=st.secrets["firebase"]["project_id"])
        else:
            # Locally, use the JSON key file
            db = firestore.Client.from_service_account_json("firestore-key.json")
        return db
    except Exception as e:
        st.error(f"Error initializing Firestore: {str(e)}")
        return None

# Firestore client
db = initialize_firestore()

# Firestore collection for scouting data
COLLECTION_NAME = "scouting_data"

DATA_FILE = "scouting_data.csv"

# Define the 2025 Reefscape Point System (Hypothetical)
POINT_SYSTEM = {
    'auto': {
        'coral_l1': 2,
        'coral_l2': 4,
        'coral_l3': 6,
        'coral_l4': 8,
        'algae_removed': 3,
        'algae_processor': 5,
        'algae_barge': 2,
    },
    'teleop': {
        'coral_l1': 1,
        'coral_l2': 2,
        'coral_l3': 3,
        'coral_l4': 4,
        'algae_removed': 2,
        'algae_processor': 3,
        'algae_barge': 1,
    },
    'endgame': {
        'No Climb': 0,
        'Parked': 5,
        'Shallow Climb': 10,
        'Deep Climb': 20,
    }
}

def calculate_match_score(row):
    auto_score = sum(row.get(f'auto_{key}', 0) * value for key, value in POINT_SYSTEM['auto'].items())
    teleop_score = sum(row.get(f'teleop_{key}', 0) * value for key, value in POINT_SYSTEM['teleop'].items())
    endgame_score = POINT_SYSTEM['endgame'].get(row.get('climb_status', 'No Climb'), 0)
    total_score = auto_score + teleop_score + endgame_score
    return pd.Series([total_score, auto_score, teleop_score, endgame_score], 
                     index=['total_score', 'auto_score', 'teleop_score', 'endgame_score'])

def load_data():
    try:
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

        if not data:
            # Return an empty DataFrame with expected columns if no data exists
            columns = [
                'team_number', 'match_number', 'alliance_color', 'scouter_name', 'starting_position',
                'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
                'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
                'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
                'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
                'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
                'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed',
                'climb_status', 'defense_rating', 'speed_rating', 'driver_skill_rating',
                'defense_qa', 'teleop_qa', 'auto_qa', 'comments', 'match_result', 'timestamp'
            ]
            return pd.DataFrame(columns=columns)

        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(data)
        # Ensure all expected columns are present, fill missing ones with NaN
        expected_columns = [
            'team_number', 'match_number', 'alliance_color', 'scouter_name', 'starting_position',
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
            'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
            'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
            'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed',
            'climb_status', 'defense_rating', 'speed_rating', 'driver_skill_rating',
            'defense_qa', 'teleop_qa', 'auto_qa', 'comments', 'match_result', 'timestamp'
        ]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = pd.NA
        return df[expected_columns]
    except Exception as e:
        st.error(f"Error loading data from Firestore: {str(e)}")
        return pd.DataFrame()

def save_data(match_data):
    try:
        if db is None:
            st.error("Firestore database not initialized.")
            return False

        # Convert the match_data dictionary to a format suitable for Firestore
        # Firestore doesn't support NaN, so replace with None
        match_data = {k: (None if pd.isna(v) else v) for k, v in match_data.items()}
        
        # Add the match data as a new document to the scouting_data collection
        db.collection(COLLECTION_NAME).add(match_data)
        return True
    except Exception as e:
        st.error(f"Error saving data to Firestore: {str(e)}")
        return False

def clear_data():
    try:
        if db is None:
            st.error("Firestore database not initialized.")
            return False

        # Get all documents in the scouting_data collection
        docs = db.collection(COLLECTION_NAME).stream()
        
        # Delete each document
        for doc in docs:
            doc.reference.delete()
        
        st.info("All data cleared successfully from Firestore.")
        return True
    except Exception as e:
        st.error(f"Error clearing data from Firestore: {str(e)}")
        return False


def validate_team_number(team_number):
    try:
        team_num = int(team_number)
        return 1 <= team_num <= 9999
    except:
        return False

def validate_match_number(match_number):
    try:
        match_num = int(match_number)
        return match_num > 0
    except:
        return False