# pages/4_Match_Prediction.py
import streamlit as st
import pandas as pd
import numpy as np
from utils.utils import load_data, calculate_match_score

st.set_page_config(page_title="Match Prediction", page_icon="🎯")

st.title("Match Prediction")

# Load data
df = load_data()

if df is None or df.empty:
    st.info("No match data available for prediction.")
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
        st.stop()

    # Sort by timestamp for time-based weighting
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values(by='timestamp', ascending=True, na_position='last')
        # Assign weights: more recent matches get higher weights
        df['time_weight'] = np.linspace(0.1, 1.0, len(df))  # Linearly increasing weights
    else:
        df['time_weight'] = 1.0  # Equal weights if timestamp is not available

    # Multi-select dropdowns for alliance selection (up to 3 teams each)
    if 'team_number' in df.columns:
        team_numbers = sorted(df['team_number'].dropna().unique())
        red_alliance_teams = st.multiselect("Select Red Alliance Teams (up to 3)", options=team_numbers, max_selections=3)
        blue_alliance_teams = st.multiselect("Select Blue Alliance Teams (up to 3)", options=team_numbers, max_selections=3)
    else:
        st.error("Team number data not available.")
        st.stop()

    if red_alliance_teams and blue_alliance_teams:
        # Calculate total scores for the selected alliances
        score_cols = ['auto_score', 'teleop_score', 'endgame_score']
        if all(col in df.columns for col in score_cols):
            # Calculate weighted average scores per team, considering alliance color
            red_data = df[df['team_number'].isin(red_alliance_teams)].copy()
            blue_data = df[df['team_number'].isin(blue_alliance_teams)].copy()

            # Check if data exists for the selected teams
            if red_data.empty:
                st.warning("No data available for the selected Red Alliance teams.")
                st.stop()
            if blue_data.empty:
                st.warning("No data available for the selected Blue Alliance teams.")
                st.stop()

            # Adjust scores based on alliance color performance
            if 'alliance_color' in df.columns:
                # Calculate average performance difference when in Red vs. Blue alliance
                for data, alliance in [(red_data, 'Red'), (blue_data, 'Blue')]:
                    red_performance = data[data['alliance_color'] == 'Red'][score_cols].mean().sum()
                    blue_performance = data[data['alliance_color'] == 'Blue'][score_cols].mean().sum()
                    if not pd.isna(red_performance) and not pd.isna(blue_performance):
                        adjustment_factor = red_performance / blue_performance if alliance == 'Red' else blue_performance / red_performance
                        adjustment_factor = max(min(adjustment_factor, 1.2), 0.8)  # Limit adjustment to ±20%
                        data.loc[:, score_cols] = data[score_cols] * adjustment_factor
                    else:
                        # If no data for one color, no adjustment
                        pass

            # Calculate weighted average scores for each team
            def weighted_avg(group, cols, weight_col):
                # Sum the scores (auto, teleop, endgame) for each match
                group['total_score'] = group[cols].sum(axis=1)
                # Calculate weighted average of the total score
                weighted_sum = (group['total_score'] * group[weight_col]).sum()
                weight_sum = group[weight_col].sum()
                return weighted_sum / weight_sum if weight_sum > 0 else 0

            red_team_scores = red_data.groupby('team_number').apply(weighted_avg, cols=score_cols, weight_col='time_weight')
            blue_team_scores = blue_data.groupby('team_number').apply(weighted_avg, cols=score_cols, weight_col='time_weight')

            # Sum the scores for each alliance with diminishing returns
            def calculate_alliance_score(team_scores):
                if team_scores.empty:
                    return 0
                total_score = team_scores.sum()  # Sum of weighted average total scores across teams
                num_teams = len(team_scores)
                # Apply diminishing returns: each additional team contributes less
                if num_teams > 1:
                    total_score *= (1 + 0.7 * (num_teams - 1)) / num_teams
                return float(total_score)  # Ensure the result is a float

            red_score = calculate_alliance_score(red_team_scores)
            blue_score = calculate_alliance_score(blue_team_scores)

            # Calculate score difference and standard deviation for tie threshold
            score_diff = red_score - blue_score
            if 'total_score' in df.columns:
                score_std = df.groupby('match_number')['total_score'].std().mean()
                tie_threshold = score_std * 0.5 if not pd.isna(score_std) else 5  # Tie if within 0.5 standard deviations
            else:
                tie_threshold = 5  # Fallback to 5 points

            # Calculate win probability using a logistic function
            # Scale the score difference to map to a probability between 0 and 1
            k = 0.1  # Sensitivity parameter (adjustable)
            score_diff_scaled = score_diff * k
            red_win_probability = 1 / (1 + np.exp(-score_diff_scaled))
            blue_win_probability = 1 - red_win_probability

            # Display results
            st.subheader("Match Prediction")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Red Alliance Score", f"{red_score:.1f}")
                st.metric("Red Win Probability", f"{red_win_probability:.1%}")

            with col2:
                st.metric("Blue Alliance Score", f"{blue_score:.1f}")
                st.metric("Blue Win Probability", f"{blue_win_probability:.1%}")

            # Check for tie
            total_diff = abs(score_diff)
            is_tie = total_diff <= tie_threshold

            if is_tie:
                st.success(f"The match is likely to end in a tie! (Score difference: {total_diff:.1f} points, threshold: {tie_threshold:.1f})")
            else:
                winner = "Red Alliance" if red_score > blue_score else "Blue Alliance"
                st.success(f"The predicted winner is: {winner} with a score difference of {total_diff:.1f} points.")
        else:
            st.warning("Score data (auto_score, teleop_score, endgame_score) not available for prediction.")
    else:
        st.info("Please select teams for both Red and Blue Alliances to predict the match outcome.")