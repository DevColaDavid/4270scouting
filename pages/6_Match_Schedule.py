# app/6_Match_Schedule.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
from utils.utils import setup_sidebar_navigation

st.set_page_config(page_title="Match Schedule", page_icon="📅", layout="wide",initial_sidebar_state="collapsed")

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in to access this page.")
    st.stop()

# Set up the sidebar navigation
setup_sidebar_navigation()

# Page content
st.title("Data Management")
st.write("This is the Data Management page.")

# Check if the user is logged in and has the appropriate authority
if not st.session_state.get("logged_in", False):
    st.error("You must be logged in to access this page.")
    st.stop()

# Check user authority
allowed_authorities = ["Scouter", "Admin", "Owner","Viewer"]
if st.session_state.get("authority") not in allowed_authorities:
    st.error("You do not have the required authority to access this page. Required: Scouter, Admin, or Owner.")
    st.stop()

st.title("📅 Match Schedule")
st.markdown("View the match schedule for a specific event to plan your scouting.")

# Use Streamlit secrets for the TBA API key
try:
    TBA_API_KEY = st.secrets["TBA"]["TBA_API_KEY"]
except KeyError:
    st.error("TBA API key not found in .streamlit/secrets.toml. Please ensure the file exists and contains 'TBA_API_KEY' under the [TBA] section.")
    st.stop()

# Base URL for The Blue Alliance API v3
BASE_URL = "https://www.thebluealliance.com/api/v3"

# Headers for API requests
headers = {
    "X-TBA-Auth-Key": TBA_API_KEY,
    "User-Agent": "ScoutingApp/1.0"
}

# Simple mapping of event locations to timezones (approximate)
EVENT_TIMEZONES = {
    "cmptx": "America/Chicago",  # Houston, TX (Championship)
    "cmpmo": "America/Chicago",  # St. Louis, MO (Championship in past years)
    "txho": "America/Chicago",   # Houston, TX
    "cacc": "America/Los_Angeles",  # California events
    "oncmp": "America/Toronto",  # Ontario, Canada
    "hiho": "Pacific/Honolulu",  # Honolulu, HI (for 2025hiho)
    # Add more mappings as needed
}

# Function to fetch all events for a given year
def fetch_events_for_year(year):
    url = f"{BASE_URL}/events/{year}/simple"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        events = response.json()
        return events
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching events for {year}: {e}")
        return []

# Function to fetch event details (to get location for timezone)
def fetch_event_details(event_key):
    url = f"{BASE_URL}/event/{event_key}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        event = response.json()
        return event
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching event details: {e}")
        return None

# Function to fetch match schedule from TBA API (live data only)
def fetch_match_schedule(event_key):
    url = f"{BASE_URL}/event/{event_key}/matches"
    try:
        # Always fetch live data
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        matches = response.json()
        return matches
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            st.error(f"Event key '{event_key}' not found. Please check the event key and try again.")
        else:
            st.error(f"Error fetching match schedule: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to The Blue Alliance API: {e}")
        return None

# Function to process match data into a DataFrame
def process_match_data(matches, event_key, team_number_filter=None):
    if not matches:
        return pd.DataFrame()

    # Fetch event details to determine timezone
    event = fetch_event_details(event_key)
    if event and 'timezone' in event:
        event_timezone = event['timezone']
    else:
        # Fallback: Guess timezone based on event key
        event_code = event_key[4:]  # e.g., 'cmptx' from '2025cmptx'
        event_timezone = EVENT_TIMEZONES.get(event_code, "UTC")
        st.warning(f"Could not determine event timezone. Using {event_timezone} as a fallback.")

    timezone = pytz.timezone(event_timezone)

    # List to store match data
    match_list = []

    for match in matches:
        # Skip matches that aren't qualification or playoff matches
        if match['comp_level'] not in ['qm', 'qf', 'sf', 'f']:
            continue

        # Extract match number and competition level
        comp_level = match['comp_level']
        match_number = match['match_number']
        
        # Convert comp_level to a readable format
        if comp_level == 'qm':
            comp_level_readable = "Qualification"
        elif comp_level == 'qf':
            comp_level_readable = "Quarterfinal"
        elif comp_level == 'sf':
            comp_level_readable = "Semifinal"
        elif comp_level == 'f':
            comp_level_readable = "Final"
        
        match_display = f"{comp_level_readable} {match_number}"

        # Extract team numbers for Red and Blue alliances
        red_teams = match['alliances']['red']['team_keys']
        blue_teams = match['alliances']['blue']['team_keys']
        
        # Remove 'frc' prefix from team keys for display
        red_teams = [team.replace('frc', '') for team in red_teams]
        blue_teams = [team.replace('frc', '') for team in blue_teams]
        
        red_teams_str = ", ".join(red_teams)
        blue_teams_str = ", ".join(blue_teams)

        # Check if the filtered team is in this match
        highlight = False
        if team_number_filter:
            highlight = team_number_filter in red_teams or team_number_filter in blue_teams

        # Extract scheduled and actual times
        scheduled_time = match.get('time')
        actual_time = match.get('actual_time')

        # Determine the display time
        if actual_time:
            match_time = datetime.utcfromtimestamp(actual_time)
            match_time = pytz.utc.localize(match_time).astimezone(timezone)
            time_display = match_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        elif scheduled_time:
            match_time = datetime.utcfromtimestamp(scheduled_time)
            match_time = pytz.utc.localize(match_time).astimezone(timezone)
            time_display = match_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        else:
            time_display = "Not scheduled"

        # Get match outcome if played
        outcome = "N/A"
        if actual_time:
            red_score = match['alliances']['red']['score']
            blue_score = match['alliances']['blue']['score']
            if red_score > blue_score:
                outcome = "Red Wins"
            elif blue_score > red_score:
                outcome = "Blue Wins"
            else:
                outcome = "Tie"

        # Determine if the match is completed based on the outcome
        is_completed = outcome != "N/A"

        # Add match data to the list (no Status column)
        match_list.append({
            "Match": match_display,
            "Time": time_display,
            "Red Alliance": red_teams_str,
            "Blue Alliance": blue_teams_str,
            "Outcome": outcome,
            "Highlight": highlight,
            "IsCompleted": is_completed  # Hidden column for CSS
        })

    # Create DataFrame
    df = pd.DataFrame(match_list)
    
    if df.empty:
        return df

    # Sort by match type and number
    df['match_type_order'] = df['Match'].apply(lambda x: {'Qualification': 1, 'Quarterfinal': 2, 'Semifinal': 3, 'Final': 4}[x.split()[0]])
    df['match_number'] = df['Match'].apply(lambda x: int(x.split()[1]))
    df = df.sort_values(by=['match_type_order', 'match_number']).drop(columns=['match_type_order', 'match_number'])

    # Filter by team number if provided
    if team_number_filter:
        df = df[df['Highlight']]

    return df

# Initialize session state for selected event and custom event key
if 'selected_event' not in st.session_state:
    st.session_state.selected_event = None
if 'custom_event_key' not in st.session_state:
    st.session_state.custom_event_key = ""

# Fetch available events for 2025
events = fetch_events_for_year(2025)
event_options = {f"{event['name']} ({event['event_code']})": event['key'] for event in events}
event_options["Custom Event Key"] = "custom"

# Input section
st.markdown("### Event Details")
col1, col2 = st.columns(2)
with col1:
    # Use session state to persist the selected event
    selected_event = st.selectbox(
        "Select an Event",
        options=list(event_options.keys()),
        index=list(event_options.keys()).index(st.session_state.selected_event) if st.session_state.selected_event in event_options else 0,
        help="Select an event or choose 'Custom Event Key' to enter a specific key."
    )
    # Update session state when the user selects an event
    st.session_state.selected_event = selected_event

    if selected_event == "Custom Event Key":
        # Use session state to persist the custom event key
        event_key = st.text_input(
            "Custom Event Key",
            value=st.session_state.custom_event_key,
            help="Enter the event key, e.g., '2025cmptx' for the 2025 Championship in Houston."
        )
        # Update session state when the user enters a custom event key
        st.session_state.custom_event_key = event_key
    else:
        event_key = event_options[selected_event]
        # Clear the custom event key in session state if not using a custom event
        st.session_state.custom_event_key = ""
with col2:
    team_number_filter = st.text_input("Filter by Team Number (optional)", value="", help="Enter a team number to show only their matches.")

# Fetch and display match schedule
if event_key:
    with st.spinner("Fetching match schedule..."):
        matches = fetch_match_schedule(event_key)
        if matches:
            df = process_match_data(matches, event_key, team_number_filter)
            if not df.empty:
                st.subheader(f"Match Schedule for Event {event_key}")
                # Add custom CSS to highlight filtered matches, color alliances, and highlight completed matches
                st.markdown("""
                    <style>
                    /* Highlight rows for filtered team */
                    tr:has(td[data-highlight="True"]) {
                        background-color: #e6f3ff; /* Light blue background for filtered teams */
                    }
                    /* Color Red Alliance column */
                    td:nth-child(3) {
                        color: #d32f2f; /* Red */
                        font-weight: bold;
                    }
                    /* Color Blue Alliance column */
                    td:nth-child(4) {
                        color: #1976d2; /* Blue */
                        font-weight: bold;
                    }
                    /* Highlight completed matches in light blue */
                    tr:has(td[data-completed="True"]) {
                        background-color: #e6f3ff; /* Light blue for completed matches */
                    }
                    /* Style not-yet-completed matches with a white background */
                    tr:has(td[data-completed="False"]) {
                        background-color: #ffffff; /* White for not-yet-completed matches */
                    }
                    </style>
                """, unsafe_allow_html=True)

                # Add data-testid attributes for CSS targeting
                for i, row in df.iterrows():
                    df.at[i, 'IsCompleted'] = str(row['IsCompleted'])
                    df.at[i, 'Highlight'] = str(row['Highlight'])
                
                # Drop hidden columns before rendering
                display_df = df.drop(columns=['IsCompleted', 'Highlight'])
                
                # Render the table using st.markdown
                st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            else:
                st.warning("No qualification or playoff matches found for this event.")
else:
    st.info("Please enter an event key to view the match schedule.")