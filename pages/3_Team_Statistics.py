# pages/3_Team_Statistics.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, calculate_match_score
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Team Statistics", page_icon="📊")

# Auto-refresh every 10 seconds (10000 milliseconds)
st_autorefresh(interval=10000, key="team_statistics_refresh")

st.title("Team Statistics")
st.info("This page automatically updates every 10 seconds to reflect new scouting data.")

# Load data
df = load_data()

if df is None or df.empty:
    st.info("No match data available for team statistics.")
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
        'climb_status', 'auto_taxi_left'
    ]
    if all(col in df.columns for col in required_cols):
        df = df.join(df.apply(calculate_match_score, axis=1))
    else:
        st.warning("Cannot calculate match scores. Missing required columns.")
        st.stop()

    # Team selection
    if 'team_number' in df.columns:
        team_numbers = sorted(df['team_number'].dropna().unique())
        selected_team = st.selectbox("Select a Team", options=team_numbers)
    else:
        st.error("Team number data not available.")
        st.stop()

    # Filter data for the selected team
    team_data = df[df['team_number'] == selected_team]

    if team_data.empty:
        st.info(f"No data available for Team {selected_team}.")
    else:
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
        if 'climb_status' in team_data.columns:
            st.markdown("#### Climb Status Breakdown")
            st.markdown("Distribution of endgame outcomes (parked, shallow climb, deep climb, or no climb).")
            climb_counts = team_data['climb_status'].value_counts(normalize=True) * 100
            climb_df = pd.DataFrame({
                'Climb Status': climb_counts.index,
                'Percentage': climb_counts.values
            })
            fig = px.pie(climb_df, names='Climb Status', values='Percentage', title='Climb Status Distribution')
            st.plotly_chart(fig, use_container_width=True)

        # Performance Ratings
        st.markdown("### Performance Ratings")
        st.markdown("Average ratings for defense, speed, and driver skill, as assessed by scouters (0 to 5).")
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
        if 'match_number' in team_data.columns and 'total_score' in team_data.columns:
            st.markdown("### Score Trend Over Matches")
            st.markdown("Trend of the team's total score across matches, showing improvement or decline.")
            trend_data = team_data.sort_values('match_number')
            fig = px.line(trend_data, x='match_number', y='total_score', title='Total Score Trend',
                          labels={'match_number': 'Match Number', 'total_score': 'Total Score'})
            st.plotly_chart(fig, use_container_width=True)

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