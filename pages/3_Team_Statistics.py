# pages/3_Team_Statistics.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, calculate_match_score

st.title("Team Statistics")

# Load data
df = load_data()

if df.empty:
    st.warning("No scouting data available. Please add match data first.")
else:
    # Calculate scores for all matches
    df = df.join(df.apply(calculate_match_score, axis=1))

    # Team selector
    selected_team = st.selectbox("Select Team", options=sorted(df['team_number'].unique()))

    # Filter data for the selected team
    team_data = df[df['team_number'] == selected_team].drop_duplicates(subset='match_number')

    # Match Summary
    st.subheader("Match Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Total Score", f"{team_data['total_score'].mean():.1f}")
        st.metric("Average Auto Score", f"{team_data['auto_score'].mean():.1f}")
    with col2:
        st.metric("Average Teleop Score", f"{team_data['teleop_score'].mean():.1f}")
        st.metric("Average Endgame Score", f"{team_data['endgame_score'].mean():.1f}")
    with col3:
        st.metric("Total Matches", len(team_data))
        if 'match_result' in team_data.columns:
            wins = team_data['match_result'].value_counts().get('Win', 0)
            losses = team_data['match_result'].value_counts().get('Loss', 0)
            ties = team_data['match_result'].value_counts().get('Tie', 0)
            win_rate = wins / (wins + losses + ties) if (wins + losses + ties) > 0 else 0
            st.metric("Win Rate", f"{win_rate:.1%}")

    # Team Ranking
    team_averages = df.groupby('team_number')['total_score'].mean().sort_values(ascending=False).reset_index()
    team_averages['rank'] = team_averages.index + 1
    team_rank = team_averages[team_averages['team_number'] == selected_team]['rank'].values[0]
    st.write(f"Team {selected_team} is ranked #{team_rank} based on average total score.")

    # Score Visualization
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

    # Team Statistics Section
    st.subheader("Team Statistics")

    # Scoring Breakdown
    st.markdown("#### Scoring Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Autonomous Scoring**")
        if all(col in team_data.columns for col in ['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']):
            st.write(f"Avg Coral Scored on L1: {team_data['auto_coral_l1'].mean():.3f}")
            st.write(f"Avg Coral Scored on L2: {team_data['auto_coral_l2'].mean():.3f}")
            st.write(f"Avg Coral Scored on L3: {team_data['auto_coral_l3'].mean():.3f}")
            st.write(f"Avg Coral Scored on L4: {team_data['auto_coral_l4'].mean():.3f}")
        else:
            st.write("Autonomous coral scoring data not available.")

        if all(col in team_data.columns for col in ['auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed']):
            st.write(f"Avg Algae Scored on Barge: {team_data['auto_algae_barge'].mean():.3f}")
            st.write(f"Avg Algae Scored on Processor: {team_data['auto_algae_processor'].mean():.3f}")
            st.write(f"Avg Algae Removed from Reef: {team_data['auto_algae_removed'].mean():.3f}")
        else:
            st.write("Autonomous algae management data not available.")

    with col2:
        st.markdown("**Teleop Scoring**")
        if all(col in team_data.columns for col in ['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']):
            st.write(f"Avg Coral Scored on L1: {team_data['teleop_coral_l1'].mean():.3f}")
            st.write(f"Avg Coral Scored on L2: {team_data['teleop_coral_l2'].mean():.3f}")
            st.write(f"Avg Coral Scored on L3: {team_data['teleop_coral_l3'].mean():.3f}")
            st.write(f"Avg Coral Scored on L4: {team_data['teleop_coral_l4'].mean():.3f}")
        else:
            st.write("Teleop coral scoring data not available.")

        if all(col in team_data.columns for col in ['teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed']):
            st.write(f"Avg Algae Scored on Barge: {team_data['teleop_algae_barge'].mean():.3f}")
            st.write(f"Avg Algae Scored on Processor: {team_data['teleop_algae_processor'].mean():.3f}")
            st.write(f"Avg Algae Removed from Reef: {team_data['teleop_algae_removed'].mean():.3f}")
        else:
            st.write("Teleop algae management data not available.")

    # Consistency Metrics
    st.markdown("#### Consistency Metrics")
    col1, col2 = st.columns(2)
    with col1:
        auto_score_std = team_data['auto_score'].std()
        st.write(f"Auto Score Variability (Std Dev): {auto_score_std:.1f}")
    with col2:
        teleop_score_std = team_data['teleop_score'].std()
        st.write(f"Teleop Score Variability (Std Dev): {teleop_score_std:.1f}")

    # Endgame Statistics
    st.markdown("#### Endgame Statistics")
    if 'climb_status' in team_data.columns:
        climb_counts = team_data['climb_status'].value_counts()
        total_matches = len(team_data)
        climb_success_rate = (climb_counts.get('Shallow Climb', 0) + climb_counts.get('Deep Climb', 0)) / total_matches * 100
        st.write(f"Climb Success Rate (Shallow/Deep): {climb_success_rate:.1f}%")
        st.write("Climb Status Breakdown:")
        for status, count in climb_counts.items():
            st.write(f"- {status}: {count} matches ({count/total_matches*100:.1f}%)")
    else:
        st.write("Climb status data not available.")

    # Performance Ratings
    st.markdown("#### Performance Ratings")
    if all(col in team_data.columns for col in ['defense_rating', 'speed_rating', 'driver_skill_rating']):
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
    st.dataframe(team_data[available_cols].sort_values('match_number', ascending=False))