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

# Create a copy of the DataFrame for the leaderboard (unfiltered by team selection)
df_leaderboard = df.copy()

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
    if col in df_leaderboard.columns:
        df_leaderboard[col] = pd.to_numeric(df_leaderboard[col], errors='coerce')

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
    df_leaderboard = df_leaderboard.join(df_leaderboard.apply(calculate_match_score, axis=1))

    # Calculate alliance-level bonuses
    def calculate_alliance_bonuses(df):
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

        alliance_climb = df.groupby(['match_number', 'alliance_color'])['climb_status'].value_counts().unstack(fill_value=0)
        alliance_climb['num_robots'] = df.groupby(['match_number', 'alliance_color'])['team_number'].nunique()
        alliance_climb['num_climbs'] = alliance_climb.get('Shallow Climb', 0) + alliance_climb.get('Deep Climb', 0)
        alliance_climb['harmony_bonus'] = alliance_climb.apply(
            lambda row: 15 if row['num_climbs'] == row['num_robots'] and row['num_robots'] > 0 else 0, axis=1
        )

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

        df['total_score'] = (
            df['total_score'] +
            df['coop_bonus'].fillna(0) +
            df['harmony_bonus'].fillna(0)
        )

        return df

    df = calculate_alliance_bonuses(df)
    df_leaderboard = calculate_alliance_bonuses(df_leaderboard)
else:
    st.warning("Cannot calculate match scores. Missing required columns.")
    st.stop()

# Calculate match outcomes (wins/losses/ties) for the leaderboard
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

df_leaderboard = calculate_match_outcomes(df_leaderboard)

# Team selection for detailed analysis
if 'team_number' in df.columns:
    team_numbers = sorted(df['team_number'].dropna().unique())
    selected_teams = st.multiselect("Select Teams to Analyze (Leave blank to analyze all)", options=team_numbers)
    if selected_teams:
        df = df[df['team_number'].isin(selected_teams)]
else:
    st.error("Team number data not available.")
    st.stop()

# Leaderboard Section
st.subheader("🏆 Team Leaderboard")
st.markdown("Teams are ranked based on multiple metrics in the following order: Average Total Score, Average Objects Scored, Climb Success Rate, and Average Total Score (again). Teams with tied values receive the same rank.")

# Cache the leaderboard calculations for performance
@st.cache_data
def compute_leaderboard(df_leaderboard):
    # Calculate metrics for the leaderboard
    # 1. Total matches played
    matches_played = df_leaderboard.groupby('team_number')['match_number'].nunique().reset_index(name='Matches Played')

    # 2. Wins, Losses, Ties
    win_loss = df_leaderboard.groupby('team_number')['match_outcome_final'].value_counts().unstack(fill_value=0).reset_index()
    win_loss = win_loss.rename(columns={'Won': 'Wins', 'Lost': 'Losses', 'Tie': 'Ties'})
    if 'Wins' not in win_loss.columns:
        win_loss['Wins'] = 0
    if 'Losses' not in win_loss.columns:
        win_loss['Losses'] = 0
    if 'Ties' not in win_loss.columns:
        win_loss['Ties'] = 0

    # 3. Average Total Score
    avg_metrics = df_leaderboard.groupby('team_number').agg({
        'total_score': 'mean'
    }).reset_index()
    avg_metrics = avg_metrics.rename(columns={'total_score': 'Avg Total Score'})

    # 4. Total Objects Scored (Coral + Algae)
    df_leaderboard['total_coral_scored'] = df_leaderboard[[f"{period}_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]].sum(axis=1)
    df_leaderboard['total_algae_scored'] = df_leaderboard[[f"{period}_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]].sum(axis=1)
    df_leaderboard['total_objects_scored'] = df_leaderboard['total_coral_scored'] + df_leaderboard['total_algae_scored']
    avg_objects = df_leaderboard.groupby('team_number')['total_objects_scored'].mean().reset_index(name='Avg Objects Scored')

    # 5. Climb Success Rate
    df_leaderboard['successful_climb'] = df_leaderboard['climb_status'].isin(['Shallow Climb', 'Deep Climb']).astype(int)
    climb_success = df_leaderboard.groupby('team_number')['successful_climb'].mean().reset_index(name='Climb Success Rate')
    climb_success['Climb Success Rate'] = climb_success['Climb Success Rate'] * 100  # Convert to percentage

    # Combine all metrics into a leaderboard DataFrame
    leaderboard = matches_played.merge(win_loss, on='team_number', how='left')
    leaderboard = leaderboard.merge(avg_metrics, on='team_number', how='left')
    leaderboard = leaderboard.merge(avg_objects, on='team_number', how='left')
    leaderboard = leaderboard.merge(climb_success, on='team_number', how='left')

    # Rename team_number for display
    leaderboard = leaderboard.rename(columns={'team_number': 'Team Number'})

    # Round numerical columns to 2 decimal places
    leaderboard['Avg Total Score'] = leaderboard['Avg Total Score'].round(2)
    leaderboard['Avg Objects Scored'] = leaderboard['Avg Objects Scored'].round(2)
    leaderboard['Climb Success Rate'] = leaderboard['Climb Success Rate'].round(2)

    return leaderboard

# Compute the leaderboard
leaderboard = compute_leaderboard(df_leaderboard)

# Sort the leaderboard using multiple metrics in order
# Primary: Avg Total Score (since EPA is removed)
# Secondary: Avg Objects Scored
# Tertiary: Climb Success Rate
# Quaternary: Avg Total Score (again, as requested)
leaderboard = leaderboard.sort_values(
    by=['Avg Total Score', 'Avg Objects Scored', 'Climb Success Rate', 'Avg Total Score'],
    ascending=[False, False, False, False]
)

# Sort the leaderboard using multiple metrics in order
leaderboard = leaderboard.sort_values(
    by=['Avg Total Score', 'Avg Objects Scored', 'Climb Success Rate', 'Avg Total Score'],
    ascending=[False, False, False, False]
)

# Add a Rank column based on the sorted order, handling ties
# Use rank() directly on the sorted DataFrame to assign ranks starting from 1
# ascending=False ensures the highest values get the lowest rank number (i.e., Rank 1)
leaderboard['Rank'] = leaderboard.groupby(
    ['Avg Total Score', 'Avg Objects Scored', 'Climb Success Rate']
).ngroup().rank(method='min', ascending=False).astype(int)

# Reorder columns to put Rank first
cols = ['Rank', 'Team Number', 'Matches Played', 'Wins', 'Losses', 'Ties', 'Avg Total Score', 'Avg Objects Scored', 'Climb Success Rate']
leaderboard = leaderboard[cols]

# Display the leaderboard with styling, formatting numbers to 2 decimal places
st.dataframe(
    leaderboard.style.set_table_styles(
        [
            {'selector': 'th', 'props': [('font-size', '12px'), ('text-align', 'center'), ('font-weight', 'bold')]},
            {'selector': 'td', 'props': [('font-size', '12px'), ('text-align', 'center')]}
        ]
    ).set_properties(**{'min-width': '60px'})
    .format(
        {
            'Avg Total Score': '{:.2f}',
            'Avg Objects Scored': '{:.2f}',
            'Climb Success Rate': '{:.2f}'
        }
    ),  # Ensure columns are wide enough and formatted to 2 decimal places
    use_container_width=True
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
coral_scored_cols = [f"{period}_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
coral_missed_cols = [f"{period}_missed_coral_l{level}" for period in ['auto', 'teleop'] for level in range(1, 5)]
df['total_coral_scored'] = df[coral_scored_cols].sum(axis=1)
df['total_coral_missed'] = df[coral_missed_cols].sum(axis=1)
df['total_coral_attempts'] = df['total_coral_scored'] + df['total_coral_missed']
df['coral_success_ratio'] = df['total_coral_scored'] / df['total_coral_attempts'].replace(0, pd.NA)
avg_coral_success = df.groupby('team_number')['coral_success_ratio'].mean() * 100

algae_scored_cols = [f"{period}_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
algae_missed_cols = [f"{period}_missed_algae_{target}" for period in ['auto', 'teleop'] for target in ['barge', 'processor']]
df['total_algae_scored'] = df[algae_scored_cols].sum(axis=1)
df['total_algae_missed'] = df[algae_missed_cols].sum(axis=1)
df['total_algae_attempts'] = df['total_algae_scored'] + df['total_algae_missed']
df['algae_success_ratio'] = df['total_algae_scored'] / df['total_algae_attempts'].replace(0, pd.NA)
avg_algae_success = df.groupby('team_number')['algae_success_ratio'].mean() * 100

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

# Get any additional columns (e.g., calculated fields like total_score, etc.)
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