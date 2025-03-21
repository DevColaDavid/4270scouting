# pages/2_Data_Analysis.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from utils.utils import load_data, calculate_match_score

# Cache the data loading and score calculation for performance
@st.cache_data
def load_and_calculate_scores():
    df = load_data()
    if df is not None and not df.empty:
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

        # Calculate scores if required columns are present
        required_cols = [
            'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
            'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
            'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
            'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
            'climb_status'
        ]
        if all(col in df.columns for col in required_cols):
            df = df.join(df.apply(calculate_match_score, axis=1))
    return df

st.title("Overall Data Analysis Dashboard")

# Load data
df = load_and_calculate_scores()

if df is None or df.empty:
    st.warning("No scouting data available. Please add match data in the 'Match Scouting' page.")
else:
    # Sidebar Filters
    st.sidebar.header("Filters")

    # Match number filter
    if 'match_number' in df.columns:
        match_numbers = sorted(df['match_number'].dropna().unique())
        selected_matches = st.sidebar.multiselect(
            "Select Match Numbers",
            options=match_numbers,
            default=match_numbers[:5] if len(match_numbers) >= 5 else match_numbers
        )
    else:
        selected_matches = []
        st.sidebar.warning("Match number data not available.")

    # Alliance color filter
    if 'alliance_color' in df.columns:
        alliance_colors = sorted(df['alliance_color'].dropna().unique())
        selected_alliances = st.sidebar.multiselect(
            "Select Alliance Colors",
            options=alliance_colors,
            default=alliance_colors
        )
    else:
        selected_alliances = []
        st.sidebar.warning("Alliance color data not available.")

    # Match result filter
    if 'match_result' in df.columns:
        match_results = sorted(df['match_result'].dropna().unique())
        selected_results = st.sidebar.multiselect(
            "Select Match Results",
            options=match_results,
            default=match_results
        )
    else:
        selected_results = []
        st.sidebar.warning("Match result data not available.")

    # Apply filters
    filtered_df = df.copy()
    if selected_matches:
        filtered_df = filtered_df[filtered_df['match_number'].isin(selected_matches)]
    if selected_alliances:
        filtered_df = filtered_df[filtered_df['alliance_color'].isin(selected_alliances)]
    if selected_results:
        filtered_df = filtered_df[filtered_df['match_result'].isin(selected_results)]

    if filtered_df.empty:
        st.warning("No data matches the selected filters. Please adjust the filters to include more matches, alliances, or results.")
    else:
        # Summary Statistics
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Matches", len(filtered_df))
        with col2:
            st.metric("Teams Scouted", filtered_df['team_number'].nunique())
        with col3:
            if 'total_score' in filtered_df.columns:
                avg_score = filtered_df['total_score'].mean()
                st.metric("Avg Total Score", f"{avg_score:.1f}")
            else:
                st.metric("Avg Total Score", "N/A")
        with col4:
            if 'climb_status' in filtered_df.columns:
                most_common_climb = filtered_df['climb_status'].mode()[0] if not filtered_df['climb_status'].mode().empty else "N/A"
                st.metric("Most Common Climb", most_common_climb)
            else:
                st.metric("Most Common Climb", "N/A")

        # Leaderboard
        st.subheader("Leaderboard")
        st.write("Ranking of Teams Based on Key Metrics Across All Matches")
        required_cols = ['team_number', 'total_score', 'match_result', 'climb_status', 'driver_skill_rating']
        if all(col in filtered_df.columns for col in required_cols):
            # Calculate metrics for the leaderboard
            leaderboard_data = filtered_df.groupby('team_number').agg({
                'total_score': 'mean',
                'match_result': lambda x: (x == 'Win').sum() / len(x) * 100,  # Win rate
                'climb_status': lambda x: ((x == 'Shallow Climb') | (x == 'Deep Climb')).sum() / len(x) * 100,  # Climb success rate
                'driver_skill_rating': 'mean'
            }).reset_index()

            # Rename columns for display
            leaderboard_data.columns = ['Team Number', 'Avg Total Score', 'Win Rate (%)', 'Climb Success Rate (%)', 'Avg Driver Skill Rating']

            # Round numerical columns
            leaderboard_data['Avg Total Score'] = leaderboard_data['Avg Total Score'].round(1)
            leaderboard_data['Win Rate (%)'] = leaderboard_data['Win Rate (%)'].round(1)
            leaderboard_data['Climb Success Rate (%)'] = leaderboard_data['Climb Success Rate (%)'].round(1)
            leaderboard_data['Avg Driver Skill Rating'] = leaderboard_data['Avg Driver Skill Rating'].round(3)

            # Sort by Avg Total Score (descending)
            leaderboard_data = leaderboard_data.sort_values('Avg Total Score', ascending=False)

            # Display the leaderboard
            st.dataframe(leaderboard_data)

            # Bar chart for Avg Total Score
            fig_leaderboard = px.bar(
                leaderboard_data,
                x='Team Number',
                y='Avg Total Score',
                title="Average Total Score by Team",
                labels={'Avg Total Score': 'Average Total Score'},
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            fig_leaderboard.update_traces(
                hovertemplate="<b>Team %{x}</b><br>Average Total Score: %{y:.1f}"
            )
            st.plotly_chart(fig_leaderboard, use_container_width=True, key="leaderboard_bar")
        else:
            st.warning("Leaderboard data (total_score, match_result, climb_status, driver_skill_rating) not available.")

        # Score Distribution
        st.subheader("Score Distribution")
        score_metrics = ['total_score', 'auto_score', 'teleop_score', 'endgame_score']
        if all(col in filtered_df.columns for col in score_metrics):
            # Histogram of scores
            fig_scores = px.histogram(
                filtered_df,
                x=score_metrics,
                title="Distribution of Scores Across All Matches",
                labels={'value': 'Score', 'variable': 'Score Type'},
                color_discrete_sequence=px.colors.qualitative.Plotly,
                marginal="box",  # Add box plot on the side
                nbins=20
            )
            fig_scores.update_traces(
                hovertemplate="<b>Score Type: %{y}</b><br>Score: %{x}<br>Count: %{z}"
            )
            st.plotly_chart(fig_scores, use_container_width=True, key="score_distribution_hist")
        else:
            st.warning("Score data (total_score, auto_score, teleop_score, endgame_score) not available.")

        # Coral Scoring Averages
        st.subheader("Coral Scoring Averages")
        st.write("Average Coral Scored Across All Matches")
        auto_loc_cols = ['auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4']
        teleop_loc_cols = ['teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4']
        if all(col in filtered_df.columns for col in auto_loc_cols + teleop_loc_cols):
            auto_means = filtered_df[auto_loc_cols].mean().round(3)
            teleop_means = filtered_df[teleop_loc_cols].mean().round(3)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Autonomous Period**")
                for col in auto_loc_cols:
                    st.write(f"{col.replace('auto_', '').replace('_', ' ').title()}: {auto_means[col]:.3f}")
            with col2:
                st.markdown("**Teleop Period**")
                for col in teleop_loc_cols:
                    st.write(f"{col.replace('teleop_', '').replace('_', ' ').title()}: {teleop_means[col]:.3f}")

            # Bar chart for visual comparison
            means_df = pd.DataFrame({
                'Location': [col.replace('auto_', '').replace('teleop_', '').replace('_', ' ').title() for col in auto_loc_cols + teleop_loc_cols],
                'Average Count': list(auto_means) + list(teleop_means),
                'Period': ['Autonomous'] * len(auto_loc_cols) + ['Teleop'] * len(teleop_loc_cols)
            })
            fig_coral = px.bar(
                means_df,
                x='Location',
                y='Average Count',
                color='Period',
                title="Average Coral Counts by Location and Period",
                labels={'Average Count': 'Average Count'},
                color_discrete_sequence=px.colors.qualitative.Plotly,
                barmode='group'
            )
            fig_coral.update_traces(
                hovertemplate="<b>%{x}</b><br>Period: %{customdata}<br>Average Count: %{y:.3f}",
                customdata=means_df['Period']
            )
            st.plotly_chart(fig_coral, use_container_width=True, key="coral_means_bar")
        else:
            st.warning("Coral scoring data not available.")

        # Algae Management Averages
        st.subheader("Algae Management Averages")
        st.write("Average Algae Actions Across All Matches")
        for period in ['auto', 'teleop']:
            cols = [f'{period}_algae_removed', f'{period}_algae_processor', f'{period}_algae_barge']
            if all(col in filtered_df.columns for col in cols):
                algae_means = filtered_df[cols].mean().round(3)
                st.markdown(f"**{period.capitalize()} Period**")
                for col in cols:
                    st.write(f"{col.replace(f'{period}_', '').replace('_', ' ').title()}: {algae_means[col]:.3f}")

                # Bar chart for visual comparison
                algae_means_df = pd.DataFrame({
                    'Action': [col.replace(f'{period}_', '').replace('_', ' ').title() for col in cols],
                    'Average Count': list(algae_means),
                    'Period': period.capitalize()
                })
                fig_algae = px.bar(
                    algae_means_df,
                    x='Action',
                    y='Average Count',
                    title=f"{period.capitalize()} Algae Management Averages",
                    labels={'Average Count': 'Average Count'},
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_algae.update_traces(
                    hovertemplate="<b>%{x}</b><br>Average Count: %{y:.3f}"
                )
                st.plotly_chart(fig_algae, use_container_width=True, key=f"{period}_algae_means_bar")
            else:
                st.warning(f"{period.capitalize()} algae management data not available.")

        # Climb Status Distribution
        st.subheader("Climb Status Distribution")
        if 'climb_status' in filtered_df.columns:
            climb_counts = filtered_df['climb_status'].value_counts()
            fig_climb = px.pie(
                climb_counts.reset_index(),
                names='climb_status',
                values='count',
                title="Distribution of Climb Statuses Across All Matches",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_climb.update_traces(
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}"
            )
            st.plotly_chart(fig_climb, use_container_width=True, key="climb_dist_pie")

            # Display counts and percentages
            total_matches = len(filtered_df)
            for status, count in climb_counts.items():
                percentage = (count / total_matches) * 100
                st.write(f"{status}: {count} matches ({percentage:.1f}%)")
        else:
            st.warning("Climb status data not available.")

        # Performance Ratings Averages
        st.subheader("Performance Ratings Averages")
        rating_metrics = ['defense_rating', 'speed_rating', 'driver_skill_rating']
        if all(col in filtered_df.columns for col in rating_metrics):
            ratings_means = filtered_df[rating_metrics].mean().round(3)
            st.write("Average Performance Ratings Across All Matches")
            for metric in rating_metrics:
                st.write(f"{metric.replace('_', ' ').title()}: {ratings_means[metric]:.3f}")

            # Bar chart for visual comparison
            ratings_df = pd.DataFrame({
                'Metric': [metric.replace('_', ' ').title() for metric in rating_metrics],
                'Average Rating': list(ratings_means)
            })
            fig_ratings = px.bar(
                ratings_df,
                x='Metric',
                y='Average Rating',
                title="Average Performance Ratings",
                labels={'Average Rating': 'Average Rating'},
                color_discrete_sequence=px.colors.qualitative.Dark2
            )
            fig_ratings.update_traces(
                hovertemplate="<b>%{x}</b><br>Average Rating: %{y:.3f}"
            )
            st.plotly_chart(fig_ratings, use_container_width=True, key="ratings_means_bar")
        else:
            st.warning("Performance ratings (defense, speed, driver skill) not available.")

        # Scoring Trends Over Matches
        st.subheader("Scoring Trends Over Matches")
        trend_metrics = ['total_score', 'auto_score', 'teleop_score', 'endgame_score']
        if all(col in filtered_df.columns for col in trend_metrics + ['match_number']):
            # Group by match_number and calculate mean scores
            trend_data = filtered_df.copy()
            trend_data['match_number'] = pd.to_numeric(trend_data['match_number'], errors='coerce')
            trend_data = trend_data.dropna(subset=['match_number'])
            trend_data = trend_data.groupby('match_number')[trend_metrics].mean().reset_index()

            if not trend_data.empty:
                fig_trend = px.line(
                    trend_data,
                    x='match_number',
                    y=trend_metrics,
                    title="Average Scoring Trends Over Match Numbers",
                    labels={'value': 'Average Points', 'variable': 'Score Type'},
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_trend.update_traces(
                    hovertemplate="<b>Match %{x}</b><br>Score Type: %{y}<br>Average Points: %{y:.1f}"
                )
                st.plotly_chart(fig_trend, use_container_width=True, key="scoring_trends_line")
            else:
                st.warning("No valid match numbers available for trend analysis.")
        else:
            st.warning("Scoring trend data (total_score, auto_score, teleop_score, endgame_score, or match_number) not available.")

        # Correlation Analysis (using seaborn)
        st.subheader("Correlation Analysis")
        correlation_metrics = ['total_score', 'auto_score', 'teleop_score', 'endgame_score', 'defense_rating', 'speed_rating', 'driver_skill_rating']
        available_metrics = [metric for metric in correlation_metrics if metric in filtered_df.columns]
        if len(available_metrics) >= 2:
            correlation_matrix = filtered_df[available_metrics].corr()

            # Heatmap using seaborn
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1, center=0, ax=ax)
            plt.title("Correlation Between Performance Metrics")
            st.pyplot(fig)

            # Display correlation matrix as a table
            st.write("Correlation Matrix")
            st.dataframe(correlation_matrix.style.format("{:.3f}"))
        else:
            st.warning("Not enough metrics available for correlation analysis (at least two numeric metrics required).")

        # Raw Data Table
        st.subheader("Raw Match Data")
        if all(col in filtered_df.columns for col in ['match_number', 'team_number']):
            display_df = filtered_df.copy()
            display_df['match_number'] = pd.to_numeric(display_df['match_number'], errors='coerce')
            display_df['team_number'] = pd.to_numeric(display_df['team_number'], errors='coerce')
            display_df = display_df.sort_values(['match_number', 'team_number'], ascending=[False, True])
            st.dataframe(display_df)
        else:
            st.warning("Cannot display raw data table: 'match_number' or 'team_number' columns are missing.")

        # Export Options
        st.subheader("Export Data")
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name=f"scouting_data_filtered_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="download_filtered_data"
        )