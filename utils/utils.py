# utils/utils.py
import pandas as pd
import streamlit as st
import os

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
        if os.path.exists(DATA_FILE):
            return pd.read_csv(DATA_FILE)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def save_data(data):
    try:
        if isinstance(data, pd.DataFrame):
            data.to_csv(DATA_FILE, index=False)
            return True
        return False
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

def clear_data():
    try:
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            return True
        return False
    except Exception as e:
        st.error(f"Error clearing data: {str(e)}")
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