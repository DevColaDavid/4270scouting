import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests  # Added for checking image URL accessibility
from utils.utils import load_data, calculate_match_score
from utils.utils import setup_sidebar_navigation
from firebase_admin import firestore  # Added for fetching pit data

# Initialize Firestore client
db = firestore.client()

# Constants (adjust these to match your setup)
PIT_SCOUT_COLLECTION = "pit_scout_data"  # Same as in 7_Data_Management.py

st.set_page_config(page_title="Match Prediction", page_icon="📉", layout="wide", initial_sidebar_state="collapsed")

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in to access this page.")
    st.stop()

# Set up the sidebar navigation
setup_sidebar_navigation()

# Page content
st.title("Match Prediction")
st.write("This is the Match Prediction page.")

st.title("📉 Match Prediction")
st.markdown("Predict the outcome of a match based on historical scouting data.")

# Load match data with error handling
try:
    df = load_data()
except Exception as e:
    st.error(f"Failed to load data: {str(e)}")
    st.stop()

# Check if data is empty or None
if df is None or df.empty:
    st.info("No match data available for prediction. Please upload data in the Data Upload page.")
    st.stop()

# Ensure numeric columns are properly typed
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
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Convert team_number to string to ensure consistency
if 'team_number' in df.columns:
    df['team_number'] = df['team_number'].astype(str)
else:
    st.error("Required column 'team_number' is missing in the data.")
    st.stop()

# Define required columns for scoring
required_cols = [
    'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
    'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
    'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
    'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
    'auto_taxi_left', 'climb_status', 'match_number', 'alliance_color'
]

# Calculate match scores and alliance bonuses
score_columns = ['auto_score', 'teleop_score', 'endgame_score', 'total_score']
if all(col in df.columns for col in required_cols):
    # Only calculate scores if they don't already exist
    if not all(col in df.columns for col in score_columns):
        scores = df.apply(calculate_match_score, axis=1)
        df[score_columns] = scores

    # Calculate alliance-level bonuses
    def calculate_alliance_bonuses(df):
        # Ensure match_number and alliance_color are in the correct format
        if 'match_number' in df.columns and 'alliance_color' in df.columns:
            # Handle NaN values and ensure match_number is a string
            df['match_number'] = df['match_number'].astype(str)
            # Standardize alliance_color (e.g., to lowercase)
            df['alliance_color'] = df['alliance_color'].fillna('unknown').str.lower()
        else:
            df['coop_bonus'] = 0
            df['harmony_bonus'] = 0
            return df

        # Co-op Bonus: 15 points if alliance scores 5 coral on at least 3 levels
        coral_cols = [
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4'
        ]
        # Ensure all coral columns exist; fill missing ones with 0
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

        # Ensure merge keys are consistent
        alliance_coral['match_number'] = alliance_coral['match_number'].astype(str)
        alliance_coral['alliance_color'] = alliance_coral['alliance_color'].str.lower()

        # Merge coop_bonus into df
        df = df.merge(
            alliance_coral[['match_number', 'alliance_color', 'coop_bonus']],
            on=['match_number', 'alliance_color'],
            how='left'
        )

        # Ensure coop_bonus exists, even if merge fails
        if 'coop_bonus' not in df.columns:
            df['coop_bonus'] = 0

        # Harmony Bonus: 15 points if all robots in the alliance climb (Shallow or Deep)
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

        # Reset the index to convert match_number and alliance_color to columns
        alliance_climb = alliance_climb.reset_index()

        # Standardize the columns after resetting the index
        alliance_climb['match_number'] = alliance_climb['match_number'].astype(str)
        alliance_climb['alliance_color'] = alliance_climb['alliance_color'].str.lower()

        # Merge harmony_bonus into df
        df = df.merge(
            alliance_climb[['match_number', 'alliance_color', 'harmony_bonus']],
            on=['match_number', 'alliance_color'],
            how='left'
        )

        # Ensure harmony_bonus exists, even if merge fails
        if 'harmony_bonus' not in df.columns:
            df['harmony_bonus'] = 0

        # Add bonuses to total score
        df['total_score'] = (
            df['total_score'] +
            df['coop_bonus'].fillna(0) +
            df['harmony_bonus'].fillna(0)
        )

        return df

    df = calculate_alliance_bonuses(df)

    # Calculate EPA (Expected Points Added)
    def calculate_epa(df):
        if 'match_number' in df.columns and 'alliance_color' in df.columns:
            # Ensure consistent types for grouping
            df['match_number'] = df['match_number'].astype(str)
            df['alliance_color'] = df['alliance_color'].str.lower()
            alliance_avg = df.groupby(['match_number', 'alliance_color'])['total_score'].mean().reset_index()
            alliance_avg = alliance_avg.rename(columns={'total_score': 'alliance_avg'})
            # Merge the average back into the original DataFrame
            alliance_avg['match_number'] = alliance_avg['match_number'].astype(str)
            alliance_avg['alliance_color'] = alliance_avg['alliance_color'].str.lower()
            df = df.merge(alliance_avg, on=['match_number', 'alliance_color'], how='left')
            # Calculate EPA as team score minus alliance average
            df['epa'] = df['total_score'] - df['alliance_avg']
            # Drop the temporary column
            df = df.drop(columns=['alliance_avg'])
        else:
            df['epa'] = 0
        return df

    df = calculate_epa(df)
else:
    st.warning("Cannot calculate match scores. Missing required columns: " +
               ", ".join([col for col in required_cols if col not in df.columns]))
    st.stop()

# Calculate success ratios for prediction adjustment
df['auto_coral_success'] = df['auto_coral_l1'] + df['auto_coral_l2'] + df['auto_coral_l3'] + df['auto_coral_l4']
df['auto_coral_missed'] = df['auto_missed_coral_l1'] + df['auto_missed_coral_l2'] + df['auto_missed_coral_l3'] + df['auto_missed_coral_l4']
df['teleop_coral_success'] = df['teleop_coral_l1'] + df['teleop_coral_l2'] + df['teleop_coral_l3'] + df['teleop_coral_l4']
df['teleop_coral_missed'] = df['teleop_missed_coral_l1'] + df['teleop_missed_coral_l2'] + df['teleop_missed_coral_l3'] + df['teleop_missed_coral_l4']
df['auto_coral_attempts'] = df['auto_coral_success'] + df['auto_coral_missed']
df['teleop_coral_attempts'] = df['teleop_coral_success'] + df['teleop_coral_missed']
df['auto_coral_success_ratio'] = (df['auto_coral_success'] / df['auto_coral_attempts'].replace(0, pd.NA)).fillna(0)
df['teleop_coral_success_ratio'] = (df['teleop_coral_success'] / df['teleop_coral_attempts'].replace(0, pd.NA)).fillna(0)

df['auto_algae_success'] = df['auto_algae_barge'] + df['auto_algae_processor']
df['auto_algae_missed'] = df['auto_missed_algae_barge'] + df['auto_missed_algae_processor']
df['teleop_algae_success'] = df['teleop_algae_barge'] + df['teleop_algae_processor']
df['teleop_algae_missed'] = df['teleop_missed_algae_barge'] + df['teleop_missed_algae_processor']
df['auto_algae_attempts'] = df['auto_algae_success'] + df['auto_algae_missed']
df['teleop_algae_attempts'] = df['teleop_algae_success'] + df['teleop_algae_missed']
df['auto_algae_success_ratio'] = (df['auto_algae_success'] / df['auto_algae_attempts'].replace(0, pd.NA)).fillna(0)
df['teleop_algae_success_ratio'] = (df['teleop_algae_success'] / df['teleop_algae_attempts'].replace(0, pd.NA)).fillna(0)

# Team selection for prediction
# Define default values to avoid NameError
red_alliance_teams = []
blue_alliance_teams = []

if 'team_number' in df.columns:
    # Use all teams with any data
    team_numbers = sorted(df['team_number'].unique())
    st.subheader("Select Teams for the Match")
    col1, col2 = st.columns(2)
    with col1:
        red_alliance_teams = st.multiselect("Select Red Alliance Teams (up to 3)", options=team_numbers, max_selections=3)
    with col2:
        blue_alliance_teams = st.multiselect("Select Blue Alliance Teams (up to 3)", options=team_numbers, max_selections=3)

    # Validate that no team is selected for both alliances
    overlapping_teams = set(red_alliance_teams).intersection(set(blue_alliance_teams))
    if overlapping_teams:
        st.error(f"The following teams are selected for both alliances: {', '.join(overlapping_teams)}. Please select unique teams for each alliance.")
        st.stop()
else:
    st.error("Team number column not found in data.")
    st.stop()

# Fetch pit scouting data to get robot photos
# Modified from fetch_pit_data in 7_Data_Management.py, simplified for this page
def fetch_team_photos():
    try:
        docs = db.collection(PIT_SCOUT_COLLECTION)\
                 .select(['team_number', 'robot_photo_url', 'timestamp'])\
                 .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                 .get()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['team_number'] = str(doc_data.get('team_number', ''))  # Ensure team_number is a string
            data.append(doc_data)
        pit_df = pd.DataFrame(data)
        if not pit_df.empty:
            # Keep the most recent record per team (based on timestamp)
            pit_df = pit_df.sort_values('timestamp', ascending=False).drop_duplicates('team_number', keep='first')
        return pit_df
    except Exception as e:
        st.error(f"Error fetching pit scouting data for robot photos: {e}")
        return pd.DataFrame()

# Load pit data for photos
pit_data = fetch_team_photos()
team_photos = {}
if not pit_data.empty:
    for _, row in pit_data.iterrows():
        team_photos[row['team_number']] = row.get('robot_photo_url', None)

# Prediction logic
if red_alliance_teams and blue_alliance_teams:
    def calculate_alliance_score(team_metrics, metric='total_score'):
        if not team_metrics:
            return 0.0, 0.0
        # Use the specified metric (default to 'total_score')
        scores = [metrics[metric] for metrics in team_metrics]
        std_devs = [metrics[f'{metric}_std'] for metrics in team_metrics]
        # Apply weights to the top teams (1.0, 0.8, 0.6)
        weights = np.array([1.0, 0.8, 0.6])[:len(scores)]
        weighted_scores = [
            score * weight for score, weight in zip(sorted(scores, reverse=True), weights)
        ]
        # Sum the weighted scores to get the total alliance score
        total_score = sum(weighted_scores)
        # Calculate weighted standard deviation for confidence interval
        weighted_std = np.sqrt(sum((std * weight) ** 2 for std, weight in zip(sorted(std_devs, reverse=True), weights)))
        return total_score, weighted_std

    def estimate_alliance_bonuses(data, alliance_teams, full_data):
        if not alliance_teams:
            return 0.0
        
        # Calculate climb probability for Harmony bonus
        climb_stats = full_data.groupby('team_number')['climb_status'].value_counts(normalize=True).unstack(fill_value=0)
        climb_stats['climb_prob'] = climb_stats.get('Shallow Climb', 0) + climb_stats.get('Deep Climb', 0)
        
        # Ensure alliance_teams are strings to match df['team_number']
        alliance_teams = [str(team) for team in alliance_teams]
        
        # Check for missing teams
        missing_teams = [team for team in alliance_teams if team not in climb_stats.index]
        if missing_teams:
            present_teams = [team for team in alliance_teams if team in climb_stats.index]
            harmony_bonus_prob = climb_stats.loc[present_teams, 'climb_prob'].prod() if present_teams else 0
        else:
            harmony_bonus_prob = climb_stats.loc[alliance_teams, 'climb_prob'].prod()

        # Calculate co-op bonus probability
        coral_cols = [
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4'
        ]
        team_coral = data.groupby('team_number')[coral_cols].mean()
        team_coral['l1_total'] = team_coral['auto_coral_l1'] + team_coral['teleop_coral_l1']
        team_coral['l2_total'] = team_coral['auto_coral_l2'] + team_coral['teleop_coral_l2']
        team_coral['l3_total'] = team_coral['auto_coral_l3'] + team_coral['teleop_coral_l3']
        team_coral['l4_total'] = team_coral['auto_coral_l4'] + team_coral['teleop_coral_l4']
        if not team_coral.empty and team_coral.index.isin(alliance_teams).any():
            avg_coral_per_level = team_coral.loc[team_coral.index.isin(alliance_teams), ['l1_total', 'l2_total', 'l3_total', 'l4_total']].sum()
            levels_with_5_plus = (avg_coral_per_level >= 5).sum()
            coop_bonus_prob = min(1.0, levels_with_5_plus / 3)
        else:
            coop_bonus_prob = 0

        expected_bonus = (coop_bonus_prob * 15) + (harmony_bonus_prob * 15)
        return max(expected_bonus, 0.0)

    # Calculate team metrics (EPA, total_score, and their standard deviations)
    team_metrics = df.groupby('team_number').agg({
        'epa': ['mean', 'std'],
        'total_score': ['mean', 'std'],
        'auto_score': 'mean',
        'teleop_score': 'mean',
        'endgame_score': 'mean',
        'teleop_coral_success_ratio': 'mean',
        'teleop_algae_success_ratio': 'mean',
        'climb_status': lambda x: ((x == 'Shallow Climb') | (x == 'Deep Climb')).mean()  # Keep as a proportion (0 to 1)
    }).reset_index()

    # Flatten the multi-index columns
    team_metrics.columns = [
        'team_number', 'epa', 'epa_std', 'total_score', 'total_score_std',
        'auto_score', 'teleop_score', 'endgame_score',
        'teleop_coral_success_ratio', 'teleop_algae_success_ratio', 'climb_rate'
    ]
    team_metrics = team_metrics.fillna({'epa': 0, 'epa_std': 0, 'total_score': 0, 'total_score_std': 0})

    # Prepare metrics for each team in the alliances
    red_team_metrics = []
    blue_team_metrics = []
    insufficient_data_teams = []

    for team in red_alliance_teams:
        team_data = team_metrics[team_metrics['team_number'] == team]
        if team_data.empty or team_data['total_score'].iloc[0] == 0:
            insufficient_data_teams.append(f"Red Team {team}")
            red_team_metrics.append({'epa': 0, 'epa_std': 0, 'total_score': 0, 'total_score_std': 0})
        else:
            red_team_metrics.append(team_data.iloc[0].to_dict())

    for team in blue_alliance_teams:
        team_data = team_metrics[team_metrics['team_number'] == team]
        if team_data.empty or team_data['total_score'].iloc[0] == 0:
            insufficient_data_teams.append(f"Blue Team {team}")
            blue_team_metrics.append({'epa': 0, 'epa_std': 0, 'total_score': 0, 'total_score_std': 0})
        else:
            blue_team_metrics.append(team_data.iloc[0].to_dict())

    # Display warning for teams with insufficient data
    if insufficient_data_teams:
        st.warning(f"Insufficient data for the following teams: {', '.join(insufficient_data_teams)}. Predictions may be inaccurate.")

    # Calculate alliance scores using total_score (average match score per team)
    red_score, red_std = calculate_alliance_score(red_team_metrics, metric='total_score')
    blue_score, blue_std = calculate_alliance_score(blue_team_metrics, metric='total_score')

    # Since total_score in team_metrics is the average per match for each team,
    # the sum of weighted scores is already the expected total alliance score
    # (no need to multiply by the number of teams, as we're summing contributions)

    # Split data by alliance for bonus estimation
    red_data = df[df['team_number'].isin(red_alliance_teams)]
    blue_data = df[df['team_number'].isin(blue_alliance_teams)]

    # Estimate alliance bonuses
    red_bonus = estimate_alliance_bonuses(red_data, red_alliance_teams, df)
    blue_bonus = estimate_alliance_bonuses(blue_data, blue_alliance_teams, df)

    # Add bonuses to predicted total alliance scores
    red_total_score = max(red_score + red_bonus, 0.0)
    blue_total_score = max(blue_score + blue_bonus, 0.0)

    # Calculate confidence intervals (approximate 95% CI: mean ± 1.96 * std)
    red_ci_lower = max(red_total_score - 1.96 * red_std, 0.0)
    red_ci_upper = red_total_score + 1.96 * red_std
    blue_ci_lower = max(blue_total_score - 1.96 * blue_std, 0.0)
    blue_ci_upper = blue_total_score + 1.96 * blue_std

    # Calculate win probability using a logistic function based on score difference
    score_diff = red_total_score - blue_total_score
    # Logistic function: P = 1 / (1 + exp(-k * (score_diff)))
    k = 0.1  # Sensitivity parameter (adjustable)
    red_win_prob = 100 / (1 + np.exp(-k * score_diff))
    blue_win_prob = 100 - red_win_prob

    # Display prediction with robot images in a horizontal layout using Streamlit-native borders
    st.subheader("Match Prediction")

    # Create two columns for Red and Blue Alliances to group the teams
    col_red, col_blue = st.columns([1, 1], gap="medium")

    # Minimal CSS for border colors and subtle background tints
    st.markdown(
        """
        <style>
        /* Set border color for Red Alliance */
        div[data-testid="stVerticalBlockBorderWrapper"][data-border-color="red"] > div {
            border-color: red !important;
        }
        /* Set border color for Blue Alliance */
        div[data-testid="stVerticalBlockBorderWrapper"][data-border-color="blue"] > div {
            border-color: blue !important;
        }
        /* Subtle background tints */
        .red-background {
            background-color: rgba(255, 0, 0, 0.6);
            padding: 10px;
            border-radius: 5px;
        }
        .blue-background {
            background-color: rgba(0, 0, 255, 0.6);
            padding: 10px;
            border-radius: 5px;
        }
        .team-box {
            text-align: center;
            margin: 0 5px; /* Small margin between team boxes */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Red Alliance Teams
    with col_red:
        # Use Streamlit container with border=True for the surrounding border
        with st.container(border=True):
            # Set a custom attribute to identify this container for CSS styling
            st.markdown('<div data-border-color="red" class="red-background">', unsafe_allow_html=True)
            st.markdown("### Red Alliance")
            team_cols = st.columns(3)  # 3 columns for Red Alliance teams
            for idx, team in enumerate(red_alliance_teams):
                with team_cols[idx]:
                    st.markdown('<div class="team-box">', unsafe_allow_html=True)
                    st.markdown(f"**Team {team}**", unsafe_allow_html=True)
                    photo_url = team_photos.get(team, None)
                    if photo_url and isinstance(photo_url, str) and photo_url.strip():
                        try:
                            # Check if the URL is accessible
                            response = requests.head(photo_url, timeout=5)
                            if response.status_code == 200:
                                st.image(photo_url, caption=f"Team {team}", width=150)
                            else:
                                st.markdown(
                                    '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                                    'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                                    'No Image</div>',
                                    unsafe_allow_html=True
                                )
                        except requests.exceptions.RequestException as e:
                            st.markdown(
                                '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                                'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                                'No Image</div>',
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.markdown(
                                '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                                'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                                'No Image</div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                            'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                            'No Image</div>',
                            unsafe_allow_html=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Blue Alliance Teams
    with col_blue:
        # Use Streamlit container with border=True for the surrounding border
        with st.container(border=True):
            # Set a custom attribute to identify this container for CSS styling
            st.markdown('<div data-border-color="blue" class="blue-background">', unsafe_allow_html=True)
            st.markdown("### Blue Alliance")
            team_cols = st.columns(3)  # 3 columns for Blue Alliance teams
            for idx, team in enumerate(blue_alliance_teams):
                with team_cols[idx]:
                    st.markdown('<div class="team-box">', unsafe_allow_html=True)
                    st.markdown(f"**Team {team}**", unsafe_allow_html=True)
                    photo_url = team_photos.get(team, None)
                    if photo_url and isinstance(photo_url, str) and photo_url.strip():
                        try:
                            # Check if the URL is accessible
                            response = requests.head(photo_url, timeout=5)
                            if response.status_code == 200:
                                st.image(photo_url, caption=f"Team {team}", width=150)
                            else:
                                st.markdown(
                                    '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                                    'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                                    'No Image</div>',
                                    unsafe_allow_html=True
                                )
                        except requests.exceptions.RequestException as e:
                            st.markdown(
                                '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                                'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                                'No Image</div>',
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.markdown(
                                '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                                'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                                'No Image</div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            '<div style="width: 150px; height: 150px; background-color: #333; color: white; '
                            'display: flex; align-items: center; justify-content: center; border-radius: 5px;">'
                            'No Image</div>',
                            unsafe_allow_html=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Display the predicted scores and win probabilities below the images
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Red Alliance")
        st.metric("Red Alliance Total Predicted Score", f"{red_total_score:.2f}", f"95% CI: [{red_ci_lower:.2f}, {red_ci_upper:.2f}]")
        st.metric("Red Alliance Win Probability", f"{red_win_prob:.1f}%")

    with col2:
        st.markdown("### Blue Alliance")
        st.metric("Blue Alliance Total Predicted Score", f"{blue_total_score:.2f}", f"95% CI: [{blue_ci_lower:.2f}, {blue_ci_upper:.2f}]")
        st.metric("Blue Alliance Win Probability", f"{blue_win_prob:.1f}%")

    # Determine winner
    if red_total_score > blue_total_score:
        st.success(f"Red Alliance is predicted to win by {red_total_score - blue_total_score:.2f} points!")
    elif blue_total_score > red_total_score:
        st.success(f"Blue Alliance is predicted to win by {blue_total_score - red_total_score:.2f} points!")
    else:
        st.info("The match is predicted to be a tie!")

    # Calculate key metrics for each alliance
    if not red_data.empty:
        red_metrics = red_data.groupby('team_number').agg({
            'total_score': 'mean',
            'auto_score': 'mean',
            'teleop_score': 'mean',
            'endgame_score': 'mean',
            'teleop_coral_success_ratio': 'mean',  # Already a proportion (0 to 1)
            'teleop_algae_success_ratio': 'mean',  # Already a proportion (0 to 1)
            'climb_status': lambda x: ((x == 'Shallow Climb') | (x == 'Deep Climb')).mean(),  # Proportion (0 to 1)
            'epa': 'mean'
        }).mean()
        # Convert proportions to percentages for display
        red_metrics['teleop_coral_success_ratio'] *= 100
        red_metrics['teleop_algae_success_ratio'] *= 100
        red_metrics['climb_status'] *= 100
    else:
        red_metrics = pd.Series({
            'total_score': np.nan,
            'auto_score': np.nan,
            'teleop_score': np.nan,
            'endgame_score': np.nan,
            'teleop_coral_success_ratio': np.nan,
            'teleop_algae_success_ratio': np.nan,
            'climb_status': np.nan,
            'epa': np.nan
        })

    if not blue_data.empty:
        blue_metrics = blue_data.groupby('team_number').agg({
            'total_score': 'mean',
            'auto_score': 'mean',
            'teleop_score': 'mean',
            'endgame_score': 'mean',
            'teleop_coral_success_ratio': 'mean',  # Already a proportion (0 to 1)
            'teleop_algae_success_ratio': 'mean',  # Already a proportion (0 to 1)
            'climb_status': lambda x: ((x == 'Shallow Climb') | (x == 'Deep Climb')).mean(),  # Proportion (0 to 1)
            'epa': 'mean'
        }).mean()
        # Convert proportions to percentages for display
        blue_metrics['teleop_coral_success_ratio'] *= 100
        blue_metrics['teleop_algae_success_ratio'] *= 100
        blue_metrics['climb_status'] *= 100
    else:
        blue_metrics = pd.Series({
            'total_score': np.nan,
            'auto_score': np.nan,
            'teleop_score': np.nan,
            'endgame_score': np.nan,
            'teleop_coral_success_ratio': np.nan,
            'teleop_algae_success_ratio': np.nan,
            'climb_status': np.nan,
            'epa': np.nan
        })

    # Provide reasons based on data
    st.subheader("Reasons for Prediction")

    # Visualize key metrics comparison
    metrics_to_compare = [
        'epa', 'total_score', 'auto_score', 'teleop_score', 'endgame_score',
        'teleop_coral_success_ratio', 'teleop_algae_success_ratio', 'climb_status'
    ]
    comparison_data = pd.DataFrame({
        'Metric': metrics_to_compare,
        'Red Alliance': [red_metrics[metric] for metric in metrics_to_compare],
        'Blue Alliance': [blue_metrics[metric] for metric in metrics_to_compare]
    })
    # Since percentages are already scaled in red_metrics and blue_metrics, no further adjustment needed here
    comparison_data['Metric'] = comparison_data['Metric'].map({
        'epa': 'EPA',
        'total_score': 'Average Team Score',
        'auto_score': 'Auto Score',
        'teleop_score': 'Teleop Score',
        'endgame_score': 'Endgame Score',
        'teleop_coral_success_ratio': 'Coral Success Ratio (%)',
        'teleop_algae_success_ratio': 'Algae Success Ratio (%)',
        'climb_status': 'Climb Rate (%)'
    })
    comparison_data = comparison_data.melt(id_vars='Metric', var_name='Alliance', value_name='Value')
    # Replace NaN values with 0 for visualization
    comparison_data['Value'] = comparison_data['Value'].fillna(0)
    fig = px.bar(
        comparison_data,
        x='Value',
        y='Metric',
        color='Alliance',
        barmode='group',
        title="Comparison of Red and Blue Alliance Metrics (Per Team Averages)",
        labels={'Value': 'Value', 'Metric': 'Metric'},
        color_discrete_map={'Red Alliance': 'red', 'Blue Alliance': 'blue'}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detailed reasoning
    st.subheader("Key Factors Influencing the Prediction:")
    
    # EPA Comparison
    st.markdown("- **Expected Points Added (EPA)**")
    red_epa = f"{red_metrics['epa']:.2f}" if not pd.isna(red_metrics['epa']) else "N/A"
    blue_epa = f"{blue_metrics['epa']:.2f}" if not pd.isna(blue_metrics['epa']) else "N/A"
    st.markdown(f"  - Red Alliance Avg EPA (per team): {red_epa}")
    st.markdown(f"  - Blue Alliance Avg EPA (per team): {blue_epa}")
    if not pd.isna(red_metrics['epa']) and not pd.isna(blue_metrics['epa']):
        if red_metrics['epa'] > blue_metrics['epa']:
            st.markdown("    - Red Alliance has a higher EPA, indicating a greater contribution to their alliance's score.")
        else:
            st.markdown("    - Blue Alliance has a higher EPA, indicating a greater contribution to their alliance's score.")
    else:
        st.markdown("    - Insufficient data to compare EPA.")

    # Total Score Comparison
    st.markdown("- **Average Team Score**")
    red_team_score = f"{red_metrics['total_score']:.2f}" if not pd.isna(red_metrics['total_score']) else "N/A"
    blue_team_score = f"{blue_metrics['total_score']:.2f}" if not pd.isna(blue_metrics['total_score']) else "N/A"
    st.markdown(f"  - Red Alliance (per team): {red_team_score}")
    st.markdown(f"  - Blue Alliance (per team): {blue_team_score}")
    if not pd.isna(red_metrics['total_score']) and not pd.isna(blue_metrics['total_score']):
        if red_metrics['total_score'] > blue_metrics['total_score']:
            st.markdown("    - Red Alliance teams have a higher average score, contributing to a stronger total alliance score.")
        else:
            st.markdown("    - Blue Alliance teams have a higher average score, contributing to a stronger total alliance score.")
    else:
        st.markdown("    - Insufficient data to compare average team scores.")

    # Autonomous Performance
    st.markdown("- **Autonomous Performance**")
    red_auto_score = f"{red_metrics['auto_score']:.2f}" if not pd.isna(red_metrics['auto_score']) else "N/A"
    blue_auto_score = f"{blue_metrics['auto_score']:.2f}" if not pd.isna(blue_metrics['auto_score']) else "N/A"
    st.markdown(f"  - Red Alliance Avg Auto Score (per team): {red_auto_score}")
    st.markdown(f"  - Blue Alliance Avg Auto Score (per team): {blue_auto_score}")
    if not pd.isna(red_metrics['auto_score']) and not pd.isna(blue_metrics['auto_score']):
        if red_metrics['auto_score'] > blue_metrics['auto_score']:
            st.markdown("    - Red Alliance performs better in autonomous, giving them an early advantage.")
        else:
            st.markdown("    - Blue Alliance performs better in autonomous, giving them an early advantage.")
    else:
        st.markdown("    - Insufficient data to compare autonomous performance.")

    # Teleop Performance
    st.markdown("- **Teleop Performance**")
    red_teleop_score = f"{red_metrics['teleop_score']:.2f}" if not pd.isna(red_metrics['teleop_score']) else "N/A"
    blue_teleop_score = f"{blue_metrics['teleop_score']:.2f}" if not pd.isna(blue_metrics['teleop_score']) else "N/A"
    red_coral_success = f"{red_metrics['teleop_coral_success_ratio']:.1f}" if not pd.isna(red_metrics['teleop_coral_success_ratio']) else "N/A"
    blue_coral_success = f"{blue_metrics['teleop_coral_success_ratio']:.1f}" if not pd.isna(blue_metrics['teleop_coral_success_ratio']) else "N/A"
    red_algae_success = f"{red_metrics['teleop_algae_success_ratio']:.1f}" if not pd.isna(red_metrics['teleop_algae_success_ratio']) else "N/A"
    blue_algae_success = f"{blue_metrics['teleop_algae_success_ratio']:.1f}" if not pd.isna(blue_metrics['teleop_algae_success_ratio']) else "N/A"
    st.markdown(f"  - Red Alliance Avg Teleop Score (per team): {red_teleop_score}")
    st.markdown(f"  - Blue Alliance Avg Teleop Score (per team): {blue_teleop_score}")
    st.markdown(f"  - Red Alliance Coral Success Ratio: {red_coral_success}%")
    st.markdown(f"  - Blue Alliance Coral Success Ratio: {blue_coral_success}%")
    st.markdown(f"  - Red Alliance Algae Success Ratio: {red_algae_success}%")
    st.markdown(f"  - Blue Alliance Algae Success Ratio: {blue_algae_success}%")
    if not pd.isna(red_metrics['teleop_score']) and not pd.isna(blue_metrics['teleop_score']):
        if red_metrics['teleop_score'] > blue_metrics['teleop_score']:
            st.markdown("    - Red Alliance has a stronger teleop performance.")
        else:
            st.markdown("    - Blue Alliance has a stronger teleop performance.")
    else:
        st.markdown("    - Insufficient data to compare teleop performance.")
    if not pd.isna(red_metrics['teleop_coral_success_ratio']) and not pd.isna(blue_metrics['teleop_coral_success_ratio']):
        if red_metrics['teleop_coral_success_ratio'] > blue_metrics['teleop_coral_success_ratio']:
            st.markdown("    - Red Alliance is more accurate in scoring coral during teleop.")
        else:
            st.markdown("    - Blue Alliance is more accurate in scoring coral during teleop.")
    if not pd.isna(red_metrics['teleop_algae_success_ratio']) and not pd.isna(blue_metrics['teleop_algae_success_ratio']):
        if red_metrics['teleop_algae_success_ratio'] > blue_metrics['teleop_algae_success_ratio']:
            st.markdown("    - Red Alliance is more effective at managing algae during teleop.")
        else:
            st.markdown("    - Blue Alliance is more effective at managing algae during teleop.")

    # Endgame Performance
    st.markdown("- **Endgame Performance**")
    red_endgame_score = f"{red_metrics['endgame_score']:.2f}" if not pd.isna(red_metrics['endgame_score']) else "N/A"
    blue_endgame_score = f"{blue_metrics['endgame_score']:.2f}" if not pd.isna(blue_metrics['endgame_score']) else "N/A"
    red_climb_rate = f"{red_metrics['climb_status']:.1f}" if not pd.isna(red_metrics['climb_status']) else "N/A"
    blue_climb_rate = f"{blue_metrics['climb_status']:.1f}" if not pd.isna(blue_metrics['climb_status']) else "N/A"
    st.markdown(f"  - Red Alliance Avg Endgame Score (per team): {red_endgame_score}")
    st.markdown(f"  - Blue Alliance Avg Endgame Score (per team): {blue_endgame_score}")
    st.markdown(f"  - Red Alliance Climb Rate: {red_climb_rate}%")
    st.markdown(f"  - Blue Alliance Climb Rate: {blue_climb_rate}%")
    if not pd.isna(red_metrics['endgame_score']) and not pd.isna(blue_metrics['endgame_score']):
        if red_metrics['endgame_score'] > blue_metrics['endgame_score']:
            st.markdown("    - Red Alliance has a stronger endgame performance.")
        else:
            st.markdown("    - Blue Alliance has a stronger endgame performance.")
    else:
        st.markdown("    - Insufficient data to compare endgame performance.")
    if not pd.isna(red_metrics['climb_status']) and not pd.isna(blue_metrics['climb_status']):
        if red_metrics['climb_status'] > blue_metrics['climb_status']:
            st.markdown("    - Red Alliance is more likely to climb, increasing their chances of earning the Harmony bonus.")
        else:
            st.markdown("    - Blue Alliance is more likely to climb, increasing their chances of earning the Harmony bonus.")

    # Alliance Bonuses
    st.markdown("- **Estimated Alliance Bonuses**")
    st.markdown(f"  - Red Alliance Bonus: {red_bonus:.2f} points")
    st.markdown(f"  - Blue Alliance Bonus: {blue_bonus:.2f} points")
    if red_bonus > blue_bonus:
        st.markdown("    - Red Alliance is more likely to earn alliance bonuses (Co-op and Harmony).")
    else:
        st.markdown("    - Blue Alliance is more likely to earn alliance bonuses (Co-op and Harmony).")

else:
    st.info("Please select teams for both Red and Blue Alliances to predict the match.")