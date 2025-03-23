# utils/utils.py
import os
import pandas as pd
from datetime import datetime
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import sys

db = None
COLLECTION_NAME = "scouting_data"

def initialize_firestore():
    """Initialize the Firestore client using Streamlit secrets or a local key file."""
    global db
    if db is not None:
        return None
    try:
        if "firebase" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(st.secrets["firebase"])
            db = firestore.Client(credentials=creds, project=st.secrets["firebase"]["project_id"])
            return None
        else:
            if not os.path.exists("firestore-key.json"):
                return "firestore-key.json not found."
            db = firestore.Client.from_service_account_json("firestore-key.json")
            return None
    except Exception as e:
        return f"Error initializing Firestore: {str(e)}"

def save_data(match_data):
    """Save match data to Firestore with a unique document ID."""
    try:
        error = initialize_firestore()
        if error:
            st.error(error)
            return False, None
        if db is None:
            st.error("Firestore database not initialized.")
            return False, None
        if not isinstance(match_data, dict):
            st.error(f"Expected match_data to be a dictionary, got {type(match_data)}")
            return False, None
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
        if 'timestamp' not in cleaned_data or not cleaned_data['timestamp']:
            cleaned_data['timestamp'] = datetime.now().isoformat()
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
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        doc_id = f"team{team_number}_match{match_number}_{timestamp}"
        db.collection(COLLECTION_NAME).document(doc_id).set(cleaned_data)
        return True, doc_id
    except Exception as e:
        st.error(f"Error saving data to Firestore: {str(e)}")
        return False, str(e)

def load_data():
    """Load data from Firestore and return it as a pandas DataFrame."""
    try:
        error = initialize_firestore()
        if error:
            st.error(error)
            return None
        if db is None:
            st.error("Firestore database not initialized.")
            return None
        docs = db.collection(COLLECTION_NAME).stream()
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
        return df
    except Exception as e:
        st.error(f"Error loading data from Firestore: {str(e)}")
        return None

def calculate_match_score(row):
    """
    Calculate the match score for a single row of data.
    
    Scoring Rules:
    - Autonomous:
        - Coral: Level 1 = 2 points, Level 2 = 4 points, Level 3 = 6 points, Level 4 = 8 points
        - Algae: Barge = 2 points, Processor = 3 points, Removed = 1 point
        - Taxi: 2 points if auto_taxi_left is True
    - Teleop:
        - Coral: Level 1 = 1 point, Level 2 = 2 points, Level 3 = 3 points, Level 4 = 4 points
        - Algae: Barge = 1 point, Processor = 2 points, Removed = 1 point
    - Endgame (based on climb_status):
        - None: 0 points
        - Parked: 2 points
        - Shallow Climb: 6 points
        - Deep Climb: 12 points
    """
    # Initialize scores
    auto_score = 0
    teleop_score = 0
    endgame_score = 0

    # Auto score
    auto_score += row['auto_coral_l1'] * 2 + row['auto_coral_l2'] * 4 + row['auto_coral_l3'] * 6 + row['auto_coral_l4'] * 8
    auto_score += row['auto_algae_barge'] * 2 + row['auto_algae_processor'] * 3 + row['auto_algae_removed'] * 1
    if row['auto_taxi_left']:
        auto_score += 2

    # Teleop score
    teleop_score += row['teleop_coral_l1'] * 1 + row['teleop_coral_l2'] * 2 + row['teleop_coral_l3'] * 3 + row['teleop_coral_l4'] * 4
    teleop_score += row['teleop_algae_barge'] * 1 + row['teleop_algae_processor'] * 2 + row['teleop_algae_removed'] * 1

    # Endgame score
    if row['climb_status'] == 'Parked':
        endgame_score = 2
    elif row['climb_status'] == 'Shallow Climb':
        endgame_score = 6
    elif row['climb_status'] == 'Deep Climb':
        endgame_score = 12
    else:  # 'None' or any other value
        endgame_score = 0

    # Calculate total score (without alliance bonuses, which are added in 2_Data_Analysis.py)
    total_score = auto_score + teleop_score + endgame_score

    return pd.Series({
        'auto_score': auto_score,
        'teleop_score': teleop_score,
        'endgame_score': endgame_score,
        'total_score': total_score
    })

def calculate_epa(df, team_number):
    """Calculate the Expected Points Added (EPA) for a team based on their average total score."""
    if df.empty or 'total_score' not in df.columns:
        return 0.0
    team_data = df[df['team_number'] == team_number]
    if team_data.empty:
        return 0.0
    mean_score = team_data['total_score'].mean()
    return mean_score if not pd.isna(mean_score) else 0.0