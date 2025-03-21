# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, save_data, clear_data, calculate_match_score

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

# Sidebar navigation is automatically handled by Streamlit via the pages/ directory
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
            # Check if required columns for calculate_match_score are present
            required_columns = [
                'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
                'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
                'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
                'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
                'climb_status'
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.warning(f"Cannot calculate match scores. Missing columns: {missing_columns}")
                return

            # Calculate scores
            df = df.join(df.apply(calculate_match_score, axis=1))

            # Check if all display columns are present
            display_columns = ['match_number', 'team_number', 'auto_score', 'teleop_score', 'endgame_score', 'total_score']
            missing_display_columns = [col for col in display_columns if col not in df.columns]
            if missing_display_columns:
                st.warning(f"Cannot display recent matches. Missing columns: {missing_display_columns}")
                return

            st.subheader("Recent Matches")
            st.dataframe(df.tail(5)[display_columns])
        else:
            st.info("No match data available yet. Start by adding match data in the Match Scouting page!")
    except Exception as e:
        st.error(f"Error loading recent matches: {str(e)}")

# Display quick stats
def display_quick_stats():
    try:
        df = load_data()
        if df is not None and not df.empty:
            # Check if required columns for calculate_match_score are present
            required_columns = [
                'auto_coral_l1', 'auto_coral_l2', 'auto_coral_l3', 'auto_coral_l4',
                'auto_algae_barge', 'auto_algae_processor', 'auto_algae_removed',
                'teleop_coral_l1', 'teleop_coral_l2', 'teleop_coral_l3', 'teleop_coral_l4',
                'teleop_algae_barge', 'teleop_algae_processor', 'teleop_algae_removed',
                'climb_status'
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.warning(f"Cannot calculate match scores for statistics. Missing columns: {missing_columns}")
                return

            # Calculate scores
            df = df.join(df.apply(calculate_match_score, axis=1))

            # Check if required columns for stats are present
            if 'team_number' not in df.columns or 'total_score' not in df.columns:
                st.warning("Cannot display statistics. Missing required columns: 'team_number' and/or 'total_score'.")
                return

            st.subheader("Quick Stats")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Matches", len(df))

            with col2:
                st.metric("Teams Scouted", df['team_number'].nunique())

            with col3:
                avg_score = df['total_score'].mean()
                st.metric("Avg Score", f"{avg_score:.1f}")
        else:
            st.info("No statistics available yet. Add match data to see stats.")
    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")

# App Layout
display_quick_stats()
display_recent_matches()

# Data Management in Sidebar
st.sidebar.title("Data Management")
if st.sidebar.button("⚠️ Clear All Data"):
    # Add a confirmation prompt to prevent accidental data deletion
    if st.sidebar.checkbox("Are you sure? This will delete all data.", key="confirm_clear_data"):
        if clear_data():
            st.sidebar.success("All data cleared successfully!")
            st.rerun()
        else:
            st.sidebar.error("Error clearing data.")
    else:
        st.sidebar.warning("Please confirm to clear all data.")

# Add a download button for scouting_data.csv
df = load_data()
if df is not None and not df.empty:
    csv = df.to_csv(index=False)
    st.sidebar.download_button(
        label="Download Data as CSV",
        data=csv,
        file_name="scouting_data.csv",
        mime="text/csv"
    )