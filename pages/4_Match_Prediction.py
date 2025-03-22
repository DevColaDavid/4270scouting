import streamlit as st
import pandas as pd
import numpy as np
from utils.utils import load_data, calculate_match_score

st.set_page_config(page_title="Match Prediction", page_icon="📉", layout="wide")

st.title("📉 Match Prediction")
st.markdown("Predict the outcome of a match based on historical scouting data.")

# Load data
df = load_data()

if df is None or df.empty:
    st.info("No match data available for prediction.")
    st.stop()

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
else:
    st.warning("Cannot calculate match scores. Missing required columns.")
    st.stop()

# Calculate success ratios for prediction adjustment
df['auto_coral_success'] = df['auto_coral_l1'] + df['auto_coral_l2'] + df['auto_coral_l3'] + df['auto_coral_l4']
df['auto_coral_missed'] = df['auto_missed_coral_l1'] + df['auto_missed_coral_l2'] + df['auto_missed_coral_l3'] + df['auto_missed_coral_l4']
df['teleop_coral_success'] = df['teleop_coral_l1'] + df['teleop_coral_l2'] + df['teleop_coral_l3'] + df['teleop_coral_l4']
df['teleop_coral_missed'] = df['teleop_missed_coral_l1'] + df['teleop_missed_coral_l2'] + df['teleop_missed_coral_l3'] + df['teleop_missed_coral_l4']
df['auto_coral_attempts'] = df['auto_coral_success'] + df['auto_coral_missed']
df['teleop_coral_attempts'] = df['teleop_coral_success'] + df['teleop_coral_missed']
df['auto_coral_success_ratio'] = df['auto_coral_success'] / df['auto_coral_attempts'].replace(0, 1)
df['teleop_coral_success_ratio'] = df['teleop_coral_success'] / df['teleop_coral_attempts'].replace(0, 1)

df['auto_algae_success'] = df['auto_algae_barge'] + df['auto_algae_processor']
df['auto_algae_missed'] = df['auto_missed_algae_barge'] + df['auto_missed_algae_processor']
df['teleop_algae_success'] = df['teleop_algae_barge'] + df['teleop_algae_processor']
df['teleop_algae_missed'] = df['teleop_missed_algae_barge'] + df['teleop_missed_algae_processor']
df['auto_algae_attempts'] = df['auto_algae_success'] + df['auto_algae_missed']
df['teleop_algae_attempts'] = df['teleop_algae_success'] + df['teleop_algae_missed']
df['auto_algae_success_ratio'] = df['auto_algae_success'] / df['auto_algae_attempts'].replace(0, 1)
df['teleop_algae_success_ratio'] = df['teleop_algae_success'] / df['teleop_algae_attempts'].replace(0, 1)

# Calculate EPA for each team (ensure non-negative)
def calculate_epa(df, team):
    team_data = df[df['team_number'] == team]
    if team_data.empty:
        return 0.0
    epa_values = []
    for idx, row in team_data.iterrows():
        match_data = df[df['match_number'] == row['match_number']]
        alliance_data = match_data[match_data['alliance_color'] == row['alliance_color']]
        alliance_avg = alliance_data['total_score'].mean()
        team_score = row['total_score']
        epa = team_score - alliance_avg
        epa_values.append(epa)
    avg_epa = sum(epa_values) / len(epa_values) if epa_values else 0.0
    return max(avg_epa, 0.0)  # Ensure EPA is non-negative

# Team selection for prediction
if 'team_number' in df.columns:
    team_numbers = sorted(df['team_number'].dropna().unique())
    st.subheader("Select Teams for the Match")
    col1, col2 = st.columns(2)
    with col1:
        red_alliance_teams = st.multiselect("Select Red Alliance Teams (up to 3)", options=team_numbers, max_selections=3)
    with col2:
        blue_alliance_teams = st.multiselect("Select Blue Alliance Teams (up to 3)", options=team_numbers, max_selections=3)
else:
    st.error("Team number column not found in data.")
    st.stop()

# Prediction logic
if red_alliance_teams and blue_alliance_teams:
    def calculate_alliance_score(team_scores, team_accuracy_adjustments):
        if not team_scores:
            return 0.0
        weights = np.array([1.0, 0.8, 0.6])[:len(team_scores)]
        weighted_scores = [
            max(score * weight * (1 + (adjustment - 0.5) * 0.2), 0.0)  # Ensure non-negative score
            for score, weight, adjustment in zip(sorted(team_scores, reverse=True), weights, sorted(team_accuracy_adjustments, reverse=True))
        ]
        return sum(weighted_scores)

    def estimate_alliance_bonuses(data, alliance_teams):
        if not alliance_teams:
            return 0.0
        coral_cols = [
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4'
        ]
        team_coral = data.groupby('team_number')[coral_cols].mean()
        team_coral['l1_total'] = team_coral['auto_coral_l1'] + team_coral['teleop_coral_l1']
        team_coral['l2_total'] = team_coral['auto_coral_l2'] + team_coral['teleop_coral_l2']
        team_coral['l3_total'] = team_coral['auto_coral_l3'] + team_coral['teleop_coral_l3']
        team_coral['l4_total'] = team_coral['auto_coral_l4'] + team_coral['teleop_coral_l4']
        avg_coral_per_level = team_coral.loc[alliance_teams, ['l1_total', 'l2_total', 'l3_total', 'l4_total']].sum()
        levels_with_5_plus = (avg_coral_per_level >= 5).sum()
        coop_bonus_prob = min(1.0, levels_with_5_plus / 3)

        climb_stats = data.groupby('team_number')['climb_status'].value_counts(normalize=True).unstack(fill_value=0)
        climb_stats['climb_prob'] = climb_stats.get('Shallow Climb', 0) + climb_stats.get('Deep Climb', 0)
        harmony_bonus_prob = climb_stats.loc[alliance_teams, 'climb_prob'].prod()

        expected_bonus = (coop_bonus_prob * 15) + (harmony_bonus_prob * 15)
        return max(expected_bonus, 0.0)  # Ensure non-negative bonus

    # Split data by alliance
    red_data = df[df['team_number'].isin(red_alliance_teams)]
    blue_data = df[df['team_number'].isin(blue_alliance_teams)]

    # Calculate EPA and accuracy adjustments for each team
    red_team_scores = [calculate_epa(df, team) for team in red_alliance_teams]
    blue_team_scores = [calculate_epa(df, team) for team in blue_alliance_teams]

    # Calculate average success ratios for adjustment
    red_accuracy = red_data.groupby('team_number')[['teleop_coral_success_ratio', 'teleop_algae_success_ratio']].mean()
    red_accuracy['combined_accuracy'] = (red_accuracy['teleop_coral_success_ratio'] + red_accuracy['teleop_algae_success_ratio']) / 2
    red_accuracy_adjustments = [red_accuracy.loc[team, 'combined_accuracy'] if team in red_accuracy.index else 0.5 for team in red_alliance_teams]

    blue_accuracy = blue_data.groupby('team_number')[['teleop_coral_success_ratio', 'teleop_algae_success_ratio']].mean()
    blue_accuracy['combined_accuracy'] = (blue_accuracy['teleop_coral_success_ratio'] + blue_accuracy['teleop_algae_success_ratio']) / 2
    blue_accuracy_adjustments = [blue_accuracy.loc[team, 'combined_accuracy'] if team in blue_accuracy.index else 0.5 for team in blue_alliance_teams]

    # Calculate alliance scores with accuracy adjustments
    red_score = calculate_alliance_score(red_team_scores, red_accuracy_adjustments)
    blue_score = calculate_alliance_score(blue_team_scores, blue_accuracy_adjustments)

    # Estimate alliance bonuses
    red_bonus = estimate_alliance_bonuses(red_data, red_alliance_teams)
    blue_bonus = estimate_alliance_bonuses(blue_data, blue_alliance_teams)

    # Add bonuses to predicted scores
    red_score = max(red_score + red_bonus, 0.0)  # Ensure non-negative final score
    blue_score = max(blue_score + blue_bonus, 0.0)  # Ensure non-negative final score

    # Calculate win probability (ensure between 0% and 100%)
    if red_score == blue_score:
        red_win_prob = 50.0
        blue_win_prob = 50.0
    else:
        total_score = red_score + blue_score
        if total_score == 0:
            red_win_prob = 50.0
            blue_win_prob = 50.0
        else:
            red_win_prob = (red_score / total_score) * 100
            blue_win_prob = (blue_score / total_score) * 100

    # Display prediction
    st.subheader("Match Prediction")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Red Alliance Predicted Score", f"{red_score:.2f}")
        st.metric("Red Alliance Win Probability", f"{red_win_prob:.1f}%")
    with col2:
        st.metric("Blue Alliance Predicted Score", f"{blue_score:.2f}")
        st.metric("Blue Alliance Win Probability", f"{blue_win_prob:.1f}%")

    # Determine winner
    if red_score > blue_score:
        st.success(f"Red Alliance is predicted to win by {red_score - blue_score:.2f} points!")
    elif blue_score > red_score:
        st.success(f"Blue Alliance is predicted to win by {blue_score - red_score:.2f} points!")
    else:
        st.info("The match is predicted to be a tie!")

    # Provide reasons based on data
    st.subheader("Reasons for Prediction")
    
    # Calculate key metrics for each alliance
    red_metrics = red_data.groupby('team_number').agg({
        'total_score': 'mean',
        'auto_score': 'mean',
        'teleop_score': 'mean',
        'endgame_score': 'mean',
        'teleop_coral_success_ratio': 'mean',
        'teleop_algae_success_ratio': 'mean',
        'climb_status': lambda x: ((x == 'Shallow Climb') | (x == 'Deep Climb')).mean() * 100
    }).mean()

    blue_metrics = blue_data.groupby('team_number').agg({
        'total_score': 'mean',
        'auto_score': 'mean',
        'teleop_score': 'mean',
        'endgame_score': 'mean',
        'teleop_coral_success_ratio': 'mean',
        'teleop_algae_success_ratio': 'mean',
        'climb_status': lambda x: ((x == 'Shallow Climb') | (x == 'Deep Climb')).mean() * 100
    }).mean()

    # Compare and provide reasoning
    st.markdown("#### Key Factors Influencing the Prediction:")
    
    # Total Score Comparison
    st.markdown("- **Average Total Score**")
    st.markdown(f"  - Red Alliance: {red_metrics['total_score']:.2f}")
    st.markdown(f"  - Blue Alliance: {blue_metrics['total_score']:.2f}")
    if red_metrics['total_score'] > blue_metrics['total_score']:
        st.markdown("    - Red Alliance has a higher average total score, indicating stronger overall performance.")
    else:
        st.markdown("    - Blue Alliance has a higher average total score, indicating stronger overall performance.")

    # Autonomous Performance
    st.markdown("- **Autonomous Performance**")
    st.markdown(f"  - Red Alliance Avg Auto Score: {red_metrics['auto_score']:.2f}")
    st.markdown(f"  - Blue Alliance Avg Auto Score: {blue_metrics['auto_score']:.2f}")
    if red_metrics['auto_score'] > blue_metrics['auto_score']:
        st.markdown("    - Red Alliance performs better in autonomous, giving them an early advantage.")
    else:
        st.markdown("    - Blue Alliance performs better in autonomous, giving them an early advantage.")

    # Teleop Performance
    st.markdown("- **Teleop Performance**")
    st.markdown(f"  - Red Alliance Avg Teleop Score: {red_metrics['teleop_score']:.2f}")
    st.markdown(f"  - Blue Alliance Avg Teleop Score: {blue_metrics['teleop_score']:.2f}")
    st.markdown(f"  - Red Alliance Coral Success Ratio: {red_metrics['teleop_coral_success_ratio']*100:.1f}%")
    st.markdown(f"  - Blue Alliance Coral Success Ratio: {blue_metrics['teleop_coral_success_ratio']*100:.1f}%")
    st.markdown(f"  - Red Alliance Algae Success Ratio: {red_metrics['teleop_algae_success_ratio']*100:.1f}%")
    st.markdown(f"  - Blue Alliance Algae Success Ratio: {blue_metrics['teleop_algae_success_ratio']*100:.1f}%")
    if red_metrics['teleop_score'] > blue_metrics['teleop_score']:
        st.markdown("    - Red Alliance has a stronger teleop performance.")
    else:
        st.markdown("    - Blue Alliance has a stronger teleop performance.")
    if red_metrics['teleop_coral_success_ratio'] > blue_metrics['teleop_coral_success_ratio']:
        st.markdown("    - Red Alliance is more accurate in scoring coral during teleop.")
    else:
        st.markdown("    - Blue Alliance is more accurate in scoring coral during teleop.")
    if red_metrics['teleop_algae_success_ratio'] > blue_metrics['teleop_algae_success_ratio']:
        st.markdown("    - Red Alliance is more effective at managing algae during teleop.")
    else:
        st.markdown("    - Blue Alliance is more effective at managing algae during teleop.")

    # Endgame Performance
    st.markdown("- **Endgame Performance**")
    st.markdown(f"  - Red Alliance Avg Endgame Score: {red_metrics['endgame_score']:.2f}")
    st.markdown(f"  - Blue Alliance Avg Endgame Score: {blue_metrics['endgame_score']:.2f}")
    st.markdown(f"  - Red Alliance Climb Rate: {red_metrics['climb_status']:.1f}%")
    st.markdown(f"  - Blue Alliance Climb Rate: {blue_metrics['climb_status']:.1f}%")
    if red_metrics['endgame_score'] > blue_metrics['endgame_score']:
        st.markdown("    - Red Alliance has a stronger endgame performance.")
    else:
        st.markdown("    - Blue Alliance has a stronger endgame performance.")
    if red_metrics['climb_status'] > blue_metrics['climb_status']:
        st.markdown("    - Red Alliance is more likely to climb, increasing their chances of earning the Harmony bonus.")
    else:
        st.markdown("    - Blue Alliance is more likely to climb, increasing their chances of earning the Harmony bonus.")

    # Alliance Bonuses
    st.markdown("- **Estimated Alliance Bonuses**")
    st.markdown(f"  - Red Alliance Bonus: {red_bonus:.2f} points")
    st.markdown(f"  - Blue Alliance Bonus: {blue_bonus:.2f} points")
    if red_bonus > blue_bonus:
        st.markdown("    - Red Alliance is more likely to earn alliance bonuses (Co-op and Harmony).")
    else:
        st.markdown("    - Blue Alliance is more likely to earn alliance bonuses (Co-op and Harmony).")

else:
    st.info("Please select teams for both Red and Blue Alliances to predict the match.")