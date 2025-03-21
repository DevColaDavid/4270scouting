# pages/1_Match_Scouting.py
import streamlit as st
import pandas as pd
from utils.utils import save_data
import time  # Import time for adding a delay

st.set_page_config(page_title="Match Scouting", page_icon="🏟️", layout="wide")

st.title("Match Scouting")

# Initialize session state for form data
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

# Match Information
st.subheader("Match Information")
col1, col2, col3 = st.columns(3)
with col1:
    match_number = st.number_input("Match Number", min_value=1, step=1, value=1)
with col2:
    team_number = st.number_input("Team Number", min_value=1, step=1, value=1)
with col3:
    alliance_color = st.selectbox("Alliance Color", options=["Red", "Blue"])

# Scouter Information
st.subheader("Scouter Information")
scouter_name = st.text_input("Scouter Name", placeholder="Enter your name")

# Starting Position
st.subheader("Starting Position")
starting_position = st.selectbox("Starting Position", options=["Left", "Center", "Right"])
st.markdown("*From driver's view*")

# Autonomous Period
st.subheader("Autonomous Period")
st.markdown("**Coral Scored**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    auto_coral_l1 = st.number_input("Level 1", min_value=0, step=1, key="auto_coral_l1")
with col2:
    auto_coral_l2 = st.number_input("Level 2", min_value=0, step=1, key="auto_coral_l2")
with col3:
    auto_coral_l3 = st.number_input("Level 3", min_value=0, step=1, key="auto_coral_l3")
with col4:
    auto_coral_l4 = st.number_input("Level 4", min_value=0, step=1, key="auto_coral_l4")

st.markdown("**Coral Missed**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    auto_missed_coral_l1 = st.number_input("Missed Level 1", min_value=0, step=1, key="auto_missed_coral_l1")
with col2:
    auto_missed_coral_l2 = st.number_input("Missed Level 2", min_value=0, step=1, key="auto_missed_coral_l2")
with col3:
    auto_missed_coral_l3 = st.number_input("Missed Level 3", min_value=0, step=1, key="auto_missed_coral_l3")
with col4:
    auto_missed_coral_l4 = st.number_input("Missed Level 4", min_value=0, step=1, key="auto_missed_coral_l4")

st.markdown("**Algae Management**")
col1, col2, col3 = st.columns(3)
with col1:
    auto_algae_barge = st.number_input("Algae to Barge", min_value=0, step=1, key="auto_algae_barge")
with col2:
    auto_algae_processor = st.number_input("Algae to Processor", min_value=0, step=1, key="auto_algae_processor")
with col3:
    auto_algae_removed = st.number_input("Algae Removed", min_value=0, step=1, key="auto_algae_removed")

st.markdown("**Missed Algae**")
col1, col2 = st.columns(2)
with col1:
    auto_missed_algae_barge = st.number_input("Missed Algae to Barge", min_value=0, step=1, key="auto_missed_algae_barge")
with col2:
    auto_missed_algae_processor = st.number_input("Missed Algae to Processor", min_value=0, step=1, key="auto_missed_algae_processor")

# Teleop Period
st.subheader("Teleop Period")
st.markdown("**Coral Scored**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    teleop_coral_l1 = st.number_input("Level 1", min_value=0, step=1, key="teleop_coral_l1")
with col2:
    teleop_coral_l2 = st.number_input("Level 2", min_value=0, step=1, key="teleop_coral_l2")
with col3:
    teleop_coral_l3 = st.number_input("Level 3", min_value=0, step=1, key="teleop_coral_l3")
with col4:
    teleop_coral_l4 = st.number_input("Level 4", min_value=0, step=1, key="teleop_coral_l4")

st.markdown("**Coral Missed**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    teleop_missed_coral_l1 = st.number_input("Missed Level 1", min_value=0, step=1, key="teleop_missed_coral_l1")
with col2:
    teleop_missed_coral_l2 = st.number_input("Missed Level 2", min_value=0, step=1, key="teleop_missed_coral_l2")
with col3:
    teleop_missed_coral_l3 = st.number_input("Missed Level 3", min_value=0, step=1, key="teleop_missed_coral_l3")
with col4:
    teleop_missed_coral_l4 = st.number_input("Missed Level 4", min_value=0, step=1, key="teleop_missed_coral_l4")

st.markdown("**Algae Management**")
col1, col2, col3 = st.columns(3)
with col1:
    teleop_algae_barge = st.number_input("Algae to Barge", min_value=0, step=1, key="teleop_algae_barge")
with col2:
    teleop_algae_processor = st.number_input("Algae to Processor", min_value=0, step=1, key="teleop_algae_processor")
with col3:
    teleop_algae_removed = st.number_input("Algae Removed", min_value=0, step=1, key="teleop_algae_removed")

st.markdown("**Missed Algae**")
col1, col2 = st.columns(2)
with col1:
    teleop_missed_algae_barge = st.number_input("Missed Algae to Barge", min_value=0, step=1, key="teleop_missed_algae_barge")
with col2:
    teleop_missed_algae_processor = st.number_input("Missed Algae to Processor", min_value=0, step=1, key="teleop_missed_algae_processor")

# Endgame
st.subheader("Endgame")
climb_status = st.selectbox("Climb Status", options=["No Climb", "Shallow Climb", "Deep Climb"])

# Performance Ratings
st.subheader("Performance Ratings")
col1, col2, col3 = st.columns(3)
with col1:
    defense_rating = st.slider("Defense Rating", min_value=0.0, max_value=5.0, step=0.1, value=0.0)
with col2:
    speed_rating = st.slider("Speed Rating", min_value=0.0, max_value=5.0, step=0.1, value=0.0)
with col3:
    driver_skill_rating = st.slider("Driver Skill Rating", min_value=0.0, max_value=5.0, step=0.1, value=0.0)

# Qualitative Assessments
st.subheader("Qualitative Assessments")
defense_qa = st.text_area("Defense Observations", placeholder="Describe defensive plays...")
teleop_qa = st.text_area("Teleop Observations", placeholder="Describe teleop performance...")
auto_qa = st.text_area("Autonomous Observations", placeholder="Describe autonomous performance...")

# Additional Information
st.subheader("Additional Information")
comments = st.text_area("Comments", placeholder="Any additional comments...")
match_result = st.selectbox("Match Result", options=["Win", "Loss", "Tie"])

# Submit Button
submit_button = st.button(label="Submit Match Data")

# Collect form data
match_data = {
    "match_number": match_number,
    "team_number": team_number,
    "alliance_color": alliance_color,
    "scouter_name": scouter_name,
    "starting_position": starting_position,
    "auto_coral_l1": auto_coral_l1,
    "auto_coral_l2": auto_coral_l2,
    "auto_coral_l3": auto_coral_l3,
    "auto_coral_l4": auto_coral_l4,
    "auto_missed_coral_l1": auto_missed_coral_l1,
    "auto_missed_coral_l2": auto_missed_coral_l2,
    "auto_missed_coral_l3": auto_missed_coral_l3,
    "auto_missed_coral_l4": auto_missed_coral_l4,
    "auto_algae_barge": auto_algae_barge,
    "auto_algae_processor": auto_algae_processor,
    "auto_algae_removed": auto_algae_removed,
    "auto_missed_algae_barge": auto_missed_algae_barge,
    "auto_missed_algae_processor": auto_missed_algae_processor,
    "teleop_coral_l1": teleop_coral_l1,
    "teleop_coral_l2": teleop_coral_l2,
    "teleop_coral_l3": teleop_coral_l3,
    "teleop_coral_l4": teleop_coral_l4,
    "teleop_missed_coral_l1": teleop_missed_coral_l1,
    "teleop_missed_coral_l2": teleop_missed_coral_l2,
    "teleop_missed_coral_l3": teleop_missed_coral_l3,
    "teleop_missed_coral_l4": teleop_missed_coral_l4,
    "teleop_algae_barge": teleop_algae_barge,
    "teleop_algae_processor": teleop_algae_processor,
    "teleop_algae_removed": teleop_algae_removed,
    "teleop_missed_algae_barge": teleop_missed_algae_barge,
    "teleop_missed_algae_processor": teleop_missed_algae_processor,
    "climb_status": climb_status,
    "defense_rating": defense_rating,
    "speed_rating": speed_rating,
    "driver_skill_rating": driver_skill_rating,
    "defense_qa": defense_qa,
    "teleop_qa": teleop_qa,
    "auto_qa": auto_qa,
    "comments": comments,
    "match_result": match_result
}

# Handle form submission
if submit_button:
    # Validate team_number and match_number
    if not (isinstance(team_number, (int, float)) and team_number > 0 and team_number.is_integer()) or \
       not (isinstance(match_number, (int, float)) and match_number > 0 and match_number.is_integer()):
        st.error("Form not submitted: Team number and match number must be positive integers.")
    else:
        # Save the data directly (no duplicate checks)
        success, doc_id = save_data(match_data)
        if success:
            st.success("Form submitted successfully!")
            # Add a delay to ensure the success message is visible
            time.sleep(2)  # Delay for 2 seconds
            st.session_state.form_data = {}
            st.rerun()
        else:
            st.error("Failed to save match data. Please check the form and try again.")