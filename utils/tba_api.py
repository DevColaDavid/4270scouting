import requests
import pandas as pd
import streamlit as st
import os

def get_tba_api_key():
    # Hard-coded API key as a guaranteed fallback
    api_key = "AtRqAwQCHvqjWbR0byQNshqReqs3dhub4sQkIxRnN0OuvUAZ3WdMaxtzdzWfOKGi"
    
    # Try Replit environment variables first (this is where Replit Secrets go)
    try:
        import os
        env_key = os.environ.get('TBA_API_KEY')
        if env_key and len(env_key.strip()) > 0:
            api_key = env_key
            print("Found API key in environment variables")
    except Exception as e:
        print(f"Error accessing environment variables: {str(e)}")
    
    # For debugging purposes, show where the key is coming from
    print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
        
    return api_key

def make_tba_request(endpoint):
    """Make a request to The Blue Alliance API"""
    api_key = get_tba_api_key()

    if not api_key:
        st.error("TBA API key not found. Please add it to your Replit Secrets with key 'TBA_API_KEY'.")
        return None

    base_url = "https://www.thebluealliance.com/api/v3"
    headers = {
        "X-TBA-Auth-Key": api_key
    }

    try:
        response = requests.get(f"{base_url}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data from TBA: {str(e)}")
        return None

def get_team_info(team_number):
    """Get information about a specific team"""
    team_key = f"frc{team_number}"
    return make_tba_request(f"/team/{team_key}")

def get_team_events(team_number, year=None):
    """Get events for a specific team, optionally filtered by year"""
    team_key = f"frc{team_number}"
    if year:
        return make_tba_request(f"/team/{team_key}/events/{year}")
    return make_tba_request(f"/team/{team_key}/events")

def get_event_teams(event_key):
    """Get teams participating in a specific event"""
    return make_tba_request(f"/event/{event_key}/teams")

def get_event_matches(event_key):
    """Get matches for a specific event"""
    return make_tba_request(f"/event/{event_key}/matches")

def search_teams(query):
    """Search for teams matching a query"""
    # Unfortunately, TBA doesn't have a direct search endpoint
    # We'll use a limited approach by fetching teams by page
    teams = []
    page = 0
    while True:
        page_teams = make_tba_request(f"/teams/{page}")
        if not page_teams or len(page_teams) == 0:
            break
        teams.extend(page_teams)
        page += 1

    # Filter teams based on query
    filtered_teams = []
    for team in teams:
        if (query.lower() in str(team.get('team_number', '')).lower() or 
            query.lower() in team.get('nickname', '').lower() or
            query.lower() in team.get('name', '').lower()):
            filtered_teams.append(team)

    return filtered_teams