
import pandas as pd
import streamlit as st
import os

DATA_FILE = "scouting_data.csv"

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
