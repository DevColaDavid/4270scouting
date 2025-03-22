import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
# Add the parent directory to the Python path to ensure utils can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.utils import load_data, calculate_match_score  # Corrected import for Scenario 2
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Data Analysis", page_icon="📊", layout="wide")

# Auto-refresh every 10 seconds (10000 milliseconds)
st_autorefresh(interval=10000, key="data_analysis_refresh")

st.title("📊 Data Analysis")
st.info("This page automatically updates every 10 seconds to reflect new scouting data.")

# Load data
df = load_data()

if df is None or df.empty:
    st.info("No match data available for analysis.")
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
score_columns = ['auto_score', 'teleop_score', 'endgame_score', 'total_score']
if all(col in df.columns for col in required_cols):
    # Only calculate scores if they don't already exist
    if not all(col in df.columns for col in score_columns):
        scores = df.apply(calculate_match_score, axis=1)
        df[score_columns] = scores

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

    # Calculate EPA (optimized)
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

# Calculate success ratios (needed for leaderboard and scoring accuracy analysis)
coral_scored_cols = [f"{period}_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
coral_missed_cols = [f"{period}_missed_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
df['total_coral_scored'] = df[coral_scored_cols].sum(axis=1)
df['total_coral_missed'] = df[coral_missed_cols].sum(axis=1)
df['total_coral_attempts'] = df['total_coral_scored'] + df['total_coral_missed']
df['coral_success_ratio'] = (df['total_coral_scored'] / df['total_coral_attempts'].replace(0, pd.NA)).fillna(0)

algae_scored_cols = [f"{period}_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
algae_missed_cols = [f"{period}_missed_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
df['total_algae_scored'] = df[algae_scored_cols].sum(axis=1)
df['total_algae_missed'] = df[algae_missed_cols].sum(axis=1)
df['total_algae_attempts'] = df['total_algae_scored'] + df['total_algae_missed']
df['algae_success_ratio'] = (df['total_algae_scored'] / df['total_algae_attempts'].replace(0, pd.NA)).fillna(0)

# Team Leaderboard
st.subheader("🏆 Team Leaderboard")
st.markdown("Teams ranked based on performance metrics. Select a metric to sort the table.")

# Calculate all metrics for the leaderboard
leaderboard_data = df.groupby('team_number').agg({
    'total_score': 'mean',           # Average Total Score
    'epa': 'mean',                   # Average EPA
    'coral_success_ratio': 'mean',   # Average Coral Success Ratio
    'algae_success_ratio': 'mean'    # Average Algae Success Ratio
}).reset_index()

# Convert success ratios to percentages
leaderboard_data['coral_success_ratio'] = leaderboard_data['coral_success_ratio'] * 100
leaderboard_data['algae_success_ratio'] = leaderboard_data['algae_success_ratio'] * 100

# Rename columns for display
leaderboard_data = leaderboard_data.rename(columns={
    'team_number': 'Team Number',
    'total_score': 'Average Total Score',
    'epa': 'Average EPA',
    'coral_success_ratio': 'Coral Success Ratio (%)',
    'algae_success_ratio': 'Algae Success Ratio (%)'
})

# Dropdown to select the sorting metric
sort_metric = st.selectbox(
    "Sort Leaderboard By",
    options=[
        "Average Total Score",
        "Average EPA",
        "Coral Success Ratio (%)",
        "Algae Success Ratio (%)"
    ],
    index=0  # Default to Average Total Score
)

# Map the display name back to the DataFrame column name for sorting
sort_column_map = {
    "Average Total Score": "Average Total Score",
    "Average EPA": "Average EPA",
    "Coral Success Ratio (%)": "Coral Success Ratio (%)",
    "Algae Success Ratio (%)": "Algae Success Ratio (%)"
}

# Sort the leaderboard based on the selected metric
leaderboard_data = leaderboard_data.sort_values(by=sort_column_map[sort_metric], ascending=False)

# Add rank based on the sorting metric, handle NaN values
ranks = leaderboard_data[sort_column_map[sort_metric]].rank(ascending=False, method='min')
# Fill NaN ranks with the maximum rank + 1 (or another default value)
max_rank = ranks.max() if not ranks.isna().all() else 0
leaderboard_data['Rank'] = ranks.fillna(max_rank + 1).astype(int)

# Reorder columns to put Rank first
leaderboard_data = leaderboard_data[[
    'Rank', 'Team Number', 'Average Total Score', 'Average EPA',
    'Coral Success Ratio (%)', 'Algae Success Ratio (%)'
]]

# Round the values for better readability
leaderboard_data['Average Total Score'] = leaderboard_data['Average Total Score'].round(2)
leaderboard_data['Average EPA'] = leaderboard_data['Average EPA'].round(2)
leaderboard_data['Coral Success Ratio (%)'] = leaderboard_data['Coral Success Ratio (%)'].round(2)
leaderboard_data['Algae Success Ratio (%)'] = leaderboard_data['Algae Success Ratio (%)'].round(2)

# Display the leaderboard
st.dataframe(
    leaderboard_data,
    use_container_width=True,
    hide_index=True
)

# Total Score Analysis
st.subheader("Total Score Analysis")
st.markdown("Distribution and trends of total scores across matches for each team.")
if 'total_score' in df.columns:
    # Histogram of Total Scores
    fig = px.histogram(df, x='total_score', color='team_number', marginal="box",
                       title="Total Score Distribution by Team",
                       labels={'total_score': 'Total Score'})
    st.plotly_chart(fig, use_container_width=True)

    # Line Chart: Total Score Trend Over Matches
    if 'match_number' in df.columns:
        trend_data = df.sort_values('match_number')
        fig = px.line(trend_data, x='match_number', y='total_score', color='team_number',
                      title='Total Score Trend Over Matches',
                      labels={'match_number': 'Match Number', 'total_score': 'Total Score'})
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Total score data not available for visualization.")

# EPA Analysis
st.subheader("Expected Points Added (EPA)")
st.markdown("EPA measures a team's contribution to their alliance's score relative to the average performance of teams in the same alliance color. Higher EPA indicates a greater positive impact.")
if 'epa' in df.columns:
    epa_data = df.groupby('team_number')['epa'].mean().reset_index()
    fig = px.bar(epa_data, x='team_number', y='epa', title='Average EPA by Team',
                 labels={'team_number': 'Team Number', 'epa': 'EPA'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("EPA data not available for visualization.")

# Climb Analysis
st.subheader("Climb Analysis")
st.markdown("Analysis of endgame performance, including parking and climbing statistics.")
if 'climb_status' in df.columns and 'endgame_score' in df.columns:
    # Climb and Park Rates by Team (Stacked Bar Chart)
    climb_stats = df.groupby('team_number')['climb_status'].value_counts(normalize=True).unstack(fill_value=0) * 100
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
    endgame_scores = df.groupby('team_number')['endgame_score'].mean().reset_index()
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
if all(col in df.columns for col in ['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']):
    auto_coral = df.groupby('team_number')[['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']].mean().reset_index()
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
if all(col in df.columns for col in ['auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4']):
    auto_missed_coral = df.groupby('team_number')[['auto_missed_coral_l1', 'auto_missed_coral_l2', 'auto_missed_coral_l3', 'auto_missed_coral_l4']].mean().reset_index()
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
if all(col in df.columns for col in ['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']):
    teleop_coral = df.groupby('team_number')[['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']].mean().reset_index()
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
if all(col in df.columns for col in ['teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4']):
    teleop_missed_coral = df.groupby('team_number')[['teleop_missed_coral_l1', 'teleop_missed_coral_l2', 'teleop_missed_coral_l3', 'teleop_missed_coral_l4']].mean().reset_index()
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
if all(col in df.columns for col in ['auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed', 'auto_missed_algae_barge', 'auto_missed_algae_processor']):
    auto_algae = df.groupby('team_number')[['auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed', 'auto_missed_algae_barge', 'auto_missed_algae_processor']].mean().reset_index()
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
if all(col in df.columns for col in ['teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor']):
    teleop_algae = df.groupby('team_number')[['teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed', 'teleop_missed_algae_barge', 'teleop_missed_algae_processor']].mean().reset_index()
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

# Taxi Rate by Team
st.subheader("Taxi Rate by Team")
st.markdown("Percentage of matches where each team successfully taxied (left starting position) during autonomous.")
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

# Scoring Accuracy Analysis
st.subheader("Scoring Accuracy Analysis")
avg_coral_success = df.groupby('team_number')['coral_success_ratio'].mean() * 100
avg_algae_success = df.groupby('team_number')['algae_success_ratio'].mean() * 100

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

# Raw Data
st.subheader("Raw Data")
st.markdown("Complete dataset for all matches, including all collected metrics. Use the table below to view and download the data.")

# Define the desired column order based on the Match Scouting form
desired_column_order = [
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
available_columns = [col for col in desired_column_order if col in df.columns]

# Get any additional columns (e.g., calculated fields like total_score, epa, etc.)
additional_columns = [col for col in df.columns if col not in desired_column_order]

# Combine the columns: desired order first, then additional columns
final_column_order = available_columns + additional_columns

# Reorder the DataFrame
df_reordered = df[final_column_order]

# Display the reordered DataFrame
st.dataframe(df_reordered, use_container_width=True)

# Download button for raw data
csv = df_reordered.to_csv(index=False)
st.download_button(
    label="Download Raw Data as CSV",
    data=csv,
    file_name="scouting_data.csv",
    mime="text/csv"
)