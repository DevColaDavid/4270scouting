import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
import time
from datetime import datetime

# Add the parent directory to the Python path to ensure utils can be found
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Try importing from utils.utils
try:
    from utils.utils import setup_sidebar_navigation, load_data, load_pit_data, calculate_match_score, get_firebase_instances
    print("Successfully imported from utils.utils")
except ImportError as e:
    print(f"Failed to import from utils.utils: {e}")
    raise

# Set page config as the first Streamlit command
st.set_page_config(page_title="Data Analysis", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# Get Firebase instances after setting page config
try:
    db, bucket = get_firebase_instances()
    st.session_state.firebase_db = db
    st.session_state.firebase_bucket = bucket
except Exception as e:
    st.error(f"Failed to initialize Firebase: {str(e)}")
    st.stop()

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in to access this page.")
    st.stop()

# Set up the sidebar navigation
setup_sidebar_navigation()

# Page content
st.title("📊 Data Analysis")
st.info("This page automatically updates every 30 seconds to reflect new scouting data. Use the button below to refresh manually.")

# Track the active page
if 'active_page' not in st.session_state:
    st.session_state.active_page = None

# Set the active page to "Data Analysis" when this page is loaded
st.session_state.active_page = "Data Analysis"

# Function to fetch both match and pit scouting data with 30-second polling and manual refresh
def fetch_data(force_refresh=False):
    # Initialize data in session state if not present
    if 'match_data' not in st.session_state:
        st.session_state.match_data = None
    if 'pit_data' not in st.session_state:
        st.session_state.pit_data = None
    
    # Initialize last fetch time if not present
    if 'last_fetch_time_analysis' not in st.session_state:
        st.session_state.last_fetch_time_analysis = 0
    
    # Only fetch if we're on the Data Analysis page or if force_refresh is True
    if st.session_state.active_page != "Data Analysis" and not force_refresh:
        return st.session_state.match_data, st.session_state.pit_data

    # Fetch data if 30 seconds have passed, cache is empty, or force_refresh is True
    current_time = time.time()
    if force_refresh or current_time - st.session_state.last_fetch_time_analysis >= 30 or st.session_state.match_data is None or st.session_state.pit_data is None:
        try:
            match_df = load_data()  # Uses st.session_state.firebase_db
            pit_df = load_pit_data()  # Uses st.session_state.firebase_db
            st.session_state.match_data = match_df
            st.session_state.pit_data = pit_df
            st.session_state.last_fetch_time_analysis = current_time
            st.session_state.fetch_log_analysis = (
                f"Data fetched at {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}: "
                f"{len(match_df) if match_df is not None else 0} match records, "
                f"{len(pit_df) if pit_df is not None else 0} pit records"
            )
        except Exception as e:
            st.error(f"Failed to load data: {str(e)}")
            st.session_state.match_data = None
            st.session_state.pit_data = None
            st.stop()
    
    return st.session_state.match_data, st.session_state.pit_data

# Manual refresh button
if st.button("Refresh Now", key="manual_refresh_analysis"):
    fetch_data(force_refresh=True)
    st.rerun()

# Fetch data
with st.spinner("Loading data for analysis..."):
    match_df, pit_df = fetch_data()

# Display fetch log
if 'fetch_log_analysis' in st.session_state:
    st.write(f"{st.session_state.fetch_log_analysis}")

# Display static countdown to next refresh
if 'last_fetch_time_analysis' in st.session_state:
    time_since_last_fetch = time.time() - st.session_state.last_fetch_time_analysis
    time_until_next_fetch = max(0, 30 - time_since_last_fetch)
    st.write(f"Next refresh in {int(time_until_next_fetch)} seconds")

# Schedule the next refresh (only if on Data Analysis page)
if st.session_state.active_page == "Data Analysis":
    time_since_last_fetch = time.time() - st.session_state.last_fetch_time_analysis
    if time_since_last_fetch >= 30:
        st.rerun()

# Stop if no match data is available
if match_df is None or match_df.empty:
    st.info("No match data available for analysis. Please upload match data in the Data Management page.")
    st.stop()

# If no pit data is available, display a warning but continue with match data
if pit_df is None or pit_df.empty:
    st.warning("No pit data available for analysis. Pit scouting statistics will be unavailable.")
    pit_df = pd.DataFrame()

# Ensure numeric columns are properly typed for match data
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

# Ensure numeric and boolean columns in pit data
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

# Convert team_number to string to ensure consistency
if 'team_number' in match_df.columns:
    match_df['team_number'] = match_df['team_number'].astype(str)
else:
    st.error("Required column 'team_number' is missing in the match data.")
    st.stop()

if 'team_number' in pit_df.columns:
    pit_df['team_number'] = pit_df['team_number'].astype(str)

# Define required columns for scoring (match data)
required_cols = [
    'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
    'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
    'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
    'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
    'auto_taxi_left', 'climb_status', 'match_number', 'alliance_color'
]

# Calculate match scores and alliance bonuses
score_columns = ['auto_score', 'teleop_score', 'endgame_score', 'total_score']
if all(col in match_df.columns for col in required_cols):
    # Only calculate scores if they don't already exist
    if not all(col in match_df.columns for col in score_columns):
        scores = match_df.apply(calculate_match_score, axis=1)
        match_df[score_columns] = scores

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

    match_df = calculate_alliance_bonuses(match_df)

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

    match_df = calculate_epa(match_df)
else:
    st.warning("Cannot calculate match scores. Missing required columns: " +
               ", ".join([col for col in required_cols if col not in match_df.columns]))
    st.stop()

# Team selection for detailed analysis
if 'team_number' in match_df.columns:
    team_numbers = sorted(match_df['team_number'].dropna().unique())
    selected_teams = st.multiselect("Select Teams to Analyze (Leave blank to analyze all)", options=team_numbers)
    if selected_teams:
        match_df = match_df[match_df['team_number'].isin(selected_teams)]
        if not pit_df.empty:
            pit_df = pit_df[pit_df['team_number'].isin(selected_teams)]
else:
    st.error("Team number data not available in match data.")
    st.stop()

# Calculate success ratios for match data (needed for leaderboard and scoring accuracy analysis)
coral_scored_cols = [f"{period}_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
coral_missed_cols = [f"{period}_missed_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
match_df['total_coral_scored'] = match_df[coral_scored_cols].sum(axis=1)
match_df['total_coral_missed'] = match_df[coral_missed_cols].sum(axis=1)
match_df['total_coral_attempts'] = match_df['total_coral_scored'] + match_df['total_coral_missed']
match_df['coral_success_ratio'] = (match_df['total_coral_scored'] / match_df['total_coral_attempts'].replace(0, pd.NA)).fillna(0)

algae_scored_cols = [f"{period}_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
algae_missed_cols = [f"{period}_missed_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
match_df['total_algae_scored'] = match_df[algae_scored_cols].sum(axis=1)
match_df['total_algae_missed'] = match_df[algae_missed_cols].sum(axis=1)
match_df['total_algae_attempts'] = match_df['total_algae_scored'] + match_df['total_algae_missed']
match_df['algae_success_ratio'] = (match_df['total_algae_scored'] / match_df['total_algae_attempts'].replace(0, pd.NA)).fillna(0)

# Create tabs for Match Scouting and Pit Scouting
match_tab, pit_tab = st.tabs(["Match Scouting Analysis", "Pit Scouting Analysis"])

# Match Scouting Analysis Tab
with match_tab:
    # Team Leaderboard with Pit Scouting Data
    st.subheader("🏆 Team Leaderboard")
    st.markdown("Teams ranked based on performance metrics, including pit scouting data. Select a metric to sort the table.")

    # Calculate metrics for the leaderboard (match data)
    leaderboard_data = match_df.groupby('team_number').agg({
        'total_score': 'mean',           # Average Total Score
        'epa': 'mean',                   # Average EPA
        'coral_success_ratio': 'mean',   # Average Coral Success Ratio
        'algae_success_ratio': 'mean',   # Average Algae Success Ratio
        'defense_rating': 'mean',        # Average Defense Rating
        'speed_rating': 'mean',          # Average Speed Rating
        'driver_skill_rating': 'mean'    # Average Driver Skill Rating
    }).reset_index()

    # Merge with pit scouting data
    if not pit_df.empty:
        pit_leaderboard = pit_df.groupby('team_number').agg({
            'drivetrain_type': lambda x: x.mode()[0] if not x.mode().empty else 'Unknown',  # Most common drivetrain type
            'preferred_role': lambda x: x.mode()[0] if not x.mode().empty else 'Unknown',  # Most common preferred role
            'endgame_capability': lambda x: x.mode()[0] if not x.mode().empty else 'Unknown',  # Most common endgame capability
        }).reset_index()
        leaderboard_data = leaderboard_data.merge(pit_leaderboard, on='team_number', how='left')
    else:
        # Add placeholder columns if pit data is unavailable
        leaderboard_data['drivetrain_type'] = 'N/A'
        leaderboard_data['preferred_role'] = 'N/A'
        leaderboard_data['endgame_capability'] = 'N/A'

<<<<<<< Updated upstream
    # Convert success ratios to percentages
    leaderboard_data['coral_success_ratio'] = leaderboard_data['coral_success_ratio'] * 100
    leaderboard_data['algae_success_ratio'] = leaderboard_data['algae_success_ratio'] * 100
=======
# Get any additional columns (e.g., calculated fields like total_score, epa, etc.)
additional_columns = [col for col in df.columns if col not in desired_column_order]
>>>>>>> Stashed changes

    # Rename columns for display
    leaderboard_data = leaderboard_data.rename(columns={
        'team_number': 'Team Number',
        'total_score': 'Average Total Score',
        'epa': 'Average EPA',
        'coral_success_ratio': 'Coral Success Ratio (%)',
        'algae_success_ratio': 'Algae Success Ratio (%)',
        'defense_rating': 'Average Defense Rating',
        'speed_rating': 'Average Speed Rating',
        'driver_skill_rating': 'Average Driver Skill Rating',
        'drivetrain_type': 'Drivetrain Type',
        'preferred_role': 'Preferred Role',
        'endgame_capability': 'Endgame Capability'
    })

    # Dropdown to select the sorting metric
    sort_metric = st.selectbox(
        "Sort Leaderboard By",
        options=[
            "Average Total Score",
            "Average EPA",
            "Coral Success Ratio (%)",
            "Algae Success Ratio (%)",
            "Average Defense Rating",
            "Average Speed Rating",
            "Average Driver Skill Rating"
        ],
        index=0  # Default to Average Total Score
    )

    # Map the display name back to the DataFrame column name for sorting
    sort_column_map = {
        "Average Total Score": "Average Total Score",
        "Average EPA": "Average EPA",
        "Coral Success Ratio (%)": "Coral Success Ratio (%)",
        "Algae Success Ratio (%)": "Algae Success Ratio (%)",
        "Average Defense Rating": "Average Defense Rating",
        "Average Speed Rating": "Average Speed Rating",
        "Average Driver Skill Rating": "Average Driver Skill Rating"
    }

<<<<<<< Updated upstream
    # Sort the leaderboard based on the selected metric
    leaderboard_data = leaderboard_data.sort_values(by=sort_column_map[sort_metric], ascending=False)

    # Add rank based on the sorting metric, handle NaN values
    ranks = leaderboard_data[sort_column_map[sort_metric]].rank(ascending=False, method='min')
    # Fill NaN ranks with the maximum rank + 1 (or another default value)
    max_rank = ranks.max() if not ranks.isna().all() else 0
    leaderboard_data['Rank'] = ranks.fillna(max_rank + 1).astype(int)

    # Reorder columns to put Rank first and include pit data
    leaderboard_data = leaderboard_data[[
        'Rank', 'Team Number', 'Average Total Score', 'Average EPA',
        'Coral Success Ratio (%)', 'Algae Success Ratio (%)',
        'Average Defense Rating', 'Average Speed Rating', 'Average Driver Skill Rating',
        'Drivetrain Type', 'Preferred Role', 'Endgame Capability'
    ]]

    # Round the values for better readability
    leaderboard_data['Average Total Score'] = leaderboard_data['Average Total Score'].round(2)
    leaderboard_data['Average EPA'] = leaderboard_data['Average EPA'].round(2)
    leaderboard_data['Coral Success Ratio (%)'] = leaderboard_data['Coral Success Ratio (%)'].round(2)
    leaderboard_data['Algae Success Ratio (%)'] = leaderboard_data['Algae Success Ratio (%)'].round(2)
    leaderboard_data['Average Defense Rating'] = leaderboard_data['Average Defense Rating'].round(2)
    leaderboard_data['Average Speed Rating'] = leaderboard_data['Average Speed Rating'].round(2)
    leaderboard_data['Average Driver Skill Rating'] = leaderboard_data['Average Driver Skill Rating'].round(2)

    # Display the leaderboard
    st.dataframe(
        leaderboard_data,
        use_container_width=True,
        hide_index=True
    )

    # Total Score Analysis
    st.subheader("Total Score Analysis")
    st.markdown("Distribution and trends of total scores across matches for each team.")
    if 'total_score' in match_df.columns:
        # Histogram of Total Scores
        fig = px.histogram(match_df, x='total_score', color='team_number', marginal="box",
                           title="Total Score Distribution by Team",
                           labels={'total_score': 'Total Score'})
        st.plotly_chart(fig, use_container_width=True)

        # Line Chart: Total Score Trend Over Matches
        if 'match_number' in match_df.columns:
            trend_data = match_df.sort_values('match_number')
            fig = px.line(trend_data, x='match_number', y='total_score', color='team_number',
                          title='Total Score Trend Over Matches',
                          labels={'match_number': 'Match Number', 'total_score': 'Total Score'})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Total score data not available for visualization.")

    # EPA Analysis
    st.subheader("Expected Points Added (EPA)")
    st.markdown("EPA measures a team's contribution to their alliance's score relative to the average performance of teams in the same alliance color. Higher EPA indicates a greater positive impact.")
    if 'epa' in match_df.columns:
        epa_data = match_df.groupby('team_number')['epa'].mean().reset_index()
        fig = px.bar(epa_data, x='team_number', y='epa', title='Average EPA by Team',
                     labels={'team_number': 'Team Number', 'epa': 'EPA'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("EPA data not available for visualization.")

    # Climb Analysis
    st.subheader("Climb Analysis")
    st.markdown("Analysis of endgame performance, including parking and climbing statistics.")
    if 'climb_status' in match_df.columns and 'endgame_score' in match_df.columns:
        # Climb and Park Rates by Team (Stacked Bar Chart)
        climb_stats = match_df.groupby('team_number')['climb_status'].value_counts(normalize=True).unstack(fill_value=0) * 100
        climb_stats = climb_stats.reset_index()
        fig = go.Figure()
        for status in ['None', 'Parked', 'Shallow Climb', 'Deep Climb']:
            if status in climb_stats.columns:
                fig.add_trace(go.Bar(
                    x=climb_stats['team_number'],
                    y=climb_stats[status],
                    name=status
                ))
        fig.update_layout(
            barmode='stack',
            title="Climb and Park Rates by Team",
            xaxis_title="Team Number",
            yaxis_title="Percentage (%)",
            legend_title="Climb Status"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Average Endgame Score by Team
        endgame_scores = match_df.groupby('team_number')['endgame_score'].mean().reset_index()
        fig = px.bar(endgame_scores, x='team_number', y='endgame_score',
                     title="Average Endgame Score by Team",
                     labels={'team_number': 'Team Number', 'endgame_score': 'Average Endgame Score'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Climb status or endgame score data not available for visualization.")

    # Coral Analysis
    st.subheader("Coral Analysis")
    st.markdown("Analysis of coral scored and missed in autonomous and teleop periods.")

    # Autonomous Coral Scored
    st.markdown("#### Autonomous Coral Scored")
    st.markdown("Average number of coral scored per match in each level during autonomous.")
    if all(col in match_df.columns for col in ['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']):
        auto_coral = match_df.groupby('team_number')[['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']].mean().reset_index()
        fig = go.Figure()
        for level in ['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']:
            fig.add_trace(go.Bar(
                x=auto_coral['team_number'],
                y=auto_coral[level],
                name=level.replace('auto_coral_', 'Level ')
            ))
        fig.update_layout(
            barmode='stack',
            title="Average Autonomous Coral Scored by Team",
            xaxis_title="Team Number",
            yaxis_title="Average Coral Scored",
            legend_title="Level"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Autonomous coral data not available for visualization.")

    # Autonomous Coral Missed
    st.markdown("#### Autonomous Coral Missed")
    st.markdown("Average number of coral missed per match in each level during autonomous.")
    if all(col in match_df.columns for col in ['auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4']):
        auto_missed_coral = match_df.groupby('team_number')[['auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4']].mean().reset_index()
        fig = go.Figure()
        for level in ['auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4']:
            fig.add_trace(go.Bar(
                x=auto_missed_coral['team_number'],
                y=auto_missed_coral[level],
                name=level.replace('auto_missed_coral_', 'Level ')
            ))
        fig.update_layout(
            barmode='stack',
            title="Average Autonomous Coral Missed by Team",
            xaxis_title="Team Number",
            yaxis_title="Average Coral Missed",
            legend_title="Level"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Autonomous missed coral data not available for visualization.")

    # Teleop Coral Scored
    st.markdown("#### Teleop Coral Scored")
    st.markdown("Average number of coral scored per match in each level during teleop.")
    if all(col in match_df.columns for col in ['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']):
        teleop_coral = match_df.groupby('team_number')[['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']].mean().reset_index()
        fig = go.Figure()
        for level in ['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']:
            fig.add_trace(go.Bar(
                x=teleop_coral['team_number'],
                y=teleop_coral[level],
                name=level.replace('teleop_coral_', 'Level ')
            ))
        fig.update_layout(
            barmode='stack',
            title="Average Teleop Coral Scored by Team",
            xaxis_title="Team Number",
            yaxis_title="Average Coral Scored",
            legend_title="Level"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Teleop coral data not available for visualization.")

    # Teleop Coral Missed
    st.markdown("#### Teleop Coral Missed")
    st.markdown("Average number of coral missed per match in each level during teleop.")
    if all(col in match_df.columns for col in ['teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4']):
        teleop_missed_coral = match_df.groupby('team_number')[['teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4']].mean().reset_index()
        fig = go.Figure()
        for level in ['teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4']:
            fig.add_trace(go.Bar(
                x=teleop_missed_coral['team_number'],
                y=teleop_missed_coral[level],
                name=level.replace('teleop_missed_coral_', 'Level ')
            ))
        fig.update_layout(
            barmode='stack',
            title="Average Teleop Coral Missed by Team",
            xaxis_title="Team Number",
            yaxis_title="Average Coral Missed",
            legend_title="Level"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Teleop missed coral data not available for visualization.")

    # Algae Analysis
    st.subheader("Algae Analysis")
    st.markdown("Analysis of algae management in autonomous and teleop periods (to barge, to processor, removed, and missed).")

    # Autonomous Algae Management
    st.markdown("#### Autonomous Algae Management")
    if all(col in match_df.columns for col in ['auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed', 'auto_missed_algae_barge', 'auto_missed_algae_processor']):
        auto_algae = match_df.groupby('team_number')[['auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed', 'auto_missed_algae_barge', 'auto_missed_algae_processor']].mean().reset_index()
        fig = go.Figure()
        for metric in ['auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed', 'auto_missed_algae_barge', 'auto_missed_algae_processor']:
            fig.add_trace(go.Bar(
                x=auto_algae['team_number'],
                y=auto_algae[metric],
                name=metric.replace('auto_', '').replace('_', ' ').title()
            ))
        fig.update_layout(
            barmode='stack',
            title="Average Autonomous Algae Management by Team",
            xaxis_title="Team Number",
            yaxis_title="Average Count",
            legend_title="Metric"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Autonomous algae data not available for visualization.")

    # Teleop Algae Management
    st.markdown("#### Teleop Algae Management")
    if all(col in match_df.columns for col in ['teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor']):
        teleop_algae = match_df.groupby('team_number')[['teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor']].mean().reset_index()
        fig = go.Figure()
        for metric in ['teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor']:
            fig.add_trace(go.Bar(
                x=teleop_algae['team_number'],
                y=teleop_algae[metric],
                name=metric.replace('teleop_', '').replace('_', ' ').title()
            ))
        fig.update_layout(
            barmode='stack',
            title="Average Teleop Algae Management by Team",
            xaxis_title="Team Number",
            yaxis_title="Average Count",
            legend_title="Metric"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Teleop algae data not available for visualization.")

    # Performance Ratings
    st.subheader("Performance Ratings")
    st.markdown("Average ratings for defense, speed, and driver skill, as assessed by scouters (1 to 5).")
    if 'defense_rating' in match_df.columns and 'speed_rating' in match_df.columns and 'driver_skill_rating' in match_df.columns:
        # Calculate average ratings for each team
        ratings = match_df.groupby('team_number')[['defense_rating', 'speed_rating', 'driver_skill_rating']].mean().reset_index()

        # If specific teams are selected, use only those teams
        if selected_teams:
            ratings = ratings[ratings['team_number'].isin(selected_teams)]
        else:
            # Sort by defense_rating to determine top teams
            ratings = ratings.sort_values('defense_rating', ascending=False)

        # Get the total number of teams
        total_teams = len(ratings)

        # Check if there are teams to display
        if total_teams == 0:
            st.warning("No teams available to display in the radar chart. Please select teams or ensure rating data exists.")
        else:
            # If there's only one team, skip the slider and set num_teams_to_display to 1
            if total_teams == 1:
                num_teams_to_display = 1
                st.info("Only one team available to display in the radar chart.")
            else:
                # Add a slider to select the number of teams to display (default to 10, max is total_teams)
                num_teams_to_display = st.slider(
                    "Number of Teams to Display in Radar Chart",
                    min_value=1,
                    max_value=total_teams,
                    value=min(10, total_teams),  # Default to 10 or total_teams if less than 10
                    step=1
                )

            # Limit to the selected number of top teams
            ratings = ratings.head(num_teams_to_display)

            # Create radar chart
            fig = go.Figure()
            categories = ['Defense', 'Speed', 'Driver Skill', 'Defense']  # Repeat the first category to close the loop

            # Define a list of colors for different teams
            colors = px.colors.qualitative.Plotly  # A list of distinct colors

            for idx, row in ratings.iterrows():
                team = row['team_number']
                values = [
                    row['defense_rating'],
                    row['speed_rating'],
                    row['driver_skill_rating'],
                    row['defense_rating']  # Repeat the first value to close the loop
                ]
                # Only add the trace if the team has non-zero ratings
                if sum(values[:-1]) > 0:  # Exclude the repeated value for the check
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories,
                        fill='toself',
                        name=f'Team {team}',
                        line=dict(color=colors[idx % len(colors)]),
                        fillcolor=colors[idx % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.15)')  # Reduced opacity to 0.15
                    ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 5],  # Ratings are from 1 to 5
                        tickvals=[1, 2, 3, 4, 5]
                    )
                ),
                showlegend=True,
                title="Performance Ratings by Team (Radar Chart)",
                margin=dict(l=50, r=50, t=50, b=50)
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Performance rating data not available for visualization.")
        
    # Taxi Rate by Team
    st.subheader("Taxi Rate by Team")
    st.markdown("Percentage of matches where each team successfully taxied (left starting position) during autonomous.")
    if 'auto_taxi_left' in match_df.columns:
        taxi_rates = match_df.groupby('team_number')['auto_taxi_left'].mean() * 100
        taxi_df = pd.DataFrame({
            'Team Number': taxi_rates.index,
            'Taxi Rate (%)': taxi_rates.values
        })
        fig = px.bar(taxi_df, x='Team Number', y='Taxi Rate (%)', title="Percentage of Matches with Successful Taxi",
                     labels={'Team Number': 'Team Number', 'Taxi Rate (%)': 'Taxi Rate (%)'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Taxi data not available for visualization.")

    # Scoring Accuracy Analysis
    st.subheader("Scoring Accuracy Analysis")
    avg_coral_success = match_df.groupby('team_number')['coral_success_ratio'].mean() * 100
    avg_algae_success = match_df.groupby('team_number')['algae_success_ratio'].mean() * 100

    # Plot success ratios
    success_data = pd.DataFrame({
        'Team Number': avg_coral_success.index,
        'Coral Success Ratio (%)': avg_coral_success.values,
        'Algae Success Ratio (%)': avg_algae_success.values
    })
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=success_data['Team Number'],
        y=success_data['Coral Success Ratio (%)'],
        name='Coral Success Ratio'
    ))
    fig.add_trace(go.Bar(
        x=success_data['Team Number'],
        y=success_data['Algae Success Ratio (%)'],
        name='Algae Success Ratio'
    ))
    fig.update_layout(
        barmode='group',
        title="Scoring Success Ratios by Team",
        xaxis_title="Team Number",
        yaxis_title="Success Ratio (%)",
        legend_title="Metric"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Raw Data - Match Scouting
    st.subheader("Raw Match Scouting Data")
    st.markdown("Complete dataset for all matches, including all collected metrics. Use the table below to view and download the data.")

    # Define the desired column order for match scouting data
    match_desired_columns = [
        # MATCH_INFO
        'team_number', 'match_number', 'alliance_color', 'scouter_name', 'starting_position',
        # MATCH_OUTCOME
        'match_outcome',
        # AUTONOMOUS
        'auto_taxi_left',
        'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
        'auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4',
        'auto_algae_barge', 'auto_algae_processor', 'auto_missed_algae_barge', 'auto_missed_algae_processor', 'auto_algae_removed',
        # TELEOP
        'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
        'teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4',
        'teleop_algae_barge', 'teleop_algae_processor', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor', 'teleop_algae_removed',
        # ENDGAME
        'climb_status',
        # PERFORMANCE_RATINGS
        'defense_rating', 'speed_rating', 'driver_skill_rating',
        # STRATEGY
        'primary_role',
        # ANALYSIS
        'defense_qa', 'teleop_qa', 'auto_qa', 'comments'
    ]

    # Filter the desired columns that exist in the DataFrame
    match_available_columns = [col for col in match_desired_columns if col in match_df.columns]
    match_additional_columns = [col for col in match_df.columns if col not in match_desired_columns]
    match_final_columns = match_available_columns + match_additional_columns

    # Reorder the DataFrame
    match_df_reordered = match_df[match_final_columns]

    # Display match scouting data
    st.dataframe(match_df_reordered, use_container_width=True)

    # Download button for match scouting data
    match_csv = match_df_reordered.to_csv(index=False)
    st.download_button(
        label="Download Match Scouting Data as CSV",
        data=match_csv,
        file_name="match_scouting_data.csv",
        mime="text/csv"
    )

# Pit Scouting Analysis Tab
with pit_tab:
    # Only show pit scouting data if match scouting data exists
    if match_df is None or match_df.empty:
        st.info("Pit scouting data is not available because there is no match scouting data. Please ensure match data is uploaded.")
    elif pit_df.empty:
        st.info("No pit scouting data available for analysis.")
    else:
        # Pit Scouting Analysis
        st.subheader("Pit Scouting Analysis")
        st.markdown("Analysis of robot capabilities and strategies based on pit scouting data.")

        # Drivetrain Type Distribution
        st.markdown("#### Drivetrain Type Distribution")
        drivetrain_counts = pit_df.groupby('drivetrain_type')['team_number'].nunique().reset_index()
        drivetrain_counts.columns = ['Drivetrain Type', 'Number of Teams']
        fig = px.bar(drivetrain_counts, x='Drivetrain Type', y='Number of Teams',
                     title="Number of Teams by Drivetrain Type",
                     labels={'Drivetrain Type': 'Drivetrain Type', 'Number of Teams': 'Number of Teams'})
        st.plotly_chart(fig, use_container_width=True)

        # Capabilities Analysis
        st.markdown("#### Robot Capabilities")
        capability_cols = [
            'can_score_coral_l1', 'can_score_coral_l2', 'can_score_coral_l3', 'can_score_coral_l4',
            'can_score_algae_barge', 'can_score_algae_processor', 'can_remove_algae_l1', 'can_remove_algae_l2'
        ]
        capability_data = pit_df.groupby('team_number')[capability_cols].mean() * 100  # Convert to percentage
        capability_data = capability_data.reset_index()
        
        fig = go.Figure()
        for col in capability_cols:
            fig.add_trace(go.Bar(
                x=capability_data['team_number'],
                y=capability_data[col],
                name=col.replace('can_', '').replace('_', ' ').title()
            ))
        fig.update_layout(
            barmode='group',
            title="Robot Capabilities by Team (Percentage of Records with Capability)",
            xaxis_title="Team Number",
            yaxis_title="Percentage (%)",
            legend_title="Capability"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Preferred Role Distribution
        st.markdown("#### Preferred Role Distribution")
        role_counts = pit_df.groupby('preferred_role')['team_number'].nunique().reset_index()
        role_counts.columns = ['Preferred Role', 'Number of Teams']
        fig = px.bar(role_counts, x='Preferred Role', y='Number of Teams',
                     title="Number of Teams by Preferred Role",
                     labels={'Preferred Role': 'Preferred Role', 'Number of Teams': 'Number of Teams'})
        st.plotly_chart(fig, use_container_width=True)

        # Endgame Capability Distribution
        st.markdown("#### Endgame Capability Distribution")
        endgame_counts = pit_df.groupby('endgame_capability')['team_number'].nunique().reset_index()
        endgame_counts.columns = ['Endgame Capability', 'Number of Teams']
        fig = px.bar(endgame_counts, x='Endgame Capability', y='Number of Teams',
                     title="Number of Teams by Endgame Capability",
                     labels={'Endgame Capability': 'Endgame Capability', 'Number of Teams': 'Number of Teams'})
        st.plotly_chart(fig, use_container_width=True)

        # Robot Photos Section (Pit Scouting)
    st.markdown("#### Robot Photos (Pit Scouting)")
    st.markdown("Photos of robots submitted during pit scouting, organized by team.")
    if 'robot_photo_url' in pit_df.columns and pit_df['robot_photo_url'].notna().any():
        # Group by team number and collect all photo URLs for each team
        photo_data = pit_df.groupby('team_number')['robot_photo_url'].apply(list).reset_index()
        
        for _, row in photo_data.iterrows():
            team = row['team_number']
            photos = [url for url in row['robot_photo_url'] if url and url != '']  # Filter out None or empty URLs
            
            if photos:
                st.markdown(f"**Team {team}**")
                cols = st.columns(3)  # Display up to 3 photos per row
                for idx, photo_url in enumerate(photos):
                    # Validate the URL
                    if not isinstance(photo_url, str) or not photo_url.startswith(('http://', 'https://')):
                        with cols[idx % 3]:
                            st.warning(f"Invalid photo URL for Team {team} (Photo {idx + 1}): {photo_url}")
                        continue
                    
                    # Attempt to display the image
                    try:
                        with cols[idx % 3]:
                            st.image(photo_url, caption=f"Team {team} Pit Photo {idx + 1}", width=200)
                    except Exception as e:
                        with cols[idx % 3]:
                            st.error(f"Failed to load photo for Team {team} (Photo {idx + 1}): {str(e)}")
    else:
        st.info("No robot photos available from pit scouting.")

        # Team Comments and Scouter Notes
        st.markdown("#### Team Comments and Scouter Notes")
        comments_data = pit_df[['team_number', 'team_comments', 'scouter_notes']].drop_duplicates()
        comments_data = comments_data.sort_values('team_number')
        st.dataframe(
            comments_data,
            use_container_width=True,
            column_config={
                'team_number': 'Team Number',
                'team_comments': 'Team Comments',
                'scouter_notes': 'Scouter Notes'
            }
        )

        # Raw Data - Pit Scouting
        st.subheader("Raw Pit Scouting Data")
        st.markdown("Complete dataset for all pit scouting entries. Use the table below to view and download the data.")

        # Define the desired column order for pit scouting data
        pit_desired_columns = [
            'team_number', 'scouter_name', 'drivetrain_type',
            'can_score_coral_l1', 'can_score_coral_l2', 'can_score_coral_l3', 'can_score_coral_l4',
            'can_score_algae_barge', 'can_score_algae_processor', 'can_remove_algae_l1', 'can_remove_algae_l2',
            'endgame_capability', 'preferred_role', 'auto_strategy',
            'robot_strengths', 'robot_weaknesses', 'team_comments', 'scouter_notes',
            'robot_photo_url'  # Added to display photo URLs in the raw data table
        ]

        # Filter the desired columns that exist in the DataFrame
        pit_available_columns = [col for col in pit_desired_columns if col in pit_df.columns]
        pit_additional_columns = [col for col in pit_df.columns if col not in pit_desired_columns]
        pit_final_columns = pit_available_columns + pit_additional_columns

        # Reorder the DataFrame
        pit_df_reordered = pit_df[pit_final_columns]

        # Display pit scouting data
        st.dataframe(pit_df_reordered, use_container_width=True)

        # Download button for pit scouting data
        pit_csv = pit_df_reordered.to_csv(index=False)
        st.download_button(
            label="Download Pit Scouting Data as CSV",
            data=pit_csv,
            file_name="pit_scouting_data.csv",
            mime="text/csv"
        )
=======
# Download button for raw data
csv = df.to_csv(index=False)
st.download_button(
    label="Download Raw Data as CSV",
    data=csv,
    file_name="scouting_data.csv",
    mime="text/csv"
)
>>>>>>> Stashed changes
