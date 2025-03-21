# pages/3_Team_Statistics.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, calculate_match_score

st.title("Team Statistics")

# Load data
df = load_data()

if df is None or df.empty:
    st.warning("No scouting data available. Please add match data first.")
else:
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

    # Calculate scores for all matches
    required_cols = [
        'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
        'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
        'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
        'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
        'climb_status'
    ]
    if all(col in df.columns for col in required_cols):
        df = df.join(df.apply(calculate_match_score, axis=1))
    else:
        st.warning("Cannot calculate match scores. Missing required columns.")

    # Team selector
    if 'team_number' in df.columns:
        team_numbers = sorted(df['team_number'].dropna().unique())
        selected_team = st.selectbox("Select Team", options=team_numbers)
    else:
        st.error("Team number data not available.")
        st.stop()

    # Filter data for the selected team
    team_data = df[df['team_number'] == selected_team]
    # Drop duplicates based on match_number and scouter_name to handle multiple submissions
    if 'scouter_name' in team_data.columns:
        team_data = team_data.drop_duplicates(subset=['match_number', 'scouter_name'])
    else:
        team_data = team_data.drop_duplicates(subset=['match_number'])

    # Match Summary
    st.subheader("Match Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'total_score' in team_data.columns:
            st.metric("Average Total Score", f"{team_data['total_score'].mean():.1f}")
        else:
            st.metric("Average Total Score", "N/A")
        if 'auto_score' in team_data.columns:
            st.metric("Average Auto Score", f"{team_data['auto_score'].mean():.1f}")
        else:
            st.metric("Average Auto Score", "N/A")
    with col2:
        if 'teleop_score' in team_data.columns:
            st.metric("Average Teleop Score", f"{team_data['teleop_score'].mean():.1f}")
        else:
            st.metric("Average Teleop Score", "N/A")
        if 'endgame_score' in team_data.columns:
            st.metric("Average Endgame Score", f"{team_data['endgame_score'].mean():.1f}")
        else:
            st.metric("Average Endgame Score", "N/A")
    with col3:
        st.metric("Total Matches", len(team_data))
        if 'match_result' in team_data.columns:
            wins = team_data['match_result'].value_counts().get('Win', 0)
            losses = team_data['match_result'].value_counts().get('Loss', 0)
            ties = team_data['match_result'].value_counts().get('Tie', 0)
            total = wins + losses + ties
            win_rate = wins / total if total > 0 else 0
            st.metric("Win Rate", f"{win_rate:.1%}")
        else:
            st.metric("Win Rate", "N/A")

    # Team Ranking
    if 'total_score' in df.columns and 'team_number' in df.columns:
        team_averages = df.groupby('team_number')['total_score'].mean().sort_values(ascending=False).reset_index()
        team_averages['rank'] = team_averages.index + 1
        team_rank = team_averages[team_averages['team_number'] == selected_team]['rank'].values
        if len(team_rank) > 0:
            st.write(f"Team {selected_team} is ranked #{team_rank[0]} based on average total score.")
        else:
            st.write(f"Team {selected_team} has no total score data for ranking.")
    else:
        st.write("Team ranking not available due to missing total_score or team_number data.")

    # Score Visualization
    if all(col in df.columns for col in ['auto_score', 'teleop_score', 'endgame_score']):
        overall_avg = df[['auto_score', 'teleop_score', 'endgame_score']].mean()
        team_avg = team_data[['auto_score', 'teleop_score', 'endgame_score']].mean()
        fig = px.bar(
            x=['Auto', 'Teleop', 'Endgame'],
            y=[team_avg['auto_score'], team_avg['teleop_score'], team_avg['endgame_score']],
            labels={'x': 'Phase', 'y': 'Average Score'},
            title=f"Team {selected_team} Average Scores vs Overall Average",
        )
        fig.add_scatter(x=['Auto', 'Teleop', 'Endgame'], y=overall_avg, mode='lines+markers', name='Overall Average')
        st.plotly_chart(fig)
    else:
        st.warning("Score visualization not available due to missing score data.")

    # Team Statistics Section
    st.subheader("Team Statistics")

    # Scoring Breakdown
    st.markdown("#### Scoring Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Autonomous Scoring**")
        auto_coral_cols = ['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']
        if all(col in team_data.columns for col in auto_coral_cols):
            st.write(f"Avg Coral Scored on L1: {team_data['auto_coral_l1'].mean():.3f}")
            st.write(f"Avg Coral Scored on L2: {team_data['auto_coral_l2'].mean():.3f}")
            st.write(f"Avg Coral Scored on L3: {team_data['auto_coral_l3'].mean():.3f}")
            st.write(f"Avg Coral Scored on L4: {team_data['auto_coral_l4'].mean():.3f}")
        else:
            st.write("Autonomous coral scoring data not available.")

        auto_algae_cols = ['auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed']
        if all(col in team_data.columns for col in auto_algae_cols):
            st.write(f"Avg Algae Scored on Barge: {team_data['auto_algae_barge'].mean():.3f}")
            st.write(f"Avg Algae Scored on Processor: {team_data['auto_algae_processor'].mean():.3f}")
            st.write(f"Avg Algae Removed from Reef: {team_data['auto_algae_removed'].mean():.3f}")
        else:
            st.write("Autonomous algae management data not available.")

    with col2:
        st.markdown("**Teleop Scoring**")
        teleop_coral_cols = ['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']
        if all(col in team_data.columns for col in teleop_coral_cols):
            st.write(f"Avg Coral Scored on L1: {team_data['teleop_coral_l1'].mean():.3f}")
            st.write(f"Avg Coral Scored on L2: {team_data['teleop_coral_l2'].mean():.3f}")
            st.write(f"Avg Coral Scored on L3: {team_data['teleop_coral_l3'].mean():.3f}")
            st.write(f"Avg Coral Scored on L4: {team_data['teleop_coral_l4'].mean():.3f}")
        else:
            st.write("Teleop coral scoring data not available.")

        teleop_algae_cols = ['teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed']
        if all(col in team_data.columns for col in teleop_algae_cols):
            st.write(f"Avg Algae Scored on Barge: {team_data['teleop_algae_barge'].mean():.3f}")
            st.write(f"Avg Algae Scored on Processor: {team_data['teleop_algae_processor'].mean():.3f}")
            st.write(f"Avg Algae Removed from Reef: {team_data['teleop_algae_removed'].mean():.3f}")
        else:
            st.write("Teleop algae management data not available.")

    # Consistency Metrics
    st.markdown("#### Consistency Metrics")
    col1, col2 = st.columns(2)
    with col1:
        if 'auto_score' in team_data.columns:
            auto_score_std = team_data['auto_score'].std()
            st.write(f"Auto Score Variability (Std Dev): {auto_score_std:.1f}")
        else:
            st.write("Auto Score Variability: N/A")
    with col2:
        if 'teleop_score' in team_data.columns:
            teleop_score_std = team_data['teleop_score'].std()
            st.write(f"Teleop Score Variability (Std Dev): {teleop_score_std:.1f}")
        else:
            st.write("Teleop Score Variability: N/A")

    # Endgame Statistics
    st.markdown("#### Endgame Statistics")
    if 'climb_status' in team_data.columns:
        climb_counts = team_data['climb_status'].value_counts()
        total_matches = len(team_data)
        climb_success_rate = (climb_counts.get('Shallow Climb', 0) + climb_counts.get('Deep Climb', 0)) / total_matches * 100 if total_matches > 0 else 0
        st.write(f"Climb Success Rate (Shallow/Deep): {climb_success_rate:.1f}%")
        st.write("Climb Status Breakdown:")
        for status, count in climb_counts.items():
            percentage = (count / total_matches * 100) if total_matches > 0 else 0
            st.write(f"- {status}: {count} matches ({percentage:.1f}%)")
    else:
        st.write("Climb status data not available.")

    # Performance Ratings
    st.markdown("#### Performance Ratings")
    rating_cols = ['defense_rating', 'speed_rating', 'driver_skill_rating']
    if all(col in team_data.columns for col in rating_cols):
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_defense_rating = team_data['defense_rating'].mean()
            st.write(f"Average Defense Rating: {avg_defense_rating:.1f}")
        with col2:
            avg_speed_rating = team_data['speed_rating'].mean()
            st.write(f"Average Speed Rating: {avg_speed_rating:.1f}")
        with col3:
            avg_driver_skill_rating = team_data['driver_skill_rating'].mean()
            st.write(f"Average Driver Skill Rating: {avg_driver_skill_rating:.1f}")
    else:
        st.write("Performance ratings (defense, speed, driver skill) not available.")

    # Match History
    st.subheader("Match History")
    history_cols = ['match_number', 'match_result', 'total_score', 'auto_score', 'teleop_score', 'endgame_score', 'climb_status', 
                    'defense_rating', 'speed_rating', 'driver_skill_rating']
    available_cols = [col for col in history_cols if col in team_data.columns]
    if available_cols:
        display_df = team_data[available_cols].sort_values('match_number', ascending=False)
        st.dataframe(display_df)
    else:
        st.warning("No match history data available to display.")