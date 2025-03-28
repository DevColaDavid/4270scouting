import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from utils.utils import load_data, load_pit_data, calculate_match_score
from utils.utils import setup_sidebar_navigation
from utils.tba_api import get_tba_api_key

st.set_page_config(page_title="Team Statistics", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in to access this page.")
    st.stop()

# Set up the sidebar navigation
setup_sidebar_navigation()

# Custom CSS for modern styling and coloring
st.markdown("""
    <style>
    .team-card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .team-card img {
        border-radius: 8px;
        max-width: 150px;
        max-height: 150px;
        object-fit: cover;
    }
    .team-card h2 {
        margin: 0;
        color: #1f77b4;
    }
    .team-card p {
        margin: 5px 0;
        color: #555;
    }
    .stat-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 10px;
    }
    .stat-card h4 {
        margin: 0;
        color: #333;
    }
    .stat-card p {
        margin: 5px 0;
        font-size: 1.2em;
        color: #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #e6f0fa;
        border-radius: 5px;
        padding: 10px 20px;
        color: #1f77b4;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1f77b4;
        color: #ffffff;
    }
    .photo-gallery {
        display: flex;
        overflow-x: auto;
        gap: 10px;
        padding: 10px 0;
    }
    .photo-gallery img {
        border-radius: 8px;
        max-height: 150px;
        object-fit: cover;
    }
    /* Custom styles for Detailed Statistics */
    .stat-section {
        background-color: #f5f5f5;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .stat-section h4 {
        margin: 0 0 10px 0;
        color: #1f77b4;
    }
    .stat-item {
        margin: 5px 0;
        font-size: 0.95em;
    }
    .auto-stat {
        color: #2ca02c; /* Green for autonomous stats */
    }
    .teleop-stat {
        color: #d62728; /* Red for teleop stats */
    }
    .highlight {
        font-weight: bold;
        color: #ff7f0e; /* Orange for highlighted metrics like success ratio */
    }
    </style>
""", unsafe_allow_html=True)

# Function to fetch team data from The Blue Alliance API
def fetch_team_data(team_number, auth_key):
    url = f"https://www.thebluealliance.com/api/v3/team/frc{team_number}"
    headers = {"X-TBA-Auth-Key": auth_key}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {
            "team_number": data.get("team_number", team_number),
            "nickname": data.get("nickname", "Unknown"),
            "name": data.get("name", "Unknown"),
            "location": f"{data.get('city', '')}, {data.get('state_prov', '')}, {data.get('country', '')}".strip(", "),
            "rookie_year": data.get("rookie_year", "Unknown"),
            "motto": data.get("motto", "Not Provided")
        }
    except Exception as e:
        st.error(f"Failed to fetch team data from The Blue Alliance: {str(e)}")
        return {
            "team_number": team_number,
            "nickname": "Unknown",
            "name": "Unknown",
            "location": "Unknown",
            "rookie_year": "Unknown",
            "motto": "Not Provided"
        }

# Load match and pit data
try:
    match_df = load_data()
except Exception as e:
    st.error(f"Failed to load match data: {str(e)}")
    match_df = pd.DataFrame()

try:
    pit_df = load_pit_data()
except Exception as e:
    st.error(f"Failed to load pit scouting data: {str(e)}")
    pit_df = pd.DataFrame()

# Check if both datasets are empty
if (match_df is None or match_df.empty) and (pit_df is None or pit_df.empty):
    st.info("No match or pit scouting data available to display team statistics. Please upload data in the Data Upload page.")
    st.stop()

# Warn if either dataset is empty
if match_df is None or match_df.empty:
    st.warning("No match data available. Only pit scouting data will be displayed.")
    match_df = pd.DataFrame()
if pit_df is None or pit_df.empty:
    st.warning("No pit scouting data available. Only match scouting data will be displayed.")
    pit_df = pd.DataFrame()

# Ensure numeric columns
numeric_cols = [
    'match_number', 'team_number',
    'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
    'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
    'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
    'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
    'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
    'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed',
    'defense_rating', 'speed_rating', 'driver_skill_rating'
]
for col in numeric_cols:
    if col in match_df.columns:
        match_df[col] = pd.to_numeric(match_df[col], errors='coerce').fillna(0)

pit_numeric_cols = ['team_number']
pit_boolean_cols = [
    'can_score_coral_l1', 'can_score_coral_l2', 'can_score_coral_l3', 'can_score_coral_l4',
    'can_score_algae_barge', 'can_score_algae_processor', 'can_remove_algae_l1', 'can_remove_algae_l2'
]
for col in pit_numeric_cols:
    if col in pit_df.columns:
        pit_df[col] = pd.to_numeric(pit_df[col], errors='coerce').fillna(0)
for col in pit_boolean_cols:
    if col in pit_df.columns:
        pit_df[col] = pit_df[col].astype(bool)

# Convert team_number to string
if 'team_number' in match_df.columns:
    match_df['team_number'] = match_df['team_number'].astype(str)
if 'team_number' in pit_df.columns:
    pit_df['team_number'] = pit_df['team_number'].astype(str)

# Calculate match scores and alliance bonuses if match data exists
if not match_df.empty:
    required_cols = [
        'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
        'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
        'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
        'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
        'auto_taxi_left', 'climb_status', 'match_number', 'alliance_color'
    ]

    score_columns = ['auto_score', 'teleop_score', 'endgame_score', 'total_score']
    if all(col in match_df.columns for col in required_cols):
        if not all(col in match_df.columns for col in score_columns):
            scores = match_df.apply(calculate_match_score, axis=1)
            match_df[score_columns] = scores

        def calculate_alliance_bonuses(df):
            if 'match_number' in df.columns and 'alliance_color' in df.columns:
                df['match_number'] = df['match_number'].astype(str)
                df['alliance_color'] = df['alliance_color'].fillna('unknown').str.lower()
            else:
                df['coop_bonus'] = 0
                df['harmony_bonus'] = 0
                return df

            coral_cols = [
                'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
                'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4'
            ]
            for col in coral_cols:
                if col not in df.columns:
                    df[col] = 0
            alliance_coral = df.groupby(['match_number', 'alliance_color'])[coral_cols].sum().reset_index()
            alliance_coral['l1_total'] = alliance_coral['auto_coral_l1'] + alliance_coral['teleop_coral_l1']
            alliance_coral['l2_total'] = alliance_coral['auto_coral_l2'] + alliance_coral['teleop_coral_l2']
            alliance_coral['l3_total'] = alliance_coral['auto_coral_l3'] + alliance_coral['teleop_coral_l3']
            alliance_coral['l4_total'] = alliance_coral['auto_coral_l4'] + alliance_coral['teleop_coral_l4']
            alliance_coral['levels_with_5_plus'] = (
                (alliance_coral['l1_total'] >= 5).astype(int) +
                (alliance_coral['l2_total'] >= 5).astype(int) +
                (alliance_coral['l3_total'] >= 5).astype(int) +
                (alliance_coral['l4_total'] >= 5).astype(int)
            )
            alliance_coral['coop_bonus'] = alliance_coral['levels_with_5_plus'].apply(
                lambda x: 15 if x >= 3 else 0
            )
            alliance_coral['match_number'] = alliance_coral['match_number'].astype(str)
            alliance_coral['alliance_color'] = alliance_coral['alliance_color'].str.lower()
            df = df.merge(
                alliance_coral[['match_number', 'alliance_color', 'coop_bonus']],
                on=['match_number', 'alliance_color'],
                how='left'
            )
            if 'coop_bonus' not in df.columns:
                df['coop_bonus'] = 0

            if 'climb_status' in df.columns:
                alliance_climb = df.groupby(['match_number', 'alliance_color'])['climb_status'].value_counts().unstack(fill_value=0)
                alliance_climb['num_robots'] = df.groupby(['match_number', 'alliance_color'])['team_number'].nunique()
                alliance_climb['num_climbs'] = alliance_climb.get('Shallow Climb', 0) + alliance_climb.get('Deep Climb', 0)
                alliance_climb['harmony_bonus'] = alliance_climb.apply(
                    lambda row: 15 if row['num_climbs'] == row['num_robots'] and row['num_robots'] > 0 else 0, axis=1
                )
            else:
                alliance_climb = df.groupby(['match_number', 'alliance_color'])['team_number'].nunique()
                alliance_climb['harmony_bonus'] = 0

            alliance_climb = alliance_climb.reset_index()
            alliance_climb['match_number'] = alliance_climb['match_number'].astype(str)
            alliance_climb['alliance_color'] = alliance_climb['alliance_color'].str.lower()
            df = df.merge(
                alliance_climb[['match_number', 'alliance_color', 'harmony_bonus']],
                on=['match_number', 'alliance_color'],
                how='left'
            )
            if 'harmony_bonus' not in df.columns:
                df['harmony_bonus'] = 0

            df['total_score'] = (
                df['total_score'] +
                df['coop_bonus'].fillna(0) +
                df['harmony_bonus'].fillna(0)
            )
            return df

        match_df = calculate_alliance_bonuses(match_df)
    else:
        st.warning("Cannot calculate match scores. Missing required columns: " +
                   ", ".join([col for col in required_cols if col not in match_df.columns]))

    # Check for duplicates in match data
    duplicates = match_df[match_df.duplicated(subset=['team_number', 'match_number'], keep=False)]
    if not duplicates.empty:
        st.warning("Duplicate form submissions detected for the same team and match number:")
        st.write(duplicates[['team_number', 'match_number', 'alliance_color', 'total_score']])
        if 'timestamp' in match_df.columns:
            match_df['timestamp'] = pd.to_datetime(match_df['timestamp'], errors='coerce')
            match_df = match_df.sort_values(by=['team_number', 'match_number', 'timestamp']).drop_duplicates(subset=['team_number', 'match_number'], keep='last')
            st.info("Duplicates resolved by keeping the most recent submission based on timestamp.")
        else:
            match_df = match_df.drop_duplicates(subset=['team_number', 'match_number'], keep='first')
            st.info("Duplicates resolved by keeping the first submission. Consider adding a timestamp column.")

    # Calculate success ratios and additional metrics
    match_df['auto_coral_success'] = match_df['auto_coral_l1'] + match_df['auto_coral_l2'] + match_df['auto_coral_l3'] + match_df['auto_coral_l4']
    match_df['auto_coral_missed'] = match_df['auto_missed_coral_l1'] + match_df['auto_missed_coral_l2'] + match_df['auto_missed_coral_l3'] + match_df['auto_missed_coral_l4']
    match_df['teleop_coral_success'] = match_df['teleop_coral_l1'] + match_df['teleop_coral_l2'] + match_df['teleop_coral_l3'] + match_df['teleop_coral_l4']
    match_df['teleop_coral_missed'] = match_df['teleop_missed_coral_l1'] + match_df['teleop_missed_coral_l2'] + match_df['teleop_missed_coral_l3'] + match_df['teleop_missed_coral_l4']
    match_df['auto_coral_attempts'] = match_df['auto_coral_success'] + match_df['auto_coral_missed']
    match_df['teleop_coral_attempts'] = match_df['teleop_coral_success'] + match_df['teleop_coral_missed']
    match_df['auto_coral_success_ratio'] = (match_df['auto_coral_success'] / match_df['auto_coral_attempts'].replace(0, pd.NA)).fillna(0)
    match_df['teleop_coral_success_ratio'] = (match_df['teleop_coral_success'] / match_df['teleop_coral_attempts'].replace(0, pd.NA)).fillna(0)

    match_df['auto_algae_success'] = match_df['auto_algae_barge'] + match_df['auto_algae_processor']
    match_df['auto_algae_missed'] = match_df['auto_missed_algae_barge'] + match_df['auto_missed_algae_processor']
    match_df['teleop_algae_success'] = match_df['teleop_algae_barge'] + match_df['teleop_algae_processor']
    match_df['teleop_algae_missed'] = match_df['teleop_missed_algae_barge'] + match_df['teleop_missed_algae_processor']
    match_df['auto_algae_attempts'] = match_df['auto_algae_success'] + match_df['auto_algae_missed']
    match_df['teleop_algae_attempts'] = match_df['teleop_algae_success'] + match_df['teleop_algae_missed']
    match_df['auto_algae_success_ratio'] = (match_df['auto_algae_success'] / match_df['auto_algae_attempts'].replace(0, pd.NA)).fillna(0)
    match_df['teleop_algae_success_ratio'] = (match_df['teleop_algae_success'] / match_df['teleop_algae_attempts'].replace(0, pd.NA)).fillna(0)

    # Calculate match outcomes
    def calculate_match_outcomes(df):
        df['alliance_color'] = df['alliance_color'].str.title()
        scores_pivot = df.pivot_table(
            index='match_number',
            columns='alliance_color',
            values='total_score',
            aggfunc='sum'
        ).reset_index()
        if 'Red' not in scores_pivot.columns:
            scores_pivot['Red'] = 0
        if 'Blue' not in scores_pivot.columns:
            scores_pivot['Blue'] = 0
        scores_pivot['calculated_winner'] = scores_pivot.apply(
            lambda row: 'Red' if row['Red'] > row['Blue'] else ('Blue' if row['Blue'] > row['Red'] else 'Tie'),
            axis=1
        )
        df = df.merge(
            scores_pivot[['match_number', 'calculated_winner']],
            on='match_number',
            how='left'
        )

        def determine_outcome(row):
            manual_outcome = row['match_outcome']
            calculated_winner = row['calculated_winner']
            alliance_color = row['alliance_color']
            if pd.notna(manual_outcome):
                if manual_outcome == 'Won':
                    expected_winner = alliance_color
                elif manual_outcome == 'Lost':
                    expected_winner = 'Blue' if alliance_color == 'Red' else 'Red'
                else:
                    expected_winner = 'Tie'
                if expected_winner != calculated_winner:
                    row['outcome_discrepancy'] = f"Manual: {manual_outcome}, Calculated: {calculated_winner}"
                else:
                    row['outcome_discrepancy'] = None
                return manual_outcome
            else:
                if calculated_winner == 'Tie':
                    return 'Tie'
                elif calculated_winner == alliance_color:
                    return 'Won'
                else:
                    return 'Lost'

        df['outcome_discrepancy'] = None
        df['match_outcome_final'] = df.apply(determine_outcome, axis=1)
        return df

    match_df = calculate_match_outcomes(match_df)

    discrepancies = match_df[match_df['outcome_discrepancy'].notna()]
    if not discrepancies.empty:
        st.warning("Discrepancies found between manual and calculated match outcomes:")
        st.write(discrepancies[['match_number', 'team_number', 'alliance_color', 'match_outcome', 'calculated_winner', 'outcome_discrepancy']])

# Team selection: Combine teams from both match_df and pit_df
match_teams = match_df['team_number'].unique() if 'team_number' in match_df.columns else []
pit_teams = pit_df['team_number'].unique() if 'team_number' in pit_df.columns else []
all_teams = sorted(set(match_teams).union(set(pit_teams)))

if not all_teams:
    st.error("No teams found in match or pit scouting data.")
    st.stop()

selected_team = st.selectbox("Select a Team", options=all_teams)

# Filter data for the selected team
team_data = match_df[match_df['team_number'] == selected_team] if not match_df.empty else pd.DataFrame()
team_pit_data = pit_df[pit_df['team_number'] == selected_team] if not pit_df.empty else pd.DataFrame()

# Initialize team_stats with default values
team_stats = pd.DataFrame({
    'team_number': [selected_team],
    'avg_total_score': [0.0],
    'avg_auto_score': [0.0],
    'avg_teleop_score': [0.0],
    'avg_endgame_score': [0.0],
    'avg_auto_coral_success': [0.0],
    'total_auto_coral_success': [0],
    'avg_auto_coral_missed': [0.0],
    'total_auto_coral_missed': [0],
    'avg_teleop_coral_success': [0.0],
    'total_teleop_coral_success': [0],
    'avg_teleop_coral_missed': [0.0],
    'total_teleop_coral_missed': [0],
    'avg_auto_coral_l1': [0.0],
    'total_auto_coral_l1': [0],
    'avg_auto_coral_l2': [0.0],
    'total_auto_coral_l2': [0],
    'avg_auto_coral_l3': [0.0],
    'total_auto_coral_l3': [0],
    'avg_auto_coral_l4': [0.0],
    'total_auto_coral_l4': [0],
    'avg_teleop_coral_l1': [0.0],
    'total_teleop_coral_l1': [0],
    'avg_teleop_coral_l2': [0.0],
    'total_teleop_coral_l2': [0],
    'avg_teleop_coral_l3': [0.0],
    'total_teleop_coral_l3': [0],
    'avg_teleop_coral_l4': [0.0],
    'total_teleop_coral_l4': [0],
    'avg_auto_missed_coral_l1': [0.0],
    'total_auto_missed_coral_l1': [0],
    'avg_auto_missed_coral_l2': [0.0],
    'total_auto_missed_coral_l2': [0],
    'avg_auto_missed_coral_l3': [0.0],
    'total_auto_missed_coral_l3': [0],
    'avg_auto_missed_coral_l4': [0.0],
    'total_auto_missed_coral_l4': [0],
    'avg_teleop_missed_coral_l1': [0.0],
    'total_teleop_missed_coral_l1': [0],
    'avg_teleop_missed_coral_l2': [0.0],
    'total_teleop_missed_coral_l2': [0],
    'avg_teleop_missed_coral_l3': [0.0],
    'total_teleop_missed_coral_l3': [0],
    'avg_teleop_missed_coral_l4': [0.0],
    'total_teleop_missed_coral_l4': [0],
    'avg_auto_algae_processor': [0.0],
    'total_auto_algae_processor': [0],
    'avg_teleop_algae_processor': [0.0],
    'total_teleop_algae_processor': [0],
    'avg_auto_algae_barge': [0.0],
    'total_auto_algae_barge': [0],
    'avg_teleop_algae_barge': [0.0],
    'total_teleop_algae_barge': [0],
    'avg_auto_missed_algae_barge': [0.0],
    'total_auto_missed_algae_barge': [0],
    'avg_teleop_missed_algae_barge': [0.0],
    'total_teleop_missed_algae_barge': [0],
    'avg_auto_missed_algae_processor': [0.0],
    'total_auto_missed_algae_processor': [0],
    'avg_teleop_missed_algae_processor': [0.0],
    'total_teleop_missed_algae_processor': [0],
    'avg_auto_algae_removed': [0.0],
    'total_auto_algae_removed': [0],
    'avg_teleop_algae_removed': [0.0],
    'total_teleop_algae_removed': [0],
    'avg_auto_coral_success_ratio': [0.0],
    'avg_teleop_coral_success_ratio': [0.0],
    'avg_auto_algae_success_ratio': [0.0],
    'avg_teleop_algae_success_ratio': [0.0],
    'avg_defense_rating': [0.0],
    'avg_speed_rating': [0.0],
    'avg_driver_skill_rating': [0.0],
    'total_auto_objects_scored': [0],
    'total_teleop_objects_scored': [0],
    'total_objects_scored': [0]
})

# Calculate team statistics if match data exists
if not team_data.empty:
    team_stats = team_data.groupby('team_number').agg({
        'total_score': 'mean',
        'auto_score': 'mean',
        'teleop_score': 'mean',
        'endgame_score': 'mean',
        'auto_coral_success': ['mean', 'sum'],
        'auto_coral_missed': ['mean', 'sum'],
        'teleop_coral_success': ['mean', 'sum'],
        'teleop_coral_missed': ['mean', 'sum'],
        'auto_coral_l1': ['mean', 'sum'],
        'auto_coral_l2': ['mean', 'sum'],
        'auto_coral_l3': ['mean', 'sum'],
        'auto_coral_l4': ['mean', 'sum'],
        'teleop_coral_l1': ['mean', 'sum'],
        'teleop_coral_l2': ['mean', 'sum'],
        'teleop_coral_l3': ['mean', 'sum'],
        'teleop_coral_l4': ['mean', 'sum'],
        'auto_missed_coral_l1': ['mean', 'sum'],
        'auto_missed_coral_l2': ['mean', 'sum'],
        'auto_missed_coral_l3': ['mean', 'sum'],
        'auto_missed_coral_l4': ['mean', 'sum'],
        'teleop_missed_coral_l1': ['mean', 'sum'],
        'teleop_missed_coral_l2': ['mean', 'sum'],
        'teleop_missed_coral_l3': ['mean', 'sum'],
        'teleop_missed_coral_l4': ['mean', 'sum'],
        'auto_algae_processor': ['mean', 'sum'],
        'teleop_algae_processor': ['mean', 'sum'],
        'auto_algae_barge': ['mean', 'sum'],
        'teleop_algae_barge': ['mean', 'sum'],
        'auto_missed_algae_barge': ['mean', 'sum'],
        'teleop_missed_algae_barge': ['mean', 'sum'],
        'auto_missed_algae_processor': ['mean', 'sum'],
        'teleop_missed_algae_processor': ['mean', 'sum'],
        'auto_algae_removed': ['mean', 'sum'],
        'teleop_algae_removed': ['mean', 'sum'],
        'auto_coral_success_ratio': 'mean',
        'teleop_coral_success_ratio': 'mean',
        'auto_algae_success_ratio': 'mean',
        'teleop_algae_success_ratio': 'mean',
        'defense_rating': 'mean',
        'speed_rating': 'mean',
        'driver_skill_rating': 'mean'
    }).reset_index()

    team_stats.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in team_stats.columns]
    team_stats = team_stats.rename(columns={
        'team_number_': 'team_number',
        'total_score_mean': 'avg_total_score',
        'auto_score_mean': 'avg_auto_score',
        'teleop_score_mean': 'avg_teleop_score',
        'endgame_score_mean': 'avg_endgame_score',
        'auto_coral_success_mean': 'avg_auto_coral_success',
        'auto_coral_success_sum': 'total_auto_coral_success',
        'auto_coral_missed_mean': 'avg_auto_coral_missed',
        'auto_coral_missed_sum': 'total_auto_coral_missed',
        'teleop_coral_success_mean': 'avg_teleop_coral_success',
        'teleop_coral_success_sum': 'total_teleop_coral_success',
        'teleop_coral_missed_mean': 'avg_teleop_coral_missed',
        'teleop_coral_missed_sum': 'total_teleop_coral_missed',
        'auto_coral_l1_mean': 'avg_auto_coral_l1',
        'auto_coral_l1_sum': 'total_auto_coral_l1',
        'auto_coral_l2_mean': 'avg_auto_coral_l2',
        'auto_coral_l2_sum': 'total_auto_coral_l2',
        'auto_coral_l3_mean': 'avg_auto_coral_l3',
        'auto_coral_l3_sum': 'total_auto_coral_l3',
        'auto_coral_l4_mean': 'avg_auto_coral_l4',
        'auto_coral_l4_sum': 'total_auto_coral_l4',
        'teleop_coral_l1_mean': 'avg_teleop_coral_l1',
        'teleop_coral_l1_sum': 'total_teleop_coral_l1',
        'teleop_coral_l2_mean': 'avg_teleop_coral_l2',
        'teleop_coral_l2_sum': 'total_teleop_coral_l2',
        'teleop_coral_l3_mean': 'avg_teleop_coral_l3',
        'teleop_coral_l3_sum': 'total_teleop_coral_l3',
        'teleop_coral_l4_mean': 'avg_teleop_coral_l4',
        'teleop_coral_l4_sum': 'total_teleop_coral_l4',
        'auto_missed_coral_l1_mean': 'avg_auto_missed_coral_l1',
        'auto_missed_coral_l1_sum': 'total_auto_missed_coral_l1',
        'auto_missed_coral_l2_mean': 'avg_auto_missed_coral_l2',
        'auto_missed_coral_l2_sum': 'total_auto_missed_coral_l2',
        'auto_missed_coral_l3_mean': 'avg_auto_missed_coral_l3',
        'auto_missed_coral_l3_sum': 'total_auto_missed_coral_l3',
        'auto_missed_coral_l4_mean': 'avg_auto_missed_coral_l4',
        'auto_missed_coral_l4_sum': 'total_auto_missed_coral_l4',
        'teleop_missed_coral_l1_mean': 'avg_teleop_missed_coral_l1',
        'teleop_missed_coral_l1_sum': 'total_teleop_missed_coral_l1',
        'teleop_missed_coral_l2_mean': 'avg_teleop_missed_coral_l2',
        'teleop_missed_coral_l2_sum': 'total_teleop_missed_coral_l2',
        'teleop_missed_coral_l3_mean': 'avg_teleop_missed_coral_l3',
        'teleop_missed_coral_l3_sum': 'total_teleop_missed_coral_l3',
        'teleop_missed_coral_l4_mean': 'avg_teleop_missed_coral_l4',
        'teleop_missed_coral_l4_sum': 'total_teleop_missed_coral_l4',
        'auto_algae_processor_mean': 'avg_auto_algae_processor',
        'auto_algae_processor_sum': 'total_auto_algae_processor',
        'teleop_algae_processor_mean': 'avg_teleop_algae_processor',
        'teleop_algae_processor_sum': 'total_teleop_algae_processor',
        'auto_algae_barge_mean': 'avg_auto_algae_barge',
        'auto_algae_barge_sum': 'total_auto_algae_barge',
        'teleop_algae_barge_mean': 'avg_teleop_algae_barge',
        'teleop_algae_barge_sum': 'total_teleop_algae_barge',
        'auto_missed_algae_barge_mean': 'avg_auto_missed_algae_barge',
        'auto_missed_algae_barge_sum': 'total_auto_missed_algae_barge',
        'teleop_missed_algae_barge_mean': 'avg_teleop_missed_algae_barge',
        'teleop_missed_algae_barge_sum': 'total_teleop_missed_algae_barge',
        'auto_missed_algae_processor_mean': 'avg_auto_missed_algae_processor',
        'auto_missed_algae_processor_sum': 'total_auto_missed_algae_processor',
        'teleop_missed_algae_processor_mean': 'avg_teleop_missed_algae_processor',
        'teleop_missed_algae_processor_sum': 'total_teleop_missed_algae_processor',
        'auto_algae_removed_mean': 'avg_auto_algae_removed',
        'auto_algae_removed_sum': 'total_auto_algae_removed',
        'teleop_algae_removed_mean': 'avg_teleop_algae_removed',
        'teleop_algae_removed_sum': 'total_teleop_algae_removed',
        'auto_coral_success_ratio_mean': 'avg_auto_coral_success_ratio',
        'teleop_coral_success_ratio_mean': 'avg_teleop_coral_success_ratio',
        'auto_algae_success_ratio_mean': 'avg_auto_algae_success_ratio',
        'teleop_algae_success_ratio_mean': 'avg_teleop_algae_success_ratio',
        'defense_rating_mean': 'avg_defense_rating',
        'speed_rating_mean': 'avg_speed_rating',
        'driver_skill_rating_mean': 'avg_driver_skill_rating'
    })

    team_stats = team_stats.fillna(0)

    team_stats['total_auto_objects_scored'] = (
        team_stats['total_auto_coral_success'] +
        team_stats['total_auto_algae_barge'] +
        team_stats['total_auto_algae_processor']
    )
    team_stats['total_teleop_objects_scored'] = (
        team_stats['total_teleop_coral_success'] +
        team_stats['total_teleop_algae_barge'] +
        team_stats['total_teleop_algae_processor']
    )
    team_stats['total_objects_scored'] = (
        team_stats['total_auto_objects_scored'] +
        team_stats['total_teleop_objects_scored']
    )

    # Check for duplicates in team_data
    team_duplicates = team_data[team_data.duplicated(subset=['match_number'], keep=False)]
    if not team_duplicates.empty:
        st.warning(f"Duplicate match numbers found for Team {selected_team}:")
        st.write(team_duplicates[['match_number', 'alliance_color', 'total_score']])

    # Clean climb_status data
    team_data['climb_status'] = team_data['climb_status'].str.title()
    team_data['climb_category'] = team_data['climb_status'].map({
        'Shallow Climb': 'Shallow Climb',
        'Deep Climb': 'Deep Climb',
        'None': 'No Climb',
        'Parked': 'No Climb'
    }).fillna('No Climb')

    climb_stats = team_data.groupby('team_number')['climb_category'].value_counts(normalize=True).unstack(fill_value=0) * 100
    climb_stats = climb_stats.reset_index()
    for status in ['Shallow Climb', 'Deep Climb', 'No Climb']:
        if status not in climb_stats.columns:
            climb_stats[status] = 0

    win_loss_data = team_data.drop_duplicates(subset=['match_number'])
    win_loss = win_loss_data.groupby('team_number')['match_outcome_final'].value_counts().unstack(fill_value=0).reset_index()
    win_loss = win_loss.rename(columns={'Won': 'Wins', 'Lost': 'Losses', 'Tie': 'Ties'})
    if 'Wins' not in win_loss.columns:
        win_loss['Wins'] = 0
    if 'Losses' not in win_loss.columns:
        win_loss['Losses'] = 0
    if 'Ties' not in win_loss.columns:
        win_loss['Ties'] = 0

    if 'primary_role' in team_data.columns:
        role_distribution = team_data.groupby('team_number')['primary_role'].value_counts(normalize=True).unstack(fill_value=0) * 100
        role_distribution = role_distribution.reset_index()
        for role in ['Offense', 'Defense', 'Both', 'Neither']:
            if role not in role_distribution.columns:
                role_distribution[role] = 0
    else:
        role_distribution = pd.DataFrame({'team_number': [selected_team], 'Offense': [0], 'Defense': [0], 'Both': [0], 'Neither': [0]})
else:
    # Initialize default stats for teams without match data
    climb_stats = pd.DataFrame({'team_number': [selected_team], 'Shallow Climb': [0], 'Deep Climb': [0], 'No Climb': [0]})
    win_loss = pd.DataFrame({'team_number': [selected_team], 'Wins': [0], 'Losses': [0], 'Ties': [0]})
    role_distribution = pd.DataFrame({'team_number': [selected_team], 'Offense': [0], 'Defense': [0], 'Both': [0], 'Neither': [0]})

# Fetch team data from The Blue Alliance API
TBA_AUTH_KEY = get_tba_api_key()
team_info = fetch_team_data(selected_team, TBA_AUTH_KEY)

# Get robot image from pit scouting data
robot_image_url = None
if not team_pit_data.empty and 'robot_photo_url' in team_pit_data.columns and team_pit_data['robot_photo_url'].notna().any():
    photos = team_pit_data['robot_photo_url'].dropna().tolist()
    photos = [url for url in photos if url and url != '' and isinstance(url, str) and url.startswith(('http://', 'https://'))]
    robot_image_url = photos[0] if photos else None

# Team Profile Card
st.markdown(f"""
    <div class="team-card">
        {"<img src='" + robot_image_url + "' alt='Robot Image'>" if robot_image_url else "<div style='width: 150px; height: 150px; background-color: #ddd; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #888;'>No Image</div>"}
        <div>
            <h2>Team {team_info['team_number']}: {team_info['nickname']}</h2>
            <p><strong>Full Name:</strong> {team_info['name']}</p>
            <p><strong>Location:</strong> {team_info['location']}</p>
            <p><strong>Rookie Year:</strong> {team_info['rookie_year']}</p>
            <p><strong>Motto:</strong> {team_info['motto']}</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Tabs for Match and Pit Scouting
match_tab, pit_tab = st.tabs(["Match Scouting", "Pit Scouting"])

# Match Scouting Tab
with match_tab:
    if team_data.empty:
        st.info(f"No match scouting data available for Team {selected_team}.")
    else:
        # Summary Cards
        st.subheader("Key Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="stat-card">
                    <h4>Avg Total Score</h4>
                    <p>{team_stats['avg_total_score'].iloc[0]:.2f}</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="stat-card">
                    <h4>Wins / Losses / Ties</h4>
                    <p>{win_loss['Wins'].iloc[0]} / {win_loss['Losses'].iloc[0]} / {win_loss['Ties'].iloc[0]}</p>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="stat-card">
                    <h4>Total Objects Scored</h4>
                    <p>{team_stats['total_objects_scored'].iloc[0]:.0f}</p>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
                <div class="stat-card">
                    <h4>Avg Driver Skill</h4>
                    <p>{team_stats['avg_driver_skill_rating'].iloc[0]:.1f}</p>
                </div>
            """, unsafe_allow_html=True)

        # Charts Section
        st.subheader("Performance Charts")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("#### Climb Distribution")
            climb_data = climb_stats.melt(id_vars=['team_number'], value_vars=['Shallow Climb', 'Deep Climb', 'No Climb'],
                                          var_name='Climb Status', value_name='Percentage')
            if climb_data['Percentage'].sum() > 0:
                fig_climb = px.pie(
                    climb_data,
                    names='Climb Status',
                    values='Percentage',
                    title=f"Climb Distribution",
                    hole=0.3
                )
                fig_climb.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_climb, use_container_width=True)
            else:
                st.write("No climb data available.")

        with col2:
            st.markdown("#### Strategy Distribution")
            role_data = role_distribution.melt(id_vars=['team_number'], value_vars=['Offense', 'Defense', 'Both', 'Neither'],
                                               var_name='Primary Role', value_name='Percentage')
            if role_data['Percentage'].sum() > 0:
                fig_role = px.pie(
                    role_data,
                    names='Primary Role',
                    values='Percentage',
                    title=f"Strategy Distribution",
                    hole=0.3
                )
                fig_role.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_role, use_container_width=True)
            else:
                st.write("No strategy data available.")

        with col3:
            st.markdown("#### Team Ratings")
            categories = ['Defense', 'Speed', 'Driver Skill', 'Defense']
            values = [
                team_stats['avg_defense_rating'].iloc[0],
                team_stats['avg_speed_rating'].iloc[0],
                team_stats['avg_driver_skill_rating'].iloc[0],
                team_stats['avg_defense_rating'].iloc[0]
            ]
            if sum(values[:-1]) > 0:
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name=f'Team {selected_team}',
                    line=dict(color='deepskyblue'),
                    fillcolor='rgba(0, 191, 255, 0.3)'
                ))
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 5],
                            tickvals=[1, 2, 3, 4, 5]
                        )
                    ),
                    showlegend=False,
                    title=f"Performance Ratings",
                    margin=dict(l=50, r=50, t=50, b=50)
                )
                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.write("No rating data available.")

        # Performance Over Matches
        st.subheader("Performance Over Matches")
        team_data = team_data.copy()
        team_data['match_number'] = pd.to_numeric(team_data['match_number'], errors='coerce')
        team_data = team_data.sort_values('match_number')
        fig = px.line(
            team_data,
            x='match_number',
            y='total_score',
            title=f"Total Score per Match",
            labels={'match_number': 'Match Number', 'total_score': 'Total Score'}
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed Statistics
        st.subheader("Detailed Statistics")
        
        # Scoring Statistics
        st.markdown('<div class="stat-section">', unsafe_allow_html=True)
        st.markdown("#### Scoring Overview", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<p class="stat-item auto-stat">Avg Auto Score: {team_stats["avg_auto_score"].iloc[0]:.2f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Total Auto Objects: {team_stats["total_auto_objects_scored"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<p class="stat-item teleop-stat">Avg Teleop Score: {team_stats["avg_teleop_score"].iloc[0]:.2f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Total Teleop Objects: {team_stats["total_teleop_objects_scored"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<p class="stat-item">Avg Endgame Score: {team_stats["avg_endgame_score"].iloc[0]:.2f}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Coral Statistics
        st.markdown('<div class="stat-section">', unsafe_allow_html=True)
        st.markdown("#### Coral Statistics", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Autonomous Coral**", unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Avg Scored: {team_stats["avg_auto_coral_success"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Total Scored: {team_stats["total_auto_coral_success"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Avg Missed: {team_stats["avg_auto_coral_missed"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Total Missed: {team_stats["total_auto_coral_missed"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item highlight">Success Ratio: {team_stats["avg_auto_coral_success_ratio"].iloc[0]*100:.1f}%</p>', unsafe_allow_html=True)
            st.markdown("**Auto Coral Per-Level**", unsafe_allow_html=True)
            auto_coral_data = {
                "Level": ["L1", "L2", "L3", "L4"],
                "Avg Scored": [
                    team_stats["avg_auto_coral_l1"].iloc[0],
                    team_stats["avg_auto_coral_l2"].iloc[0],
                    team_stats["avg_auto_coral_l3"].iloc[0],
                    team_stats["avg_auto_coral_l4"].iloc[0]
                ],
                "Total Scored": [
                    team_stats["total_auto_coral_l1"].iloc[0],
                    team_stats["total_auto_coral_l2"].iloc[0],
                    team_stats["total_auto_coral_l3"].iloc[0],
                    team_stats["total_auto_coral_l4"].iloc[0]
                ]
            }
            auto_coral_df = pd.DataFrame(auto_coral_data)
            st.dataframe(auto_coral_df.style.format({"Avg Scored": "{:.1f}", "Total Scored": "{:.0f}"}), use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Teleop Coral**", unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Avg Scored: {team_stats["avg_teleop_coral_success"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Total Scored: {team_stats["total_teleop_coral_success"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Avg Missed: {team_stats["avg_teleop_coral_missed"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Total Missed: {team_stats["total_teleop_coral_missed"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item highlight">Success Ratio: {team_stats["avg_teleop_coral_success_ratio"].iloc[0]*100:.1f}%</p>', unsafe_allow_html=True)
            st.markdown("**Teleop Coral Per-Level**", unsafe_allow_html=True)
            teleop_coral_data = {
                "Level": ["L1", "L2", "L3", "L4"],
                "Avg Scored": [
                    team_stats["avg_teleop_coral_l1"].iloc[0],
                    team_stats["avg_teleop_coral_l2"].iloc[0],
                    team_stats["avg_teleop_coral_l3"].iloc[0],
                    team_stats["avg_teleop_coral_l4"].iloc[0]
                ],
                "Total Scored": [
                    team_stats["total_teleop_coral_l1"].iloc[0],
                    team_stats["total_teleop_coral_l2"].iloc[0],
                    team_stats["total_teleop_coral_l3"].iloc[0],
                    team_stats["total_teleop_coral_l4"].iloc[0]
                ]
            }
            teleop_coral_df = pd.DataFrame(teleop_coral_data)
            st.dataframe(teleop_coral_df.style.format({"Avg Scored": "{:.1f}", "Total Scored": "{:.0f}"}), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Algae Statistics
        st.markdown('<div class="stat-section">', unsafe_allow_html=True)
        st.markdown("#### Algae Statistics", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Autonomous Algae**", unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Avg Scored in Processor: {team_stats["avg_auto_algae_processor"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Total Scored in Processor: {team_stats["total_auto_algae_processor"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Avg Scored in Barge: {team_stats["avg_auto_algae_barge"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Total Scored in Barge: {team_stats["total_auto_algae_barge"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Avg Removed from Reef: {team_stats["avg_auto_algae_removed"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item auto-stat">Total Removed from Reef: {team_stats["total_auto_algae_removed"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item highlight">Success Ratio: {team_stats["avg_auto_algae_success_ratio"].iloc[0]*100:.1f}%</p>', unsafe_allow_html=True)

        with col2:
            st.markdown("**Teleop Algae**", unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Avg Scored in Processor: {team_stats["avg_teleop_algae_processor"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Total Scored in Processor: {team_stats["total_teleop_algae_processor"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Avg Scored in Barge: {team_stats["avg_teleop_algae_barge"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Total Scored in Barge: {team_stats["total_teleop_algae_barge"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Avg Removed from Reef: {team_stats["avg_teleop_algae_removed"].iloc[0]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item teleop-stat">Total Removed from Reef: {team_stats["total_teleop_algae_removed"].iloc[0]:.0f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="stat-item highlight">Success Ratio: {team_stats["avg_teleop_algae_success_ratio"].iloc[0]*100:.1f}%</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Match Comments and Q/A
        st.subheader("Match Comments and Q/A")
        qa_columns = ['match_number', 'alliance_color', 'match_outcome_final', 'defense_qa', 'teleop_qa', 'auto_qa', 'comments']
        missing_cols = [col for col in qa_columns if col not in team_data.columns]
        if missing_cols:
            st.warning(f"The following columns are missing from the match data: {', '.join(missing_cols)}. Cannot display comments and Q/A.")
        else:
            display_df = team_data[qa_columns].copy()
            display_df = display_df.rename(columns={
                'match_number': 'Match Number',
                'alliance_color': 'Alliance Color',
                'match_outcome_final': 'Match Outcome',
                'defense_qa': 'Defense Q/A',
                'teleop_qa': 'Teleop Q/A',
                'auto_qa': 'Autonomous Q/A',
                'comments': 'Additional Comments'
            })
            display_df = display_df.sort_values('Match Number', ascending=False)
            display_df = display_df.fillna("No Information Provided")
            display_df = display_df.replace(
                to_replace=r'(?i)^(nan|no\s*comment(s)?(\s*provided)?|no\s*comm.*)$',
                value="No Information Provided",
                regex=True
            )
            st.dataframe(display_df, use_container_width=True, hide_index=True)

# Pit Scouting Tab
with pit_tab:
    if team_pit_data.empty:
        st.info(f"No pit scouting data available for Team {selected_team}.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Robot Capabilities")
            capability_cols = [
                'can_score_coral_l1', 'can_score_coral_l2', 'can_score_coral_l3', 'can_score_coral_l4',
                'can_score_algae_barge', 'can_score_algae_processor', 'can_remove_algae_l1', 'can_remove_algae_l2'
            ]
            available_capabilities = [col for col in capability_cols if col in team_pit_data.columns]
            if available_capabilities:
                capabilities = team_pit_data[available_capabilities].mean() * 100
                for cap in available_capabilities:
                    cap_name = cap.replace('can_', '').replace('_', ' ').title()
                    st.markdown(f"- **{cap_name}:** {'Yes' if capabilities[cap] > 0 else 'No'}")
            else:
                st.write("No capability data available.")

        with col2:
            st.markdown("#### Robot Characteristics")
            characteristics = []
            if 'drivetrain_type' in team_pit_data.columns:
                drivetrain = team_pit_data['drivetrain_type'].mode()[0] if not team_pit_data['drivetrain_type'].mode().empty else "Unknown"
                characteristics.append(f"- **Drivetrain Type:** {drivetrain}")
            if 'preferred_role' in team_pit_data.columns:
                preferred_role = team_pit_data['preferred_role'].mode()[0] if not team_pit_data['preferred_role'].mode().empty else "Unknown"
                characteristics.append(f"- **Preferred Role:** {preferred_role}")
            if 'endgame_capability' in team_pit_data.columns:
                endgame_cap = team_pit_data['endgame_capability'].mode()[0] if not team_pit_data['endgame_capability'].mode().empty else "Unknown"
                characteristics.append(f"- **Endgame Capability:** {endgame_cap}")
            if 'auto_strategy' in team_pit_data.columns:
                auto_strategy = team_pit_data['auto_strategy'].mode()[0] if not team_pit_data['auto_strategy'].mode().empty else "Unknown"
                characteristics.append(f"- **Autonomous Strategy:** {auto_strategy}")
            for char in characteristics:
                st.markdown(char)

        st.markdown("#### Robot Strengths, Weaknesses, and Notes")
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Strengths and Weaknesses**")
            if 'robot_strengths' in team_pit_data.columns:
                strengths = team_pit_data['robot_strengths'].dropna().tolist()
                st.markdown(f"- **Strengths:** {', '.join(strengths) if strengths else 'Not Provided'}")
            if 'robot_weaknesses' in team_pit_data.columns:
                weaknesses = team_pit_data['robot_weaknesses'].dropna().tolist()
                st.markdown(f"- **Weaknesses:** {', '.join(weaknesses) if weaknesses else 'Not Provided'}")

        with col4:
            st.markdown("**Team Comments and Scouter Notes**")
            if 'team_comments' in team_pit_data.columns and 'scouter_notes' in team_pit_data.columns:
                comments_data = team_pit_data[['team_comments', 'scouter_notes']].drop_duplicates()
                comments_data = comments_data.fillna("No Information Provided")
                comments_data = comments_data.replace(
                    to_replace=r'(?i)^(nan|no\s*comment(s)?(\s*provided)?|no\s*comm.*)$',
                    value="No Information Provided",
                    regex=True
                )
                for idx, row in comments_data.iterrows():
                    st.markdown(f"- **Team Comments (Entry {idx+1}):** {row['team_comments']}")
                    st.markdown(f"- **Scouter Notes (Entry {idx+1}):** {row['scouter_notes']}")
            else:
                st.write("No comments or notes available.")

        st.markdown("#### Robot Photos")
        if 'robot_photo_url' in team_pit_data.columns and team_pit_data['robot_photo_url'].notna().any():
            photos = team_pit_data['robot_photo_url'].dropna().tolist()
            photos = [url for url in photos if url and url != '' and isinstance(url, str) and url.startswith(('http://', 'https://'))]
            if photos:
                st.markdown('<div class="photo-gallery">', unsafe_allow_html=True)
                for idx, photo_url in enumerate(photos):
                    try:
                        st.markdown(f'<img src="{photo_url}" alt="Team {selected_team} Pit Photo {idx + 1}">', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Failed to load photo (Photo {idx + 1}): {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.write("No robot photos available.")
        else:
            st.write("No robot photos available.")