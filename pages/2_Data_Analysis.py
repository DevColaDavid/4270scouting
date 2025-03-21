# pages/3_Data_Analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.utils import load_data, calculate_match_score

st.set_page_config(page_title="Data Analysis", page_icon="📈", layout="wide")

st.title("Data Analysis")

# Load data
df = load_data()

if df is None or df.empty:
    st.info("No match data available for analysis.")
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

    # Team selection for detailed analysis
    if 'team_number' in df.columns:
        team_numbers = sorted(df['team_number'].dropna().unique())
        selected_teams = st.multiselect("Select Teams to Analyze (Leave blank to analyze all)", options=team_numbers)
        if selected_teams:
            df = df[df['team_number'].isin(selected_teams)]
    else:
        st.error("Team number data not available.")
        st.stop()

    # Score Distribution
    st.subheader("Score Distribution")
    if 'total_score' in df.columns:
        fig = px.histogram(df, x='total_score', color='team_number', marginal="box",
                           title="Total Score Distribution by Team",
                           labels={'total_score': 'Total Score'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Total score data not available for visualization.")

    # Autonomous vs Teleop Performance
    st.subheader("Autonomous vs Teleop Performance")
    if 'auto_score' in df.columns and 'teleop_score' in df.columns:
        fig = px.scatter(df, x='auto_score', y='teleop_score', color='team_number',
                         size='endgame_score', hover_data=['match_number'],
                         title="Autonomous vs Teleop Scores (Size = Endgame Score)",
                         labels={'auto_score': 'Autonomous Score', 'teleop_score': 'Teleop Score'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Autonomous or Teleop score data not available for visualization.")

    # Taxi Rate by Team
    st.subheader("Taxi Rate by Team")
    if 'auto_taxi_left' in df.columns:
        taxi_rates = df.groupby('team_number')['auto_taxi_left'].mean() * 100
        taxi_df = pd.DataFrame({
            'Team Number': taxi_rates.index,
            'Taxi Rate (%)': taxi_rates.values
        })
        fig = px.bar(taxi_df, x='Team Number', y='Taxi Rate (%)', title="Percentage of Matches with Successful Taxi",
                     labels={'Team Number': 'Team Number', 'Taxi Rate (%)': 'Taxi Rate (%)'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Taxi data not available for visualization.")

    # Climb and Park Rates by Team
    st.subheader("Climb and Park Rates by Team")
    if 'climb_status' in df.columns:
        climb_stats = df.groupby('team_number')['climb_status'].value_counts(normalize=True).unstack(fill_value=0) * 100
        climb_stats = climb_stats.reset_index()
        fig = go.Figure()
        for status in ['Parked', 'Shallow Climb', 'Deep Climb']:
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
    else:
        st.warning("Climb status data not available for visualization.")

    # Performance Ratings
    st.subheader("Performance Ratings")
    if 'defense_rating' in df.columns and 'speed_rating' in df.columns and 'driver_skill_rating' in df.columns:
        ratings = df.groupby('team_number')[['defense_rating', 'speed_rating', 'driver_skill_rating']].mean().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ratings['defense_rating'],
            y=ratings['team_number'],
            name='Defense Rating',
            orientation='h'
        ))
        fig.add_trace(go.Bar(
            x=ratings['speed_rating'],
            y=ratings['team_number'],
            name='Speed Rating',
            orientation='h'
        ))
        fig.add_trace(go.Bar(
            x=ratings['driver_skill_rating'],
            y=ratings['team_number'],
            name='Driver Skill Rating',
            orientation='h'
        ))
        fig.update_layout(
            barmode='group',
            title="Average Performance Ratings by Team",
            xaxis_title="Rating",
            yaxis_title="Team Number",
            legend_title="Rating Type"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Performance rating data not available for visualization.")

    # Key Insights
    st.subheader("Key Insights")
    if 'total_score' in df.columns:
        top_scorers = df.groupby('team_number')['total_score'].mean().sort_values(ascending=False).head(3)
        st.markdown("#### Top Scoring Teams")
        for team, score in top_scorers.items():
            st.markdown(f"- Team {team}: Average score of {score:.1f}")

    if 'auto_taxi_left' in df.columns:
        top_taxi = df.groupby('team_number')['auto_taxi_left'].mean().sort_values(ascending=False).head(3)
        st.markdown("#### Top Taxi Teams")
        for team, rate in top_taxi.items():
            if rate > 0:
                st.markdown(f"- Team {team}: Taxied in {rate*100:.1f}% of matches")

    if 'climb_status' in df.columns:
        top_park = df[df['climb_status'] == 'Parked'].groupby('team_number').size().div(df.groupby('team_number').size()).sort_values(ascending=False).head(3)
        top_climb = df[df['climb_status'].isin(['Shallow Climb', 'Deep Climb'])].groupby('team_number').size().div(df.groupby('team_number').size()).sort_values(ascending=False).head(3)
        st.markdown("#### Top Parking Teams")
        for team, rate in top_park.items():
            if rate > 0:
                st.markdown(f"- Team {team}: Parked in {rate*100:.1f}% of matches")
        st.markdown("#### Top Climbing Teams")
        for team, rate in top_climb.items():
            if rate > 0:
                st.markdown(f"- Team {team}: Climbed in {rate*100:.1f}% of matches")

    if 'defense_rating' in df.columns:
        top_defenders = df.groupby('team_number')['defense_rating'].mean().sort_values(ascending=False).head(3)
        st.markdown("#### Top Defenders")
        for team, rating in top_defenders.items():
            st.markdown(f"- Team {team}: Average defense rating of {rating:.1f}")