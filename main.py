# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from utils.utils import load_data, calculate_match_score, setup_sidebar_navigation, PAGE_CONFIG, get_firebase_instances

# Set page configuration as the first command
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

# Initialize Firebase using the utility function
print("Attempting to initialize Firebase in Main page...")
try:
    db, bucket = get_firebase_instances()
    st.session_state.firebase_db = db
    st.session_state.firebase_bucket = bucket
    print("Firebase initialized successfully in Main page")
except Exception as e:
    st.error(f"Failed to initialize Firebase: {str(e)}")
    print(f"Firebase initialization failed in Main page: {str(e)}")
    st.stop()

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "authority" not in st.session_state:
    st.session_state.authority = None
if "active_page" not in st.session_state:
    st.session_state.active_page = "Main"  # Default to "Main" for the main page

# Check if the users collection is empty and create an initial Owner user
def initialize_owner_user():
    db = st.session_state.firebase_db
    users_ref = db.collection('users').limit(1).get()
    if not users_ref:  # If the users collection is empty
        initial_owner = {
            "username": "Owner",
            "password": hash_password("ownerpass123"),  # Default password, change it after first login
            "authority": "Owner"
        }
        db.collection('users').document("initial_owner").set(initial_owner)
        st.warning("No users found in Firestore. Created an initial Owner user with username 'Owner' and password 'ownerpass123'. Please log in and change the password immediately.")

# Call the function to initialize the Owner user
initialize_owner_user()

# Login function using Firestore
def login(username, password):
    db = st.session_state.firebase_db
    hashed_password = hash_password(password)
    try:
        # Query the users collection for the username
        users_ref = db.collection('users').where('username', '==', username).limit(1).get()
        if not users_ref:
            st.error("Invalid username or password")
            return
        user_doc = users_ref[0].to_dict()
        if user_doc['password'] == hashed_password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.authority = user_doc['authority']
            st.success(f"Logged in as {username} ({st.session_state.authority})")
            st.rerun()
        else:
            st.error("Invalid username or password")
    except Exception as e:
        st.error(f"Error during login: {e}")

# If not logged in, show the login form
if not st.session_state.logged_in:
    # Set up the sidebar navigation (will be empty since user is not logged in)
    setup_sidebar_navigation()
    
    st.title("🔒 Login to FRC 2025 Scouting Dashboard")
    with st.form(key="login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        if submit_button:
            login(username, password)
    st.stop()

# Set up the sidebar navigation (only runs if user is logged in)
setup_sidebar_navigation()

# Main content (only shown on the "Main" page)
st.title("FRC 2025 Scouting Dashboard")
st.markdown(f"""
Welcome to the FRC 2025 Scouting Dashboard, {st.session_state.username}! This tool helps teams collect and analyze match data.
""")

# Display features based on accessible pages
accessible_pages = [
    page for page, config in PAGE_CONFIG.items()
    if st.session_state.authority in config["authorities"]
]
if accessible_pages:
    st.markdown("### Features:")
    features = {
        "Match Scouting": "Match Scouting Form: Available to Scouters, Admins, and Owners.",
        "Data Analysis": "Data Analysis Dashboard: Available to all users.",
        "Team Statistics": "Team Statistics: Available to all users.",
        "Match Prediction": "Match Prediction: Available to all users.",
        "TBA Integration": "TBA Integration: Available to all users.",
        "Match Schedule": "Match Schedule: Available to Admins and Owners.",
        "Data Management": "Data Management: Available to Admins and Owners.",
        "User Management": "User Management: Available to Owners only (in Data Management)."
    }
    for page, description in features.items():
        # Only show features for pages the user can access
        # Special case for User Management, which is part of Data Management
        if page == "User Management":
            if "Data Management" in accessible_pages and st.session_state.authority == "Owner":
                st.markdown(f"- {description}")
        elif page in accessible_pages and page != "Main":
            st.markdown(f"- {description}")

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
                'climb_status', 'auto_taxi_left'
            ]
            score_columns = ['auto_score', 'teleop_score', 'endgame_score', 'total_score']
            if all(col in df.columns for col in required_columns):
                # Only calculate scores if they don't already exist
                if not all(col in df.columns for col in score_columns):
                    scores = df.apply(calculate_match_score, axis=1)
                    df[score_columns] = scores
            else:
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
                'auto_taxi_left', 'climb_status', 'auto_score', 'teleop_score', 'endgame_score', 'total_score'
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
                'climb_status', 'auto_taxi_left'
            ]
            score_columns = ['auto_score', 'teleop_score', 'endgame_score', 'total_score']
            if all(col in df.columns for col in required_columns):
                # Only calculate scores if they don't already exist
                if not all(col in df.columns for col in score_columns):
                    scores = df.apply(calculate_match_score, axis=1)
                    df[score_columns] = scores
            else:
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

# App Layout (only shown on the "Main" page)
display_quick_stats()
display_recent_matches()