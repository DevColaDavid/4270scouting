import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
import time
from utils.tba_api import get_team_info, get_team_events, get_event_teams, get_event_matches, search_teams, get_tba_api_key

st.set_page_config(page_title="TBA Data", page_icon="🔍", layout="wide")

st.title("TBA Data")

# Ensure API key is available
tba_api_key = get_tba_api_key()
if not tba_api_key:
    st.error("API Key is not configured. Please set it up in your environment.")
    st.stop()

# Cache API requests to reduce load, but allow clearing the cache for periodic refresh
@st.cache_data(ttl=600)
def get_team_info_cached(team_number):
    try:
        return get_team_info(team_number)
    except Exception as e:
        st.error(f"Failed to fetch team info: {str(e)}")
        return None

# Dynamic year selection
current_year = datetime.now().year
year_options = list(range(current_year, 2015, -1))  # Adjust range as needed

# Session state for team input
if "team_input" not in st.session_state:
    st.session_state.team_input = "254"

def update_team_input():
    st.session_state.team_input = st.session_state.new_team_input

# Periodic refresh mechanism
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# Refresh every 60 seconds
REFRESH_INTERVAL = 60  # seconds
current_time = time.time()
if current_time - st.session_state.last_refresh >= REFRESH_INTERVAL:
    st.session_state.last_refresh = current_time
    # Clear the cache to force a refresh of the data
    get_team_info_cached.clear()
    st.rerun()

# Display a small indicator to show the last refresh time
st.write(f"Last refreshed: {datetime.fromtimestamp(st.session_state.last_refresh).strftime('%Y-%m-%d %H:%M:%S')} (refreshes every {REFRESH_INTERVAL} seconds)")

# Team input and year selection
team_input = st.text_input("Enter Team Number", st.session_state.team_input, key="new_team_input", on_change=update_team_input)
selected_year = st.selectbox("Select Year", options=year_options, index=0)

# Fetch team data
team_data = get_team_info_cached(team_input)
if team_data:
    st.subheader(f"Team {team_data['team_number']} - {team_data.get('nickname', 'N/A')}")
    st.write(f"**Full Name:** {team_data['name']}")
    st.write(f"**Rookie Year:** {team_data.get('rookie_year', 'N/A')}")

    # Fetch event data
    team_events = get_team_events(team_input, selected_year)
    if team_events:
        event_list = [
            {
                "Name": event.get("name"),
                "Location": f"{event.get('city', 'N/A')}, {event.get('state_prov', 'N/A')}",
                "Start Date": event.get('start_date', 'N/A'),
                "Event Key": event.get("key")
            } for event in team_events
        ]

        if event_list:
            event_df = pd.DataFrame(event_list)
            event_df["Start Date"] = pd.to_datetime(event_df["Start Date"], errors='coerce')
            event_df = event_df.sort_values("Start Date")
            st.dataframe(event_df.drop(columns=["Event Key"]), use_container_width=True)
    else:
        st.info("No events found for this team in the selected year.")

    # Fetch matches
    event_keys = [event["Event Key"] for event in event_list] if event_list else []
    selected_event = st.selectbox("Select Event", options=event_keys, format_func=lambda x: next((e["Name"] for e in event_list if e["Event Key"] == x), x))

    if selected_event:
        match_data = get_event_matches(selected_event)
        if match_data:
            matches = []
            team_key = f"frc{team_input}"
            for match in match_data:
                if team_key in match.get("alliances", {}).get("red", {}).get("team_keys", []) or team_key in match.get("alliances", {}).get("blue", {}).get("team_keys", []):
                    alliance = "red" if team_key in match["alliances"]["red"]["team_keys"] else "blue"
                    result = "Win" if match["winning_alliance"] == alliance else "Loss" if match["winning_alliance"] else "Tie"
                    matches.append({
                        "Match": f"{match.get('comp_level', '').upper()}{match.get('match_number', '')}",
                        "Alliance": alliance.title(),
                        "Result": result,
                        "Score": match["alliances"][alliance]["score"]
                    })

            match_df = pd.DataFrame(matches)
            if not match_df.empty:
                st.dataframe(match_df, use_container_width=True)
                st.plotly_chart(px.line(match_df, x="Match", y="Score", title="Match Scores"), use_container_width=True)
        else:
            st.info("No match data available for this event.")
else:
    st.error("Could not retrieve team information.")