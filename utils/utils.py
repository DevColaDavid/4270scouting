# utils/utils.py
import os
import pandas as pd
import streamlit as st
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

        # Ensure match_data is a dictionary
        if not isinstance(match_data, dict):
            st.error(f"Expected match_data to be a dictionary, got {type(match_data)}")
            return False

        # Convert match_data values to a Firestore-compatible format
        cleaned_data = {}
        for k, v in match_data.items():
            # If v is a Series, convert it to a scalar
            if isinstance(v, pd.Series):
                if len(v) == 1:
                    v = v.iloc[0]  # Extract the single value
                else:
                    st.error(f"Value for {k} is a Series with multiple values: {v}")
                    return False
            # Handle NaN values
            if pd.isna(v):
                cleaned_data[k] = None
            else:
                cleaned_data[k] = v

        # Add the cleaned data as a new document to the scouting_data collection
        db.collection(COLLECTION_NAME).add(cleaned_data)
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
    if row['climb_status'] == 'Shallow Climb':
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