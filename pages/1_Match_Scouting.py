# pages/1_Match_Scout_Form.py
import streamlit as st
from utils.utils import save_data

# Set page layout to wide to utilize more screen width
st.set_page_config(page_title="Match Scout Form", page_icon="📝", layout="wide")

# Custom CSS to adjust spacing and fill the width
st.markdown("""
    <style>
    /* Adjust the overall page padding to reduce side empty space */
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Adjust the form container to fill the width */
    .stForm {
        width: 100% !important;
        padding: 1rem !important;  /* Add padding inside the form */
    }

    /* Adjust spacing between columns */
    .st-emotion-cache-1wmy9hl {
        gap: 1.5rem !important;  /* Increase gap between columns */
    }

    /* Adjust spacing between form sections */
    .stMarkdown, .stTextInput, .stNumberInput, .stSelectbox, .stSlider, .stTextArea, .stCheckbox {
        margin-bottom: 1rem !important;  /* Add vertical spacing between elements */
    }

    /* Ensure the form elements are responsive */
    @media (max-width: 768px) {
        .st-emotion-cache-1wmy9hl {
            gap: 0.5rem !important;  /* Reduce gap on smaller screens */
        }
        .stForm {
            padding: 0.5rem !important;
        }
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.title("Match Scout Form")

# Use session state to manage form key for resetting
if 'form_key' not in st.session_state:
    st.session_state.form_key = "match_scout_form_0"

# Form for match scouting
with st.form(key=st.session_state.form_key):
    # Match Information
    st.subheader("Match Information")
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        team_number = st.number_input("Team Number", min_value=0, step=1)
    with col2:
        match_number = st.number_input("Match Number", min_value=0, step=1)
    with col3:
        alliance_color = st.selectbox("Alliance Color", options=["Red", "Blue"])

    col1, col2 = st.columns([2, 1], gap="medium")  # Adjusted ratio to stretch Scouter Name
    with col1:
        scouter_name = st.text_input("Scouter Name")
    with col2:
        starting_position = st.selectbox("Starting Position", options=["Left", "Middle", "Right"])

    # Autonomous Period
    st.subheader("Autonomous Period")
    auto_taxi_left = st.checkbox("Robot Left Starting Position (Taxi)", value=False)

    st.markdown("#### Coral Scored in Autonomous")
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        auto_coral_l1 = st.number_input("Level 1 Coral", min_value=0, step=1, key="auto_coral_l1")
    with col2:
        auto_coral_l2 = st.number_input("Level 2 Coral", min_value=0, step=1, key="auto_coral_l2")
    with col3:
        auto_coral_l3 = st.number_input("Level 3 Coral", min_value=0, step=1, key="auto_coral_l3")
    with col4:
        auto_coral_l4 = st.number_input("Level 4 Coral", min_value=0, step=1, key="auto_coral_l4")

    st.markdown("#### Coral Missed in Autonomous")
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        auto_missed_coral_l1 = st.number_input("Missed Level 1 Coral", min_value=0, step=1, key="auto_missed_coral_l1")
    with col2:
        auto_missed_coral_l2 = st.number_input("Missed Level 2 Coral", min_value=0, step=1, key="auto_missed_coral_l2")
    with col3:
        auto_missed_coral_l3 = st.number_input("Missed Level 3 Coral", min_value=0, step=1, key="auto_missed_coral_l3")
    with col4:
        auto_missed_coral_l4 = st.number_input("Missed Level 4 Coral", min_value=0, step=1, key="auto_missed_coral_l4")

    st.markdown("#### Algae Management in Autonomous")
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        auto_algae_barge = st.number_input("Algae to Barge", min_value=0, step=1, key="auto_algae_barge")
        auto_missed_algae_barge = st.number_input("Missed Algae to Barge", min_value=0, step=1, key="auto_missed_algae_barge")
    with col2:
        auto_algae_processor = st.number_input("Algae to Processor", min_value=0, step=1, key="auto_algae_processor")
        auto_missed_algae_processor = st.number_input("Missed Algae to Processor", min_value=0, step=1, key="auto_missed_algae_processor")
    with col3:
        auto_algae_removed = st.number_input("Algae Removed", min_value=0, step=1, key="auto_algae_removed")

    auto_qa = st.text_area("Autonomous Qualitative Assessment", placeholder="Describe autonomous performance...")

    # Teleop Period
    st.subheader("Teleop Period")
    st.markdown("#### Coral Scored in Teleop")
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        teleop_coral_l1 = st.number_input("Level 1 Coral", min_value=0, step=1, key="teleop_coral_l1")
    with col2:
        teleop_coral_l2 = st.number_input("Level 2 Coral", min_value=0, step=1, key="teleop_coral_l2")
    with col3:
        teleop_coral_l3 = st.number_input("Level 3 Coral", min_value=0, step=1, key="teleop_coral_l3")  # Fixed label from "Level 1 Coral" to "Level 3 Coral"
    with col4:
        teleop_coral_l4 = st.number_input("Level 4 Coral", min_value=0, step=1, key="teleop_coral_l4")

    st.markdown("#### Coral Missed in Teleop")
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        teleop_missed_coral_l1 = st.number_input("Missed Level 1 Coral", min_value=0, step=1, key="teleop_missed_coral_l1")
    with col2:
        teleop_missed_coral_l2 = st.number_input("Missed Level 2 Coral", min_value=0, step=1, key="teleop_missed_coral_l2")
    with col3:
        teleop_missed_coral_l3 = st.number_input("Missed Level 3 Coral", min_value=0, step=1, key="teleop_missed_coral_l3")
    with col4:
        teleop_missed_coral_l4 = st.number_input("Missed Level 4 Coral", min_value=0, step=1, key="teleop_missed_coral_l4")

    st.markdown("#### Algae Management in Teleop")
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        teleop_algae_barge = st.number_input("Algae to Barge", min_value=0, step=1, key="teleop_algae_barge")
        teleop_missed_algae_barge = st.number_input("Missed Algae to Barge", min_value=0, step=1, key="teleop_missed_algae_barge")
    with col2:
        teleop_algae_processor = st.number_input("Algae to Processor", min_value=0, step=1, key="teleop_algae_processor")
        teleop_missed_algae_processor = st.number_input("Missed Algae to Processor", min_value=0, step=1, key="teleop_missed_algae_processor")
    with col3:
        teleop_algae_removed = st.number_input("Algae Removed", min_value=0, step=1, key="teleop_algae_removed")

    teleop_qa = st.text_area("Teleop Qualitative Assessment", placeholder="Describe teleop performance...")

    # Endgame
    st.subheader("Endgame")
    climb_status = st.selectbox("Climb Status", options=["No Climb", "Parked", "Shallow Climb", "Deep Climb"])

    # Performance Ratings
    st.subheader("Performance Ratings")
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        defense_rating = st.slider("Defense Rating", 0.0, 5.0, 0.0, 0.1)
    with col2:
        speed_rating = st.slider("Speed Rating", 0.0, 5.0, 0.0, 0.1)
    with col3:
        driver_skill_rating = st.slider("Driver Skill Rating", 0.0, 5.0, 0.0, 0.1)

    defense_qa = st.text_area("Defense Qualitative Assessment", placeholder="Describe defense performance...")

    # Additional Information
    st.subheader("Additional Information")
    col1, col2 = st.columns([1, 1], gap="medium")
    with col1:
        match_result = st.selectbox("Match Result", options=["Win", "Loss", "Tie"])
    with col2:
        # Add an empty column to maintain spacing
        st.empty()

    comments = st.text_area("Additional Comments", placeholder="Any other observations...")

    # Submit and Clear Buttons
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        submit_button = st.form_submit_button(label="Submit Match Data")
    with col2:
        clear_button = st.form_submit_button(label="Clear All")

    if submit_button:
        # Validate required fields
        if not team_number or not match_number:
            st.error("Team Number and Match Number are required.")
        elif not scouter_name:
            st.error("Scouter Name is required.")
        else:
            # Prepare match data
            match_data = {
                "team_number": int(team_number),
                "match_number": int(match_number),
                "alliance_color": alliance_color,
                "scouter_name": scouter_name,
                "starting_position": starting_position,
                "auto_taxi_left": auto_taxi_left,
                "auto_coral_l1": int(auto_coral_l1),
                "auto_coral_l2": int(auto_coral_l2),
                "auto_coral_l3": int(auto_coral_l3),
                "auto_coral_l4": int(auto_coral_l4),
                "auto_missed_coral_l1": int(auto_missed_coral_l1),
                "auto_missed_coral_l2": int(auto_missed_coral_l2),
                "auto_missed_coral_l3": int(auto_missed_coral_l3),
                "auto_missed_coral_l4": int(auto_missed_coral_l4),
                "auto_algae_barge": int(auto_algae_barge),
                "auto_algae_processor": int(auto_algae_processor),
                "auto_missed_algae_barge": int(auto_missed_algae_barge),
                "auto_missed_algae_processor": int(auto_missed_algae_processor),
                "auto_algae_removed": int(auto_algae_removed),
                "auto_qa": auto_qa,
                "teleop_coral_l1": int(teleop_coral_l1),
                "teleop_coral_l2": int(teleop_coral_l2),
                "teleop_coral_l3": int(teleop_coral_l3),
                "teleop_coral_l4": int(teleop_coral_l4),
                "teleop_missed_coral_l1": int(teleop_missed_coral_l1),
                "teleop_missed_coral_l2": int(teleop_missed_coral_l2),
                "teleop_missed_coral_l3": int(teleop_missed_coral_l3),
                "teleop_missed_coral_l4": int(teleop_missed_coral_l4),
                "teleop_algae_barge": int(teleop_algae_barge),
                "teleop_algae_processor": int(teleop_algae_processor),
                "teleop_missed_algae_barge": int(teleop_missed_algae_barge),
                "teleop_missed_algae_processor": int(teleop_missed_algae_processor),
                "teleop_algae_removed": int(teleop_algae_removed),
                "teleop_qa": teleop_qa,
                "climb_status": climb_status,
                "defense_rating": float(defense_rating),
                "speed_rating": float(speed_rating),
                "driver_skill_rating": float(driver_skill_rating),
                "defense_qa": defense_qa,
                "match_result": match_result,
                "comments": comments
            }

            # Save the data
            success, message = save_data(match_data)
            if success:
                st.success(f"Match data submitted successfully! Document ID: {message}")
                st.balloons()  # Trigger balloon animation on successful submission
                # Reset the form by changing the form key
                st.session_state.form_key = f"match_scout_form_{int(st.session_state.form_key.split('_')[-1]) + 1}"
            else:
                st.error(f"Failed to submit match data: {message}")

    if clear_button:
        # Reset the form by changing the form key
        st.session_state.form_key = f"match_scout_form_{int(st.session_state.form_key.split('_')[-1]) + 1}"
        st.rerun()  # Force a rerun to reset the form