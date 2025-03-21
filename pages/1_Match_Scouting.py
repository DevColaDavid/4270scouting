# pages/1_Match_Scouting.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.utils import save_data

st.set_page_config(page_title="Match Scouting", page_icon="📝")

st.title("Match Scouting")
st.markdown("Enter match data for scouting. All fields are required unless specified.")

# Form for match scouting
with st.form(key="match_scouting_form"):
    # Team and Match Information
    st.subheader("Team and Match Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        team_number = st.number_input("Team Number", min_value=1, step=1)
    with col2:
        match_number = st.number_input("Match Number", min_value=1, step=1)
    with col3:
        alliance_color = st.selectbox("Alliance Color", options=["Red", "Blue"])

    scouter_name = st.text_input("Scouter Name")
    starting_position = st.selectbox("Starting Position", options=["Left", "Center", "Right"])

    # Auto Period
    st.subheader("Auto Period")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        auto_coral_l1 = st.number_input("Auto Coral L1", min_value=0, step=1)
    with col2:
        auto_coral_l2 = st.number_input("Auto Coral L2", min_value=0, step=1)
    with col3:
        auto_coral_l3 = st.number_input("Auto Coral L3", min_value=0, step=1)
    with col4:
        auto_coral_l4 = st.number_input("Auto Coral L4", min_value=0, step=1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        auto_missed_coral_l1 = st.number_input("Auto Missed Coral L1", min_value=0, step=1)
    with col2:
        auto_missed_coral_l2 = st.number_input("Auto Missed Coral L2", min_value=0, step=1)
    with col3:
        auto_missed_coral_l3 = st.number_input("Auto Missed Coral L3", min_value=0, step=1)
    with col4:
        auto_missed_coral_l4 = st.number_input("Auto Missed Coral L4", min_value=0, step=1)

    col1, col2, col3 = st.columns(3)
    with col1:
        auto_algae_barge = st.number_input("Auto Algae Barge", min_value=0, step=1)
    with col2:
        auto_algae_processor = st.number_input("Auto Algae Processor", min_value=0, step=1)
    with col3:
        auto_algae_removed = st.number_input("Auto Algae Removed", min_value=0, step=1)

    col1, col2 = st.columns(2)
    with col1:
        auto_missed_algae_barge = st.number_input("Auto Missed Algae Barge", min_value=0, step=1)
    with col2:
        auto_missed_algae_processor = st.number_input("Auto Missed Algae Processor", min_value=0, step=1)

    # Teleop Period
    st.subheader("Teleop Period")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        teleop_coral_l1 = st.number_input("Teleop Coral L1", min_value=0, step=1)
    with col2:
        teleop_coral_l2 = st.number_input("Teleop Coral L2", min_value=0, step=1)
    with col3:
        teleop_coral_l3 = st.number_input("Teleop Coral L3", min_value=0, step=1)
    with col4:
        teleop_coral_l4 = st.number_input("Teleop Coral L4", min_value=0, step=1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        teleop_missed_coral_l1 = st.number_input("Teleop Missed Coral L1", min_value=0, step=1)
    with col2:
        teleop_missed_coral_l2 = st.number_input("Teleop Missed Coral L2", min_value=0, step=1)
    with col3:
        teleop_missed_coral_l3 = st.number_input("Teleop Missed Coral L3", min_value=0, step=1)
    with col4:
        teleop_missed_coral_l4 = st.number_input("Teleop Missed Coral L4", min_value=0, step=1)

    col1, col2, col3 = st.columns(3)
    with col1:
        teleop_algae_barge = st.number_input("Teleop Algae Barge", min_value=0, step=1)
    with col2:
        teleop_algae_processor = st.number_input("Teleop Algae Processor", min_value=0, step=1)
    with col3:
        teleop_algae_removed = st.number_input("Teleop Algae Removed", min_value=0, step=1)

    col1, col2 = st.columns(2)
    with col1:
        teleop_missed_algae_barge = st.number_input("Teleop Missed Algae Barge", min_value=0, step=1)
    with col2:
        teleop_missed_algae_processor = st.number_input("Teleop Missed Algae Processor", min_value=0, step=1)

    # Endgame
    st.subheader("Endgame")
    climb_status = st.selectbox("Climb Status", options=["No Climb", "Shallow Climb", "Deep Climb"])

    # Ratings
    st.subheader("Ratings")
    col1, col2, col3 = st.columns(3)
    with col1:
        defense_rating = st.slider("Defense Rating", min_value=1.0, max_value=5.0, step=0.5)
    with col2:
        speed_rating = st.slider("Speed Rating", min_value=1.0, max_value=5.0, step=0.5)
    with col3:
        driver_skill_rating = st.slider("Driver Skill Rating", min_value=1.0, max_value=5.0, step=0.5)

    # Qualitative Assessments
    st.subheader("Qualitative Assessments")
    defense_qa = st.text_area("Defense QA", placeholder="Notes on defense performance")
    teleop_qa = st.text_area("Teleop QA", placeholder="Notes on teleop performance")
    auto_qa = st.text_area("Auto QA", placeholder="Notes on auto performance")
    comments = st.text_area("General Comments", placeholder="Additional comments")

    # Match Result
    match_result = st.selectbox("Match Result", options=["Win", "Loss", "Tie"])

    # Submit Button
    submitted = st.form_submit_button("Submit Match Data")

    if submitted:
        # Collect all data into a dictionary
        match_data = {
            "team_number": team_number,
            "match_number": match_number,
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
            "auto_missed_algae_barge": auto_missed_algae_barge,
            "auto_missed_algae_processor": auto_missed_algae_processor,
            "auto_algae_removed": auto_algae_removed,
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
            "teleop_missed_algae_barge": teleop_missed_algae_barge,
            "teleop_missed_algae_processor": teleop_missed_algae_processor,
            "teleop_algae_removed": teleop_algae_removed,
            "climb_status": climb_status,
            "defense_rating": defense_rating,
            "speed_rating": speed_rating,
            "driver_skill_rating": driver_skill_rating,
            "defense_qa": defense_qa,
            "teleop_qa": teleop_qa,
            "auto_qa": auto_qa,
            "comments": comments,
            "match_result": match_result,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Save the data (debug statements removed)
        if save_data(match_data):
            st.success("Match data submitted successfully!")
        else:
            st.error("Error saving match data.")