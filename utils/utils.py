import os
import pandas as pd
from datetime import datetime
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

db = None
COLLECTION_NAME = "scouting_data"

def initialize_firestore():
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
    Calculate the match score for a single team's performance in FRC 2025 REEFSCAPE.
    Returns a Series with auto_score, teleop_score, endgame_score, and total_score.
    Note: Alliance-level bonuses (co-op bonus, harmony bonus) are calculated separately.
    """
    # Autonomous Period
    auto_score = (
        (row['auto_coral_l1'] * 3) +    # Level 1 coral: 3 points each
        (row['auto_coral_l2'] * 5) +    # Level 2 coral: 5 points each
        (row['auto_coral_l3'] * 8) +    # Level 3 coral: 8 points each
        (row['auto_coral_l4'] * 12) +   # Level 4 coral: 12 points each
        (row['auto_algae_barge'] * 4) + # Algae to barge: 4 points each
        (row['auto_algae_processor'] * 6) +  # Algae to processor: 6 points each
        (row['auto_algae_removed'] * 2)  # Algae removed: 2 points each
    )
    # Taxi points
    if row['auto_taxi_left']:
        auto_score += 4  # 4 points for leaving starting position

    # Teleop Period
    teleop_score = (
        (row['teleop_coral_l1'] * 1) +  # Level 1 coral: 1 point each
        (row['teleop_coral_l2'] * 2) +  # Level 2 coral: 2 points each
        (row['teleop_coral_l3'] * 4) +  # Level 3 coral: 4 points each
        (row['teleop_coral_l4'] * 6) +  # Level 4 coral: 6 points each
        (row['teleop_algae_barge'] * 2) +  # Algae to barge: 2 points each
        (row['teleop_algae_processor'] * 6) +  # Algae to processor: 6 points each
        (row['teleop_algae_removed'] * 1)  # Algae removed: 1 point each
    )

    # Endgame Score (interpreted as attaching to the barge)
    endgame_score = 0
    if row['climb_status'] == 'Parked':
        endgame_score = 3  # 3 points for parking
    elif row['climb_status'] == 'Shallow Climb':
        endgame_score = 6  # 6 points for shallow climb
    elif row['climb_status'] == 'Deep Climb':
        endgame_score = 12  # 12 points for deep climb

    # Calculate total score before alliance-level bonuses
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