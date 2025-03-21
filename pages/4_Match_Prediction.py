# pages/4_Match_Prediction.py
import streamlit as st
import pandas as pd
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
            # Calculate average scores per team
            red_data = df[df['team_number'].isin(red_alliance_teams)]
            blue_data = df[df['team_number'].isin(blue_alliance_teams)]

            # Check if data exists for the selected teams
            if red_data.empty:
                st.warning("No data available for the selected Red Alliance teams.")
                st.stop()
            if blue_data.empty:
                st.warning("No data available for the selected Blue Alliance teams.")
                st.stop()

            red_scores = red_data[score_cols].mean().sum()
            blue_scores = blue_data[score_cols].mean().sum()

            # Scale scores for the alliance (3 teams)
            red_score = red_scores * len(red_alliance_teams)
            blue_score = blue_scores * len(blue_alliance_teams)

            # Calculate win probability based on scores
            total_score = red_score + blue_score
            if total_score > 0:
                red_win_probability = red_score / total_score
                blue_win_probability = blue_score / total_score
            else:
                red_win_probability = 0.5
                blue_win_probability = 0.5

            # Check for tie (within 5 points)
            total_diff = abs(red_score - blue_score)
            is_tie = total_diff <= 5

            st.subheader("Match Prediction")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Red Alliance Score", f"{red_score:.1f}")
                st.metric("Red Win Probability", f"{red_win_probability:.1%}")

            with col2:
                st.metric("Blue Alliance Score", f"{blue_score:.1f}")
                st.metric("Blue Win Probability", f"{blue_win_probability:.1%}")

            if is_tie:
                st.success("The match is likely to end in a tie!")
            else:
                winner = "Red Alliance" if red_score > blue_score else "Blue Alliance"
                st.success(f"The predicted winner is: {winner} with a score difference of {total_diff:.1f} points.")
        else:
            st.warning("Score data (auto_score, teleop_score, endgame_score) not available for prediction.")
    else:
        st.info("Please select teams for both Red and Blue Alliances to predict the match outcome.")