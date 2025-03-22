import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.utils import load_data, calculate_match_score
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

    # Calculate EPA (retained from current version)
    def calculate_epa(df):
        epa_values = []
        for idx, row in df.iterrows():
            match_data = df[df['match_number'] == row['match_number']]
            alliance_data = match_data[match_data['alliance_color'] == row['alliance_color']]
            alliance_avg = alliance_data['total_score'].mean()
            team_score = row['total_score']
            epa = team_score - alliance_avg
            epa_values.append(epa)
        df['epa'] = epa_values
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

# Scoring Accuracy Analysis (retained from current version)
st.subheader("Scoring Accuracy Analysis")
# Coral Success Ratio
coral_scored_cols = [f"{period}_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
coral_missed_cols = [f"{period}_missed_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
df['total_coral_scored'] = df[coral_scored_cols].sum(axis=1)
df['total_coral_missed'] = df[coral_missed_cols].sum(axis=1)
df['total_coral_attempts'] = df['total_coral_scored'] + df['total_coral_missed']
df['coral_success_ratio'] = df['total_coral_scored'] / df['total_coral_attempts'].replace(0, pd.NA)
avg_coral_success = df.groupby('team_number')['coral_success_ratio'].mean() * 100

# Algae Success Ratio
algae_scored_cols = [f"{period}_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
algae_missed_cols = [f"{period}_missed_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
df['total_algae_scored'] = df[algae_scored_cols].sum(axis=1)
df['total_algae_missed'] = df[algae_missed_cols].sum(axis=1)
df['total_algae_attempts'] = df['total_algae_scored'] + df['total_algae_missed']
df['algae_success_ratio'] = df['total_algae_scored'] / df['total_algae_attempts'].replace(0, pd.NA)
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
st.dataframe(df, use_container_width=True)

# Download button for raw data
csv = df.to_csv(index=False)
st.download_button(
    label="Download Raw Data as CSV",
    data=csv,
    file_name="scouting_data.csv",
    mime="text/csv"
)