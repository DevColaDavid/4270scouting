import streamlit as st
import pandas as pd
from utils import load_data

st.set_page_config(page_title="Match Prediction", page_icon="🎯")

st.title("Match Prediction")

# Load data
df = load_data()
if df is not None and not df.empty:
    # Multi-select dropdowns for alliance selection (up to 3 teams each)
    red_alliance_teams = st.multiselect("Select Red Alliance Teams (up to 3)", options=df['team_number'].unique(), max_selections=3)
    blue_alliance_teams = st.multiselect("Select Blue Alliance Teams (up to 3)", options=df['team_number'].unique(), max_selections=3)

    if 'alliance_color' in df.columns:
        # Calculate 'auto_score' if it does not exist
        if 'auto_score' not in df.columns:
            df['auto_score'] = (df['auto_score_l1'] + df['auto_score_l2'] +
                               df['auto_score_l3'] + df['auto_score_l4'] +
                               df['auto_algae_removed'] + df['auto_algae_processor'] +
                               df['auto_barge_scored'])

        df['auto_score'] = pd.to_numeric(df['auto_score'], errors='coerce')

        # Calculate teleop_score
        if 'teleop_score' not in df.columns:
            df['teleop_score'] = (df['teleop_score_l1'] + df['teleop_score_l2'] +
                                  df['teleop_score_l3'] + df['teleop_score_l4'] +
                                  df['teleop_algae_removed'] + df['teleop_algae_processor'] +
                                  df['teleop_barge_scored'])
        df['teleop_score'] = pd.to_numeric(df['teleop_score'], errors='coerce')

        # Check if 'endgame_score' column exists
        if 'endgame_score' not in df.columns:
            df['endgame_score'] = df.get('endgame_score', 0)

        # Calculate total scores for the selected alliances
        red_scores = df[df['team_number'].isin(red_alliance_teams)][['auto_score', 'teleop_score', 'endgame_score']].mean().sum()
        blue_scores = df[df['team_number'].isin(blue_alliance_teams)][['auto_score', 'teleop_score', 'endgame_score']].mean().sum()

        red_score = red_scores * 3
        blue_score = blue_scores * 3

        # Calculate win probability based on scores
        total_score = red_score + blue_score
        if total_score > 0:
            red_win_probability = red_score / total_score
            blue_win_probability = blue_score / total_score
        else:
            red_win_probability = 0
            blue_win_probability = 0

        # Check for tie (within 5 points)
        total_diff = abs(red_score - blue_score)
        is_tie = total_diff <= 5

        st.subheader("Match Prediction")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Red Team Score", red_score)
            st.metric("Red Win Probability", f"{red_win_probability:.1%}")

        with col2:
            st.metric("Blue Team Score", blue_score)
            st.metric("Blue Win Probability", f"{blue_win_probability:.1%}")

        if is_tie:
            st.success("The match is likely to end in a tie!")
        else:
            winner = "Red Team" if red_score > blue_score else "Blue Team"
            st.success(f"The predicted winner is: {winner} with a score difference of {total_diff:.1f} points.")

    else:
        st.warning("No valid alliance data available.")
else:
    st.info("No match data available for prediction.")