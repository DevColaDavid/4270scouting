# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, calculate_match_score

# Set page configuration
st.set_page_config(
    page_title="FRC 2025 Scouting Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed", 
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Configure Streamlit to handle connection issues
if 'websocket_retry_counter' not in st.session_state:
    st.session_state.websocket_retry_counter = 0

# Disable websocket warning messages
st.set_option('client.showErrorDetails', False)

# Hide Streamlit's default menu and footer for cleaner mobile view
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Main content
st.title("FRC 2025 Scouting Dashboard")
st.markdown("""
Welcome to the FRC 2025 Scouting Dashboard! This tool helps teams collect and analyze match data.

### Features:
- Match Scouting Form
- Data Analysis Dashboard
- Team Statistics
- Export Capabilities
""")

# Display recent matches
def display_recent_matches():
    try:
        df = load_data()
        if df is not None and not df.empty:
            # Calculate scores if possible
            required_columns = [
                'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
                'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
                'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
                'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
                'climb_status'
            ]
            if all(col in df.columns for col in required_columns):
                df = df.join(df.apply(calculate_match_score, axis=1))
            else:
                # If scores can't be calculated, proceed without them
                st.warning("Match scores not calculated due to missing data.")

            # Sort by timestamp (if available) to get the most recent responses
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df = df.sort_values(by='timestamp', ascending=False, na_position='last')
            else:
                # If timestamp is not available, use the DataFrame order (most recent at the bottom)
                df = df.sort_index(ascending=False)

            # Display the 7 most recent responses (not unique matches)
            display_columns = [
                'match_number', 'team_number', 'scouter_name', 'timestamp',
                'auto_score', 'teleop_score', 'endgame_score', 'total_score'
            ]
            available_display_columns = [col for col in display_columns if col in df.columns]
            if available_display_columns:
                st.subheader("Recent Responses (Last 7)")
                st.dataframe(df.head(7)[available_display_columns])
            else:
                st.info("No response data available to display.")
        else:
            st.info("No response data available yet. Start by adding match data in the Match Scouting page!")
    except Exception as e:
        st.error(f"Error loading recent responses: {str(e)}")

# Display quick stats
def display_quick_stats():
    try:
        df = load_data()
        if df is not None and not df.empty:
            # Calculate scores if possible
            required_columns = [
                'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
                'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
                'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
                'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
                'climb_status'
            ]
            if all(col in df.columns for col in required_columns):
                df = df.join(df.apply(calculate_match_score, axis=1))
            else:
                # If scores can't be calculated, proceed without them
                st.warning("Match scores not calculated due to missing data.")

            st.subheader("Quick Stats")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Responses", len(df))

            with col2:
                if 'team_number' in df.columns:
                    st.metric("Teams Scouted", df['team_number'].nunique())
                else:
                    st.metric("Teams Scouted", "N/A")

            with col3:
                if 'total_score' in df.columns:
                    avg_score = df['total_score'].mean()
                    st.metric("Avg Score", f"{avg_score:.1f}")
                else:
                    st.metric("Avg Score", "N/A")
        else:
            st.info("No statistics available yet. Add match data to see stats.")
    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")

# App Layout
display_quick_stats()
display_recent_matches()