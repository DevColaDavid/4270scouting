import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, calculate_match_score

st.set_page_config(page_title="Team Statistics", page_icon="📊", layout="wide")

st.title("📊 Team Statistics")
st.markdown("View detailed statistics for each team based on historical scouting data.")

# Load data
df = load_data()

if df is None or df.empty:
    st.info("No match data available to display team statistics.")
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

# Convert team_number to string to ensure consistency
df['team_number'] = df['team_number'].astype(str)

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
else:
    st.warning("Cannot calculate match scores. Missing required columns.")
    st.stop()

# Check for duplicates in the data (same team_number and match_number)
duplicates = df[df.duplicated(subset=['team_number', 'match_number'], keep=False)]
if not duplicates.empty:
    st.warning("Duplicate form submissions detected for the same team and match number:")
    st.write(duplicates[['team_number', 'match_number', 'alliance_color', 'total_score']])
    # Deduplicate by keeping the first submission (or use timestamp if available)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values(by=['team_number', 'match_number', 'timestamp']).drop_duplicates(subset=['team_number', 'match_number'], keep='last')
        st.info("Duplicates resolved by keeping the most recent submission based on timestamp.")
    else:
        df = df.drop_duplicates(subset=['team_number', 'match_number'], keep='first')
        st.info("Duplicates resolved by keeping the first submission. Consider adding a timestamp column to prioritize more recent submissions.")

# Calculate success ratios and additional metrics
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

# Calculate match outcomes (wins/losses/ties) based on scores
def calculate_match_outcomes(df):
    # Standardize alliance_color values to title case
    df['alliance_color'] = df['alliance_color'].str.title()

    # Pivot the DataFrame to get red and blue scores per match
    scores_pivot = df.pivot_table(
        index='match_number',
        columns='alliance_color',
        values='total_score',
        aggfunc='sum'
    ).reset_index()

    # Check if 'Red' and 'Blue' columns exist, and fill with 0 if missing
    if 'Red' not in scores_pivot.columns:
        scores_pivot['Red'] = 0
    if 'Blue' not in scores_pivot.columns:
        scores_pivot['Blue'] = 0

    # Determine the winner of each match based on scores
    scores_pivot['calculated_winner'] = scores_pivot.apply(
        lambda row: 'Red' if row['Red'] > row['Blue'] else ('Blue' if row['Blue'] > row['Red'] else 'Tie'),
        axis=1
    )

    # Merge the calculated winner back into the original DataFrame
    df = df.merge(
        scores_pivot[['match_number', 'calculated_winner']],
        on='match_number',
        how='left'
    )

    # Compare manual match_outcome with calculated_winner
    def determine_outcome(row):
        manual_outcome = row['match_outcome']
        calculated_winner = row['calculated_winner']
        alliance_color = row['alliance_color']

        # If manual outcome is provided, use it and flag discrepancies
        if pd.notna(manual_outcome):
            # Convert manual outcome to match the calculated format for comparison
            if manual_outcome == 'Won':
                expected_winner = alliance_color
            elif manual_outcome == 'Lost':
                expected_winner = 'Blue' if alliance_color == 'Red' else 'Red'
            else:  # Tie
                expected_winner = 'Tie'

            # Check for discrepancies
            if expected_winner != calculated_winner:
                row['outcome_discrepancy'] = f"Manual: {manual_outcome}, Calculated: {calculated_winner}"
            else:
                row['outcome_discrepancy'] = None

            return manual_outcome
        else:
            # If no manual outcome, use the calculated winner
            if calculated_winner == 'Tie':
                return 'Tie'
            elif calculated_winner == alliance_color:
                return 'Won'
            else:
                return 'Lost'

    # Add outcome_discrepancy column
    df['outcome_discrepancy'] = None
    # Determine the final outcome (manual if provided, else calculated)
    df['match_outcome_final'] = df.apply(determine_outcome, axis=1)

    return df

df = calculate_match_outcomes(df)

# Display discrepancies if any
discrepancies = df[df['outcome_discrepancy'].notna()]
if not discrepancies.empty:
    st.warning("Discrepancies found between manual and calculated match outcomes:")
    st.write(discrepancies[['match_number', 'team_number', 'alliance_color', 'match_outcome', 'calculated_winner', 'outcome_discrepancy']])

# Team selection
if 'team_number' in df.columns:
    team_numbers = sorted(df['team_number'].unique())
    selected_team = st.selectbox("Select a Team", options=team_numbers)
else:
    st.error("Team number column not found in data.")
    st.stop()

# Filter data for the selected team
team_data = df[df['team_number'] == selected_team]

if team_data.empty:
    st.info(f"No data available for team {selected_team}.")
    st.stop()

# Check for duplicates in team_data (already handled globally, but let's confirm)
team_duplicates = team_data[team_data.duplicated(subset=['match_number'], keep=False)]
if not team_duplicates.empty:
    st.warning(f"Duplicate match numbers found for Team {selected_team}:")
    st.write(team_duplicates[['match_number', 'alliance_color', 'total_score']])

# Calculate team statistics with additional metrics
team_stats = team_data.groupby('team_number').agg({
    'total_score': 'mean',
    'auto_score': 'mean',
    'teleop_score': 'mean',
    'endgame_score': 'mean',
    'auto_coral_success': 'mean',
    'auto_coral_missed': 'mean',
    'teleop_coral_success': 'mean',
    'teleop_coral_missed': 'mean',
    'auto_coral_l1': 'mean',
    'auto_coral_l2': 'mean',
    'auto_coral_l3': 'mean',
    'auto_coral_l4': 'mean',
    'teleop_coral_l1': 'mean',
    'teleop_coral_l2': 'mean',
    'teleop_coral_l3': 'mean',
    'teleop_coral_l4': 'mean',
    'auto_missed_coral_l1': 'mean',
    'auto_missed_coral_l2': 'mean',
    'auto_missed_coral_l3': 'mean',
    'auto_missed_coral_l4': 'mean',
    'teleop_missed_coral_l1': 'mean',
    'teleop_missed_coral_l2': 'mean',
    'teleop_missed_coral_l3': 'mean',
    'teleop_missed_coral_l4': 'mean',
    'auto_algae_processor': 'mean',
    'teleop_algae_processor': 'mean',
    'auto_algae_barge': 'mean',
    'teleop_algae_barge': 'mean',
    'auto_missed_algae_barge': 'mean',
    'teleop_missed_algae_barge': 'mean',
    'auto_missed_algae_processor': 'mean',
    'teleop_missed_algae_processor': 'mean',
    'auto_algae_removed': 'mean',
    'teleop_algae_removed': 'mean',
    'auto_coral_success_ratio': 'mean',
    'teleop_coral_success_ratio': 'mean',
    'auto_algae_success_ratio': 'mean',
    'teleop_algae_success_ratio': 'mean',
}).reset_index()

# Fill NaN values with 0 to prevent display issues
team_stats = team_stats.fillna(0)

# Calculate total objects scored (coral + algae)
team_stats['total_auto_objects_scored'] = (
    team_stats['auto_coral_success'] +
    team_stats['auto_algae_barge'] +
    team_stats['auto_algae_processor']
)
team_stats['total_teleop_objects_scored'] = (
    team_stats['teleop_coral_success'] +
    team_stats['teleop_algae_barge'] +
    team_stats['teleop_algae_processor']
)
team_stats['total_objects_scored'] = (
    team_stats['total_auto_objects_scored'] +
    team_stats['total_teleop_objects_scored']
)

# Clean the climb_status data by converting to title case
team_data['climb_status'] = team_data['climb_status'].str.title()

# Map climb_status to simplified categories for the pie chart
team_data['climb_category'] = team_data['climb_status'].map({
    'Shallow Climb': 'Shallow Climb',
    'Deep Climb': 'Deep Climb',
    'None': 'No Climb',
    'Parked': 'No Climb'
}).fillna('No Climb')  # Default to 'No Climb' for unmapped values

# Calculate climb statistics
climb_stats = team_data.groupby('team_number')['climb_category'].value_counts(normalize=True).unstack(fill_value=0) * 100
climb_stats = climb_stats.reset_index()
# Ensure all possible climb categories are present
for status in ['Shallow Climb', 'Deep Climb', 'No Climb']:
    if status not in climb_stats.columns:
        climb_stats[status] = 0

# Calculate win/loss/tie record using the final match outcome on deduplicated data
# Ensure team_data is deduplicated for win/loss calculation
win_loss_data = team_data.drop_duplicates(subset=['match_number'])
win_loss = win_loss_data.groupby('team_number')['match_outcome_final'].value_counts().unstack(fill_value=0).reset_index()
win_loss = win_loss.rename(columns={'Won': 'Wins', 'Lost': 'Losses', 'Tie': 'Ties'})
if 'Wins' not in win_loss.columns:
    win_loss['Wins'] = 0
if 'Losses' not in win_loss.columns:
    win_loss['Losses'] = 0
if 'Ties' not in win_loss.columns:
    win_loss['Ties'] = 0

# Calculate primary role distribution
if 'primary_role' in team_data.columns:
    role_distribution = team_data.groupby('team_number')['primary_role'].value_counts(normalize=True).unstack(fill_value=0) * 100
    role_distribution = role_distribution.reset_index()
    # Ensure all possible roles are present
    for role in ['Offense', 'Defense', 'Both', 'Neither']:
        if role not in role_distribution.columns:
            role_distribution[role] = 0
else:
    role_distribution = pd.DataFrame({'team_number': [selected_team], 'Offense': [0], 'Defense': [0], 'Both': [0], 'Neither': [0]})

# Display team statistics
st.subheader(f"Statistics for Team {selected_team}")

# Organize into sections using columns
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Scoring Statistics")
    st.markdown(f"- **Average Total Score:** {team_stats['total_score'].iloc[0]:.2f}")
    st.markdown(f"- **Average Auto Score:** {team_stats['auto_score'].iloc[0]:.2f}")
    st.markdown(f"- **Average Teleop Score:** {team_stats['teleop_score'].iloc[0]:.2f}")
    st.markdown(f"- **Average Endgame Score:** {team_stats['endgame_score'].iloc[0]:.2f}")
    st.markdown(f"- **Avg Total Objects Scored:** {team_stats['total_objects_scored'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Auto Objects Scored:** {team_stats['total_auto_objects_scored'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Teleop Objects Scored:** {team_stats['total_teleop_objects_scored'].iloc[0]:.1f}")

    st.markdown("### Win/Loss Record")
    st.markdown(f"- **Wins:** {win_loss['Wins'].iloc[0]}")
    st.markdown(f"- **Losses:** {win_loss['Losses'].iloc[0]}")
    st.markdown(f"- **Ties:** {win_loss['Ties'].iloc[0]}")

with col2:
    st.markdown("### Coral Statistics")
    st.markdown("#### Autonomous Coral")
    st.markdown(f"- **Avg Scored on L1:** {team_stats['auto_coral_l1'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L1:** {team_stats['auto_missed_coral_l1'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored on L2:** {team_stats['auto_coral_l2'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L2:** {team_stats['auto_missed_coral_l2'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored on L3:** {team_stats['auto_coral_l3'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L3:** {team_stats['auto_missed_coral_l3'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored on L4:** {team_stats['auto_coral_l4'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L4:** {team_stats['auto_missed_coral_l4'].iloc[0]:.1f}")
    st.markdown(f"- **Total Auto Coral Scored:** {team_stats['auto_coral_success'].iloc[0]:.1f}")
    st.markdown(f"- **Total Auto Coral Missed:** {team_stats['auto_coral_missed'].iloc[0]:.1f}")
    st.markdown(f"- **Auto Coral Success Ratio:** {team_stats['auto_coral_success_ratio'].iloc[0]*100:.1f}%")

    st.markdown("#### Teleop Coral")
    st.markdown(f"- **Avg Scored on L1:** {team_stats['teleop_coral_l1'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L1:** {team_stats['teleop_missed_coral_l1'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored on L2:** {team_stats['teleop_coral_l2'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L2:** {team_stats['teleop_missed_coral_l2'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored on L3:** {team_stats['teleop_coral_l3'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L3:** {team_stats['teleop_missed_coral_l4'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored on L4:** {team_stats['teleop_coral_l4'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed on L4:** {team_stats['teleop_missed_coral_l4'].iloc[0]:.1f}")
    st.markdown(f"- **Total Teleop Coral Scored:** {team_stats['teleop_coral_success'].iloc[0]:.1f}")
    st.markdown(f"- **Total Teleop Coral Missed:** {team_stats['teleop_coral_missed'].iloc[0]:.1f}")
    st.markdown(f"- **Teleop Coral Success Ratio:** {team_stats['teleop_coral_success_ratio'].iloc[0]*100:.1f}%")

with col3:
    st.markdown("### Algae Statistics")
    st.markdown("#### Autonomous Algae")
    st.markdown(f"- **Avg Scored in Processor:** {team_stats['auto_algae_processor'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed in Processor:** {team_stats['auto_missed_algae_processor'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored in Barge:** {team_stats['auto_algae_barge'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed in Barge:** {team_stats['auto_missed_algae_barge'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Removed from Reef:** {team_stats['auto_algae_removed'].iloc[0]:.1f}")
    st.markdown(f"- **Auto Algae Success Ratio:** {team_stats['auto_algae_success_ratio'].iloc[0]*100:.1f}%")

    st.markdown("#### Teleop Algae")
    st.markdown(f"- **Avg Scored in Processor:** {team_stats['teleop_algae_processor'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed in Processor:** {team_stats['teleop_missed_algae_processor'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Scored in Barge:** {team_stats['teleop_algae_barge'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Missed in Barge:** {team_stats['teleop_missed_algae_barge'].iloc[0]:.1f}")
    st.markdown(f"- **Avg Removed from Reef:** {team_stats['teleop_algae_removed'].iloc[0]:.1f}")
    st.markdown(f"- **Teleop Algae Success Ratio:** {team_stats['teleop_algae_success_ratio'].iloc[0]*100:.1f}%")

# Display climb and strategy distribution as pie charts
st.subheader("Climb and Strategy Distribution")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Climb Distribution")
    climb_data = climb_stats.melt(id_vars=['team_number'], value_vars=['Shallow Climb', 'Deep Climb', 'No Climb'],
                                  var_name='Climb Status', value_name='Percentage')
    # Check if there is any non-zero data to plot
    if climb_data['Percentage'].sum() > 0:
        fig_climb = px.pie(
            climb_data,
            names='Climb Status',
            values='Percentage',
            title=f"Team {selected_team} Climb Distribution",
            hole=0.3
        )
        fig_climb.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_climb, use_container_width=True)
    else:
        st.write("No climb data available to display.")

with col2:
    st.markdown("#### Strategy Distribution")
    role_data = role_distribution.melt(id_vars=['team_number'], value_vars=['Offense', 'Defense', 'Both', 'Neither'],
                                       var_name='Primary Role', value_name='Percentage')
    # Check if there is any non-zero data to plot
    if role_data['Percentage'].sum() > 0:
        fig_role = px.pie(
            role_data,
            names='Primary Role',
            values='Percentage',
            title=f"Team {selected_team} Strategy Distribution",
            hole=0.3
        )
        fig_role.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_role, use_container_width=True)
    else:
        st.write("No strategy data available to display.")

# Plot performance over matches
st.subheader("Performance Over Matches")
# Ensure match_number is numeric and sort the data
team_data = team_data.copy()  # Avoid SettingWithCopyWarning
team_data['match_number'] = pd.to_numeric(team_data['match_number'], errors='coerce')
team_data = team_data.sort_values('match_number')
fig = px.line(
    team_data,
    x='match_number',
    y='total_score',
    title=f"Team {selected_team} Total Score per Match",
    labels={'match_number': 'Match Number', 'total_score': 'Total Score'}
)
st.plotly_chart(fig, use_container_width=True)