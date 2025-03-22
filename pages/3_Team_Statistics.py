import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, calculate_match_score
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Team Statistics", page_icon="📈", layout="wide")

# Auto-refresh every 10 seconds (10000 milliseconds)
st_autorefresh(interval=10000, key="team_statistics_refresh")

st.title("📈 Team Statistics")
st.info("This page automatically updates every 10 seconds to reflect new scouting data.")

# Load data
df = load_data()

if df is None or df.empty:
    st.info("No match data available for statistics.")
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
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Define required columns for scoring
required_cols = [
    'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
    'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
    'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
    'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
    'auto_taxi_left', 'climb_status', 'match_number', 'alliance_color'
]

# Calculate match scores and alliance bonuses
if all(col in df.columns for col in required_cols):
    df = df.join(df.apply(calculate_match_score, axis=1))

    # Calculate alliance-level bonuses
    def calculate_alliance_bonuses(df):
        # Co-op Bonus: 15 points if alliance scores 5 coral on at least 3 levels
        coral_cols = [
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4'
        ]
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

        # Harmony Bonus: 15 points if all robots in the alliance climb (Shallow or Deep)
        alliance_climb = df.groupby(['match_number', 'alliance_color'])['climb_status'].value_counts().unstack(fill_value=0)
        alliance_climb['num_robots'] = df.groupby(['match_number', 'alliance_color'])['team_number'].nunique()
        alliance_climb['num_climbs'] = alliance_climb.get('Shallow Climb', 0) + alliance_climb.get('Deep Climb', 0)
        alliance_climb['harmony_bonus'] = alliance_climb.apply(
            lambda row: 15 if row['num_climbs'] == row['num_robots'] and row['num_robots'] > 0 else 0, axis=1
        )

        # Merge bonuses back into the DataFrame
        df = df.merge(
            alliance_coral[['match_number', 'alliance_color', 'coop_bonus']],
            on=['match_number', 'alliance_color'],
            how='left'
        )
        df = df.merge(
            alliance_climb[['harmony_bonus']].reset_index()[['match_number', 'alliance_color', 'harmony_bonus']],
            on=['match_number', 'alliance_color'],
            how='left'
        )

        # Add bonuses to total score
        df['total_score'] = (
            df['total_score'] +
            df['coop_bonus'].fillna(0) +
            df['harmony_bonus'].fillna(0)
        )

        return df

    df = calculate_alliance_bonuses(df)

    # Calculate match outcomes (Win, Loss, Tie)
    def calculate_match_outcomes(df):
        # Calculate total score for each alliance in each match
        alliance_scores = df.groupby(['match_number', 'alliance_color'])['total_score'].sum().reset_index()
        
        # Pivot to get Red and Blue scores for each match
        scores_pivot = alliance_scores.pivot(index='match_number', columns='alliance_color', values='total_score').reset_index()
        scores_pivot = scores_pivot.rename(columns={'Red': 'red_score', 'Blue': 'blue_score'})
        
        # Determine the winner for each match
        scores_pivot['winner'] = scores_pivot.apply(
            lambda row: 'Red' if row['red_score'] > row['blue_score'] else ('Blue' if row['blue_score'] > row['red_score'] else 'Tie'),
            axis=1
        )
        
        # Merge the winner back into the original DataFrame
        df = df.merge(scores_pivot[['match_number', 'winner']], on='match_number', how='left')
        
        # Assign match_result to each team based on their alliance
        df['match_result'] = df.apply(
            lambda row: 'Win' if row['alliance_color'] == row['winner'] else ('Tie' if row['winner'] == 'Tie' else 'Loss'),
            axis=1
        )
        
        return df

    df = calculate_match_outcomes(df)
else:
    st.warning("Cannot calculate match scores. Missing required columns.")
    st.stop()

# Team selection
if 'team_number' in df.columns:
    team_numbers = sorted(df['team_number'].dropna().unique())
    selected_team = st.selectbox("Select a Team", options=team_numbers)
else:
    st.error("Team number column not found in data.")
    st.stop()

# Filter data for the selected team
team_data = df[df['team_number'] == selected_team]

if team_data.empty:
    st.info(f"No data available for team {selected_team}.")
    st.stop()

# Display team statistics
st.subheader(f"Statistics for Team {selected_team}")

# Basic Statistics
st.markdown("### Basic Statistics")
st.markdown("Overview of the team's overall performance across all matches.")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Matches", len(team_data))
with col2:
    if 'total_score' in team_data.columns:
        avg_score = team_data['total_score'].mean()
        st.metric("Avg Total Score", f"{avg_score:.1f}")
    else:
        st.metric("Avg Total Score", "N/A")
with col3:
    if 'match_result' in team_data.columns:
        win_rate = (team_data['match_result'] == 'Win').mean() * 100
        st.metric("Win Rate", f"{win_rate:.1f}%")
    else:
        st.metric("Win Rate", "N/A")

# Autonomous Statistics
st.markdown("### Autonomous Statistics")
st.markdown("Performance metrics for the autonomous period (first 15 seconds of the match).")
col1, col2, col3 = st.columns(3)
with col1:
    if 'auto_score' in team_data.columns:
        avg_auto_score = team_data['auto_score'].mean()
        st.metric("Avg Auto Score", f"{avg_auto_score:.1f}")
    else:
        st.metric("Avg Auto Score", "N/A")
with col2:
    if 'auto_taxi_left' in team_data.columns:
        taxi_rate = team_data['auto_taxi_left'].mean() * 100
        st.metric("Taxi Rate", f"{taxi_rate:.1f}%")
    else:
        st.metric("Taxi Rate", "N/A")
with col3:
    if 'auto_algae_removed' in team_data.columns:
        avg_algae_removed = team_data['auto_algae_removed'].mean()
        st.metric("Avg Algae Removed", f"{avg_algae_removed:.1f}")
    else:
        st.metric("Avg Algae Removed", "N/A")

# Detailed Autonomous Coral Stats
st.markdown("#### Autonomous Coral Scored")
st.markdown("Average number of coral scored per match in each level during autonomous.")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if 'auto_coral_l1' in team_data.columns:
        avg_auto_coral_l1 = team_data['auto_coral_l1'].mean()
        st.metric("Avg Level 1 Coral", f"{avg_auto_coral_l1:.1f}")
    else:
        st.metric("Avg Level 1 Coral", "N/A")
with col2:
    if 'auto_coral_l2' in team_data.columns:
        avg_auto_coral_l2 = team_data['auto_coral_l2'].mean()
        st.metric("Avg Level 2 Coral", f"{avg_auto_coral_l2:.1f}")
    else:
        st.metric("Avg Level 2 Coral", "N/A")
with col3:
    if 'auto_coral_l3' in team_data.columns:
        avg_auto_coral_l3 = team_data['auto_coral_l3'].mean()
        st.metric("Avg Level 3 Coral", f"{avg_auto_coral_l3:.1f}")
    else:
        st.metric("Avg Level 3 Coral", "N/A")
with col4:
    if 'auto_coral_l4' in team_data.columns:
        avg_auto_coral_l4 = team_data['auto_coral_l4'].mean()
        st.metric("Avg Level 4 Coral", f"{avg_auto_coral_l4:.1f}")
    else:
        st.metric("Avg Level 4 Coral", "N/A")

st.markdown("#### Autonomous Coral Missed")
st.markdown("Average number of coral missed per match in each level during autonomous.")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if 'auto_missed_coral_l1' in team_data.columns:
        avg_auto_missed_l1 = team_data['auto_missed_coral_l1'].mean()
        st.metric("Avg Missed Level 1", f"{avg_auto_missed_l1:.1f}")
    else:
        st.metric("Avg Missed Level 1", "N/A")
with col2:
    if 'auto_missed_coral_l2' in team_data.columns:
        avg_auto_missed_l2 = team_data['auto_missed_coral_l2'].mean()
        st.metric("Avg Missed Level 2", f"{avg_auto_missed_l2:.1f}")
    else:
        st.metric("Avg Missed Level 2", "N/A")
with col3:
    if 'auto_missed_coral_l3' in team_data.columns:
        avg_auto_missed_l3 = team_data['auto_missed_coral_l3'].mean()
        st.metric("Avg Missed Level 3", f"{avg_auto_missed_l3:.1f}")
    else:
        st.metric("Avg Missed Level 3", "N/A")
with col4:
    if 'auto_missed_coral_l4' in team_data.columns:
        avg_auto_missed_l4 = team_data['auto_missed_coral_l4'].mean()
        st.metric("Avg Missed Level 4", f"{avg_auto_missed_l4:.1f}")
    else:
        st.metric("Avg Missed Level 4", "N/A")

# Detailed Autonomous Algae Stats
st.markdown("#### Autonomous Algae Management")
st.markdown("Average algae managed per match during autonomous (to barge, processor, and removed).")
col1, col2, col3 = st.columns(3)
with col1:
    if 'auto_algae_barge' in team_data.columns:
        avg_auto_algae_barge = team_data['auto_algae_barge'].mean()
        st.metric("Avg Algae to Barge", f"{avg_auto_algae_barge:.1f}")
    else:
        st.metric("Avg Algae to Barge", "N/A")
with col2:
    if 'auto_algae_processor' in team_data.columns:
        avg_auto_algae_processor = team_data['auto_algae_processor'].mean()
        st.metric("Avg Algae to Processor", f"{avg_auto_algae_processor:.1f}")
    else:
        st.metric("Avg Algae to Processor", "N/A")
with col3:
    if 'auto_missed_algae_barge' in team_data.columns and 'auto_missed_algae_processor' in team_data.columns:
        total_missed_algae = (team_data['auto_missed_algae_barge'] + team_data['auto_missed_algae_processor']).mean()
        st.metric("Avg Missed Algae", f"{total_missed_algae:.1f}")
    else:
        st.metric("Avg Missed Algae", "N/A")

# Teleop Statistics
st.markdown("### Teleop Statistics")
st.markdown("Performance metrics for the teleop period (driver-controlled phase of the match).")
col1, col2, col3 = st.columns(3)
with col1:
    if 'teleop_score' in team_data.columns:
        avg_teleop_score = team_data['teleop_score'].mean()
        st.metric("Avg Teleop Score", f"{avg_teleop_score:.1f}")
    else:
        st.metric("Avg Teleop Score", "N/A")
with col2:
    if 'teleop_coral_l1' in team_data.columns:
        total_coral = (team_data['teleop_coral_l1'] + team_data['teleop_coral_l2'] +
                       team_data['teleop_coral_l3'] + team_data['teleop_coral_l4']).mean()
        st.metric("Avg Coral Scored", f"{total_coral:.1f}")
    else:
        st.metric("Avg Coral Scored", "N/A")
with col3:
    if 'teleop_algae_removed' in team_data.columns:
        avg_teleop_algae = team_data['teleop_algae_removed'].mean()
        st.metric("Avg Algae Removed", f"{avg_teleop_algae:.1f}")
    else:
        st.metric("Avg Algae Removed", "N/A")

# Detailed Teleop Coral Stats
st.markdown("#### Teleop Coral Scored")
st.markdown("Average number of coral scored per match in each level during teleop.")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if 'teleop_coral_l1' in team_data.columns:
        avg_teleop_coral_l1 = team_data['teleop_coral_l1'].mean()
        st.metric("Avg Level 1 Coral", f"{avg_teleop_coral_l1:.1f}")
    else:
        st.metric("Avg Level 1 Coral", "N/A")
with col2:
    if 'teleop_coral_l2' in team_data.columns:
        avg_teleop_coral_l2 = team_data['teleop_coral_l2'].mean()
        st.metric("Avg Level 2 Coral", f"{avg_teleop_coral_l2:.1f}")
    else:
        st.metric("Avg Level 2 Coral", "N/A")
with col3:
    if 'teleop_coral_l3' in team_data.columns:
        avg_teleop_coral_l3 = team_data['teleop_coral_l3'].mean()
        st.metric("Avg Level 3 Coral", f"{avg_teleop_coral_l3:.1f}")
    else:
        st.metric("Avg Level 3 Coral", "N/A")
with col4:
    if 'teleop_coral_l4' in team_data.columns:
        avg_teleop_coral_l4 = team_data['teleop_coral_l4'].mean()
        st.metric("Avg Level 4 Coral", f"{avg_teleop_coral_l4:.1f}")
    else:
        st.metric("Avg Level 4 Coral", "N/A")

st.markdown("#### Teleop Coral Missed")
st.markdown("Average number of coral missed per match in each level during teleop.")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if 'teleop_missed_coral_l1' in team_data.columns:
        avg_teleop_missed_l1 = team_data['teleop_missed_coral_l1'].mean()
        st.metric("Avg Missed Level 1", f"{avg_teleop_missed_l1:.1f}")
    else:
        st.metric("Avg Missed Level 1", "N/A")
with col2:
    if 'teleop_missed_coral_l2' in team_data.columns:
        avg_teleop_missed_l2 = team_data['teleop_missed_coral_l2'].mean()
        st.metric("Avg Missed Level 2", f"{avg_teleop_missed_l2:.1f}")
    else:
        st.metric("Avg Missed Level 2", "N/A")
with col3:
    if 'teleop_missed_coral_l3' in team_data.columns:
        avg_teleop_missed_l3 = team_data['teleop_missed_coral_l3'].mean()
        st.metric("Avg Missed Level 3", f"{avg_teleop_missed_l3:.1f}")
    else:
        st.metric("Avg Missed Level 3", "N/A")
with col4:
    if 'teleop_missed_coral_l4' in team_data.columns:
        avg_teleop_missed_l4 = team_data['teleop_missed_coral_l4'].mean()
        st.metric("Avg Missed Level 4", f"{avg_teleop_missed_l4:.1f}")
    else:
        st.metric("Avg Missed Level 4", "N/A")

# Detailed Teleop Algae Stats
st.markdown("#### Teleop Algae Management")
st.markdown("Average algae managed per match during teleop (to barge, processor, and removed).")
col1, col2, col3 = st.columns(3)
with col1:
    if 'teleop_algae_barge' in team_data.columns:
        avg_teleop_algae_barge = team_data['teleop_algae_barge'].mean()
        st.metric("Avg Algae to Barge", f"{avg_teleop_algae_barge:.1f}")
    else:
        st.metric("Avg Algae to Barge", "N/A")
with col2:
    if 'teleop_algae_processor' in team_data.columns:
        avg_teleop_algae_processor = team_data['teleop_algae_processor'].mean()
        st.metric("Avg Algae to Processor", f"{avg_teleop_algae_processor:.1f}")
    else:
        st.metric("Avg Algae to Processor", "N/A")
with col3:
    if 'teleop_missed_algae_barge' in team_data.columns and 'teleop_missed_algae_processor' in team_data.columns:
        total_missed_algae = (team_data['teleop_missed_algae_barge'] + team_data['teleop_missed_algae_processor']).mean()
        st.metric("Avg Missed Algae", f"{total_missed_algae:.1f}")
    else:
        st.metric("Avg Missed Algae", "N/A")

# Endgame Statistics
st.markdown("### Endgame Statistics")
st.markdown("Performance metrics for the endgame phase, including parking and climbing.")
col1, col2, col3 = st.columns(3)
with col1:
    if 'endgame_score' in team_data.columns:
        avg_endgame_score = team_data['endgame_score'].mean()
        st.metric("Avg Endgame Score", f"{avg_endgame_score:.1f}")
    else:
        st.metric("Avg Endgame Score", "N/A")
with col2:
    if 'climb_status' in team_data.columns:
        park_rate = (team_data['climb_status'] == 'Parked').mean() * 100
        st.metric("Park Rate", f"{park_rate:.1f}%")
    else:
        st.metric("Park Rate", "N/A")
with col3:
    if 'climb_status' in team_data.columns:
        climb_rate = ((team_data['climb_status'] == 'Shallow Climb') | (team_data['climb_status'] == 'Deep Climb')).mean() * 100
        st.metric("Climb Rate", f"{climb_rate:.1f}%")
    else:
        st.metric("Climb Rate", "N/A")

# Climb Status Breakdown
st.markdown("#### Climb Status Breakdown")
st.markdown("Distribution of endgame outcomes (parked, shallow climb, deep climb, or no climb).")
if 'climb_status' in team_data.columns:
    climb_counts = team_data['climb_status'].value_counts().reset_index()
    climb_counts.columns = ['Climb Status', 'Count']
    fig = px.pie(climb_counts, names='Climb Status', values='Count', title="Climb Status Distribution")
    st.plotly_chart(fig, use_container_width=True)

# Performance Ratings
st.markdown("### Performance Ratings")
st.markdown("Average ratings for defense, speed, and driver skill, as assessed by scouters (1 to 5).")
col1, col2, col3 = st.columns(3)
with col1:
    if 'defense_rating' in team_data.columns:
        avg_defense = team_data['defense_rating'].mean()
        st.metric("Avg Defense Rating", f"{avg_defense:.1f}")
    else:
        st.metric("Avg Defense Rating", "N/A")
with col2:
    if 'speed_rating' in team_data.columns:
        avg_speed = team_data['speed_rating'].mean()
        st.metric("Avg Speed Rating", f"{avg_speed:.1f}")
    else:
        st.metric("Avg Speed Rating", "N/A")
with col3:
    if 'driver_skill_rating' in team_data.columns:
        avg_driver_skill = team_data['driver_skill_rating'].mean()
        st.metric("Avg Driver Skill", f"{avg_driver_skill:.1f}")
    else:
        st.metric("Avg Driver Skill", "N/A")

# Score Trend Over Matches
st.markdown("### Score Trend Over Matches")
st.markdown("Trend of the team's total score across matches, showing improvement or decline.")
if 'match_number' in team_data.columns:
    score_trend = team_data.groupby('match_number')['total_score'].mean().reset_index()
    fig = px.line(score_trend, x='match_number', y='total_score', title=f"Score Trend for Team {selected_team}")
    st.plotly_chart(fig, use_container_width=True)

# Scoring Accuracy Analysis (retained from current version)
st.write("### Scoring Accuracy Analysis")
# Coral Success Ratio
coral_scored_cols = [f"{period}_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
coral_missed_cols = [f"{period}_missed_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
team_data['total_coral_scored'] = team_data[coral_scored_cols].sum(axis=1)
team_data['total_coral_missed'] = team_data[coral_missed_cols].sum(axis=1)
team_data['total_coral_attempts'] = team_data['total_coral_scored'] + team_data['total_coral_missed']
team_data['coral_success_ratio'] = team_data['total_coral_scored'] / team_data['total_coral_attempts'].replace(0, pd.NA)
avg_coral_success = team_data['coral_success_ratio'].mean() * 100 if not team_data['coral_success_ratio'].isna().all() else 0

# Algae Success Ratio
algae_scored_cols = [f"{period}_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
algae_missed_cols = [f"{period}_missed_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
team_data['total_algae_scored'] = team_data[algae_scored_cols].sum(axis=1)
team_data['total_algae_missed'] = team_data[algae_missed_cols].sum(axis=1)
team_data['total_algae_attempts'] = team_data['total_algae_scored'] + team_data['total_algae_missed']
team_data['algae_success_ratio'] = team_data['total_algae_scored'] / team_data['total_algae_attempts'].replace(0, pd.NA)
avg_algae_success = team_data['algae_success_ratio'].mean() * 100 if not team_data['algae_success_ratio'].isna().all() else 0

col1, col2 = st.columns(2)
with col1:
    st.metric("Coral Success Ratio", f"{avg_coral_success:.1f}%")
with col2:
    st.metric("Algae Success Ratio", f"{avg_algae_success:.1f}%")

# EPA (Expected Points Added) (retained from current version)
st.write("### Expected Points Added (EPA)")
# Simple EPA calculation: average points above/below alliance average per match
epa_values = []
for match in team_data['match_number'].unique():
    match_data = df[df['match_number'] == match]
    alliance_data = match_data[match_data['alliance_color'] == team_data[team_data['match_number'] == match]['alliance_color'].iloc[0]]
    alliance_avg = alliance_data['total_score'].mean()
    team_score = team_data[team_data['match_number'] == match]['total_score'].iloc[0]
    epa_values.append(team_score - alliance_avg)
avg_epa = sum(epa_values) / len(epa_values) if epa_values else 0
st.write(f"Average EPA: {avg_epa:.2f} points")

# Qualitative Assessments
st.markdown("### Qualitative Assessments")
st.markdown("Scouter observations and comments for each match.")
if 'auto_qa' in team_data.columns:
    st.markdown("#### Autonomous Observations")
    for idx, row in team_data.iterrows():
        if row['auto_qa']:
            st.markdown(f"- Match {row['match_number']}: {row['auto_qa']}")

if 'teleop_qa' in team_data.columns:
    st.markdown("#### Teleop Observations")
    for idx, row in team_data.iterrows():
        if row['teleop_qa']:
            st.markdown(f"- Match {row['match_number']}: {row['teleop_qa']}")

if 'defense_qa' in team_data.columns:
    st.markdown("#### Defense Observations")
    for idx, row in team_data.iterrows():
        if row['defense_qa']:
            st.markdown(f"- Match {row['match_number']}: {row['defense_qa']}")

if 'comments' in team_data.columns:
    st.markdown("#### Additional Comments")
    for idx, row in team_data.iterrows():
        if row['comments']:
            st.markdown(f"- Match {row['match_number']}: {row['comments']}")

# Display raw team data (retained from current version)
st.write("### Raw Data")
st.dataframe(team_data)