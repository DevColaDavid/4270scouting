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
        'climb_status', 'auto_taxi_left'  # Added new field
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
            red_adjustment = 1.0
            blue_adjustment = 1.0
            if 'alliance_color' in df.columns:
                # Calculate average performance difference when in Red vs. Blue alliance
                for data, alliance in [(red_data, 'Red'), (blue_data, 'Blue')]:
                    red_performance = data[data['alliance_color'] == 'Red'][score_cols].mean().sum()
                    blue_performance = data[data['alliance_color'] == 'Blue'][score_cols].mean().sum()
                    if not pd.isna(red_performance) and not pd.isna(blue_performance) and blue_performance != 0:
                        adjustment_factor = red_performance / blue_performance if alliance == 'Red' else blue_performance / red_performance
                        adjustment_factor = max(min(adjustment_factor, 1.2), 0.8)  # Limit adjustment to ±20%
                        if alliance == 'Red':
                            red_adjustment = adjustment_factor
                        else:
                            blue_adjustment = adjustment_factor
                        data.loc[:, score_cols] = data[score_cols] * adjustment_factor

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

            # Apply alliance color adjustments to final scores
            red_score *= red_adjustment
            blue_score *= blue_adjustment

            # Calculate score difference and standard deviation for tie threshold
            score_diff = red_score - blue_score
            if 'total_score' in df.columns:
                score_std = df.groupby('match_number')['total_score'].std().mean()
                tie_threshold = score_std * 0.5 if not pd.isna(score_std) else 5  # Tie if within 0.5 standard deviations
            else:
                tie_threshold = 5  # Fallback to 5 points

            # Calculate win probability using a logistic function
            k = 0.1  # Sensitivity parameter (adjustable)
            score_diff_scaled = score_diff * k
            red_win_probability = 1 / (1 + np.exp(-score_diff_scaled))
            blue_win_probability = 1 - red_win_probability

            # Analyze team contributions and trends
            def analyze_team_contributions(data, team_scores, alliance_name):
                insights = []
                for team in data['team_number'].unique():
                    team_data = data[data['team_number'] == team]
                    avg_score = team_scores[team]
                    # Check performance trend (improving or declining)
                    if 'timestamp' in team_data.columns and len(team_data) > 1:
                        recent_matches = team_data.sort_values('timestamp').tail(3)
                        older_matches = team_data.sort_values('timestamp').head(3)
                        recent_avg = recent_matches[score_cols].sum(axis=1).mean()
                        older_avg = older_matches[score_cols].sum(axis=1).mean()
                        if not pd.isna(recent_avg) and not pd.isna(older_avg):
                            trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
                            insights.append(f"Team {team} has a {trend} performance trend (recent avg: {recent_avg:.1f}, older avg: {older_avg:.1f}).")
                    # Highlight key strengths
                    auto_avg = team_data['auto_score'].mean()
                    teleop_avg = team_data['teleop_score'].mean()
                    endgame_avg = team_data['endgame_score'].mean()
                    strengths = []
                    if auto_avg > teleop_avg and auto_avg > endgame_avg:
                        strengths.append("strong autonomous performance")
                    if teleop_avg > auto_avg and teleop_avg > endgame_avg:
                        strengths.append("strong teleop performance")
                    if endgame_avg > auto_avg and endgame_avg > teleop_avg:
                        strengths.append("strong endgame performance")
                    if strengths:
                        insights.append(f"Team {team} contributes with {', '.join(strengths)} (avg score: {avg_score:.1f}).")
                    else:
                        insights.append(f"Team {team} has balanced performance (avg score: {avg_score:.1f}).")
                    # Add taxiing and parking insights
                    if 'auto_taxi_left' in team_data.columns:
                        taxi_rate = team_data['auto_taxi_left'].mean() * 100
                        insights.append(f"Team {team} successfully taxied in {taxi_rate:.1f}% of matches.")
                    if 'climb_status' in team_data.columns:
                        park_rate = (team_data['climb_status'] == 'Parked').mean() * 100
                        shallow_climb_rate = (team_data['climb_status'] == 'Shallow Climb').mean() * 100
                        deep_climb_rate = (team_data['climb_status'] == 'Deep Climb').mean() * 100
                        insights.append(f"Team {team} parked in {park_rate:.1f}% of matches, achieved a shallow climb in {shallow_climb_rate:.1f}%, and a deep climb in {deep_climb_rate:.1f}%.")
                return insights

            red_insights = analyze_team_contributions(red_data, red_team_scores, "Red Alliance")
            blue_insights = analyze_team_contributions(blue_data, blue_team_scores, "Blue Alliance")

            # Display results
            st.subheader("Match Prediction")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Predicted Red Alliance Score", f"{red_score:.1f}")
                st.metric("Red Win Probability", f"{red_win_probability:.1%}")

            with col2:
                st.metric("Predicted Blue Alliance Score", f"{blue_score:.1f}")
                st.metric("Blue Win Probability", f"{blue_win_probability:.1%}")

            # Check for tie
            total_diff = abs(score_diff)
            is_tie = total_diff <= tie_threshold

            # Generate detailed prediction description
            st.subheader("Prediction Details")
            if is_tie:
                st.success(f"The match is predicted to be a close tie! The score difference is only {total_diff:.1f} points, which is within the tie threshold of {tie_threshold:.1f} points.")
                st.markdown("### Why This Is a Tie:")
                st.markdown("- **Close Scores**: The predicted scores for both alliances are very similar, indicating a highly competitive match.")
                if red_adjustment != 1.0 or blue_adjustment != 1.0:
                    st.markdown(f"- **Alliance Color Impact**: Red Alliance scores were adjusted by a factor of {red_adjustment:.2f}, and Blue Alliance scores by {blue_adjustment:.2f} based on historical performance in their respective alliance colors.")
            else:
                winner = "Red Alliance" if red_score > blue_score else "Blue Alliance"
                loser = "Blue Alliance" if winner == "Red Alliance" else "Red Alliance"
                st.success(f"The {winner} is predicted to win with a score difference of {total_diff:.1f} points!")
                st.markdown(f"### Why {winner} Is Predicted to Win:")
                st.markdown(f"- **Score Advantage**: The {winner} has a higher predicted score ({red_score:.1f} vs {blue_score:.1f}), giving them a {red_win_probability:.1%} chance of winning compared to {loser}'s {blue_win_probability:.1%}.")
                if red_adjustment != 1.0 or blue_adjustment != 1.0:
                    st.markdown(f"- **Alliance Color Impact**: Red Alliance scores were adjusted by a factor of {red_adjustment:.2f}, and Blue Alliance scores by {blue_adjustment:.2f} based on historical performance in their respective alliance colors.")
                st.markdown(f"- **Performance Trends**: Recent matches were given more weight, reflecting the teams' current form.")

            # Display team contributions
            st.markdown("### Red Alliance Insights:")
            for insight in red_insights:
                st.markdown(f"- {insight}")

            st.markdown("### Blue Alliance Insights:")
            for insight in blue_insights:
                st.markdown(f"- {insight}")

            st.markdown("### Additional Notes:")
            st.markdown("- The prediction accounts for diminishing returns in alliance contributions, meaning additional teams contribute less than their full average score due to shared roles.")
            st.markdown("- Win probabilities are calculated using a logistic model, making close matches more uncertain and decisive score differences more confident.")
        else:
            st.warning("Score data (auto_score, teleop_score, endgame_score) not available for prediction.")
    else:
        st.info("Please select teams for both Red and Blue Alliances to predict the match outcome.")