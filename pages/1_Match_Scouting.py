# pages/1_Match_Scouting.py
import streamlit as st
import pandas as pd
from utils.utils import load_data, save_data, validate_team_number, validate_match_number
from utils.form_config import MATCH_INFO, AUTONOMOUS, TELEOP, ENDGAME, PERFORMANCE_RATINGS, ANALYSIS

# Page configuration
st.title("Match Scouting Form")

# Optimized form field renderer
def render_form_field(field, prefix):
    key = f"{prefix}_{field['name']}"
    field_types = {
        'number': lambda: st.number_input(field['label'], min_value=0, value=0, step=1, key=key),
        'text': lambda: st.text_input(field['label'], key=key),
        'boolean': lambda: st.checkbox(field['label'], key=key),
        'select': lambda: st.selectbox(field['label'], field['options'], key=key),
        'radio': lambda: st.radio(field['label'], field['options'], horizontal=True, key=key),
        'checkbox': lambda: st.checkbox(field['label'], key=key),
        'slider': lambda: st.slider(field['label'], field['min'], field['max'], (field['max'] + field['min']) // 2, key=key),
        'textarea': lambda: st.text_area(field['label'], help=field.get('help', ''), key=key),
    }
    return field_types.get(field['type'], lambda: None)()

# Helper function to render sections
def render_section(section_title, fields, prefix, columns=2, expander=True):
    if expander:
        with st.expander(section_title, expanded=True):
            cols = st.columns(columns)
            for i, field in enumerate(fields):
                with cols[i % columns]:
                    form_data[field['name']] = render_form_field(field, prefix)
    else:
        st.markdown(f"#### {section_title}")
        cols = st.columns(columns)
        for i, field in enumerate(fields):
            with cols[i % columns]:
                form_data[field['name']] = render_form_field(field, prefix)

# Clear Streamlit cache to reset expander states
st.cache_data.clear()

# Initialize session state for feedback and duplicate handling
if "submit_status" not in st.session_state:
    st.session_state.submit_status = None
if "duplicate_data" not in st.session_state:
    st.session_state.duplicate_data = None
if "form_data" not in st.session_state:
    st.session_state.form_data = None

# Instructions (collapsed by default)
with st.expander("Instructions"):
    st.write("""
    - **Team Number**: Enter the competing team's number (e.g., 1234).
    - **Match Number**: Enter the match number (e.g., 1-150).
    - **Match Result**: Select the outcome of the match for this team's alliance (Win, Loss, or Tie) at the end of the form.
    - Fill out all sections based on the robot's performance during the match.
    - Use the 'Analysis' section for qualitative observations.
    """)

# Form
form_data = {}
with st.form("scouting_form"):
    # Match Information (expanded by default)
    with st.expander("Match Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            form_data['team_number'] = render_form_field(MATCH_INFO['basic_info'][0], 'match_info')
            form_data['match_number'] = render_form_field(MATCH_INFO['basic_info'][1], 'match_info')
        with col2:
            form_data['alliance_color'] = render_form_field(MATCH_INFO['basic_info'][2], 'match_info')
            form_data['scouter_name'] = render_form_field(MATCH_INFO['basic_info'][3], 'match_info')
        form_data['starting_position'] = render_form_field(MATCH_INFO['starting_position'], 'match_info')

    # Autonomous (expanded by default)
    with st.expander("Autonomous", expanded=True):
        render_section("Coral Scored", AUTONOMOUS['scoring'], 'auto', expander=False)
        render_section("Coral Missed", AUTONOMOUS['missed_attempts'], 'auto', expander=False)
        render_section("Algae Management", AUTONOMOUS['algae_management'], 'auto', expander=False)

    # Teleop (expanded by default)
    with st.expander("Teleop", expanded=True):
        render_section("Coral Scored", TELEOP['scoring'], 'teleop', expander=False)
        render_section("Coral Missed", TELEOP['missed_attempts'], 'teleop', expander=False)
        render_section("Algae Management", TELEOP['algae_management'], 'teleop', expander=False)

    # Endgame (expanded by default)
    with st.expander("Endgame", expanded=True):
        form_data['climb_status'] = render_form_field(ENDGAME['climb_status'], 'endgame')

    # Performance Ratings (expanded by default)
    with st.expander("Performance Ratings", expanded=True):
        cols = st.columns(3)
        for i, field in enumerate(PERFORMANCE_RATINGS['ratings']):
            with cols[i]:
                form_data[field['name']] = render_form_field(field, 'performance')

    # Analysis (expanded by default)
    with st.expander("Analysis", expanded=True):
        for field in ANALYSIS['questions']:
            form_data[field['name']] = render_form_field(field, 'analysis')

    # Match Result (added at the bottom)
    st.markdown("#### Match Result")
    form_data['match_result'] = st.selectbox("Match Result", ['Win', 'Loss', 'Tie'], key='match_result')

    # Submit and Reset Buttons
    col_submit, col_reset = st.columns(2)
    with col_submit:
        submitted = st.form_submit_button("Submit Match Data")
    with col_reset:
        reset = st.form_submit_button("Reset Form")

    # Form Submission Logic (Inside Form)
    if submitted:
        team_valid = validate_team_number(form_data['team_number'])
        match_valid = validate_match_number(form_data['match_number'])

        if team_valid and match_valid:
            form_data['team_number'] = int(form_data['team_number'])
            form_data['match_number'] = int(form_data['match_number'])
            form_data['timestamp'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            new_data = pd.DataFrame([form_data])
            existing_data = load_data()

            # Check for duplicates
            if not existing_data.empty:
                duplicate = existing_data[
                    (existing_data['team_number'] == form_data['team_number']) &
                    (existing_data['match_number'] == form_data['match_number'])
                ]
                if not duplicate.empty:
                    st.session_state.duplicate_data = duplicate
                    st.session_state.form_data = form_data
                    st.session_state.submit_status = "duplicate"
                else:
                    combined_data = pd.concat([existing_data, new_data], ignore_index=True) if not existing_data.empty else new_data
                    if save_data(combined_data):
                        st.session_state.submit_status = "success"
                    else:
                        st.session_state.submit_status = "error"
            else:
                if save_data(new_data):
                    st.session_state.submit_status = "success"
                else:
                    st.session_state.submit_status = "error"
        else:
            if not team_valid:
                st.warning("Team number must be a positive integer.")
            if not match_valid:
                st.warning("Match number must be between 1 and 150.")

    if reset:
        st.session_state.duplicate_data = None
        st.session_state.form_data = None
        st.experimental_rerun()

# Handle Duplicate Logic (Outside Form)
if st.session_state.submit_status == "duplicate" and st.session_state.duplicate_data is not None:
    st.warning("Data for this team and match already exists!")
    st.dataframe(st.session_state.duplicate_data)
    if st.button("Overwrite Existing Data"):
        existing_data = load_data()
        form_data = st.session_state.form_data
        new_data = pd.DataFrame([form_data])
        existing_data = existing_data[
            (existing_data['team_number'] != form_data['team_number']) |
            (existing_data['match_number'] != form_data['match_number'])
        ]
        combined_data = pd.concat([existing_data, new_data], ignore_index=True)
        if save_data(combined_data):
            st.session_state.submit_status = "success"
        else:
            st.session_state.submit_status = "error"
        st.session_state.duplicate_data = None
        st.session_state.form_data = None

# Display Feedback
if st.session_state.submit_status == "success":
    st.success("Match data saved successfully!")
    st.balloons()
    st.session_state.submit_status = None
elif st.session_state.submit_status == "error":
    st.error("Error saving match data.")
    st.session_state.submit_status = None

# Display Existing Data and Stats
df = load_data()
if df is not None and not df.empty:
    st.subheader("Recent Matches")
    st.dataframe(df.tail())

    st.subheader("Quick Stats")
    st.write(f"Total Responses Submitted: {len(df)}")
    if 'match_number' in df.columns:
        st.write(f"Total Unique Matches: {df['match_number'].nunique()}")
    else:
        st.write("Total Unique Matches: N/A (No match number data available)")
    if 'auto_coral_l1' in df.columns:
        st.write(f"Average Auto Coral Scored on L1: {df['auto_coral_l1'].mean():.2f}")
    else:
        st.write("Average Auto Coral Scored on L1: N/A (No data available)")
    if 'teleop_coral_l1' in df.columns:
        st.write(f"Average Teleop Coral Scored on L1: {df['teleop_coral_l1'].mean():.2f}")
    else:
        st.write("Average Teleop Coral Scored on L1: N/A (No data available)")

    csv = df.to_csv(index=False)
    st.download_button(
        label="Download All Data as CSV",
        data=csv,
        file_name=f"match_scouting_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )
else:
    st.info("No match data available yet. Submit some data to see statistics.")