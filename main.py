# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.utils import load_data, save_data, clear_data, calculate_match_score
import pages  # This is just to ensure the pages are loaded by Streamlit

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

# Sidebar navigation (Streamlit automatically handles this with the pages directory)
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
    df = load_data()
    if df is not None and not df.empty:
        # Calculate scores using the Reefscape point system
        df = df.join(df.apply(calculate_match_score, axis=1))
        st.subheader("Recent Matches")
        st.dataframe(df.tail(5)[['match_number', 'team_number', 'auto_score', 'teleop_score', 'endgame_score', 'total_score']])
    else:
        st.info("No match data available yet. Start by adding match data in the Match Scouting page!")

# Display quick stats
def display_quick_stats():
    try:
        df = load_data()
        if df is not None and not df.empty:
            # Calculate scores using the Reefscape point system
            df = df.join(df.apply(calculate_match_score, axis=1))
            st.subheader("Quick Stats")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Matches", len(df))

            with col2:
                st.metric("Teams Scouted", df['team_number'].nunique())

            with col3:
                avg_score = df['total_score'].mean()
                st.metric("Avg Score", f"{avg_score:.1f}")
    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")

# App Layout
display_quick_stats()
display_recent_matches()

# Data Management
st.sidebar.title("Data Management")
if st.sidebar.button("⚠️ Clear All Data"):
    if clear_data():
        st.sidebar.success("All data cleared successfully!")
        st.rerun() 
    else:
        st.sidebar.error("Error clearing data.")