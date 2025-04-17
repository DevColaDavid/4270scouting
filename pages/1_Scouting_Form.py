# pages/1_Scouting_Form.py
import streamlit as st
import pandas as pd
from utils.form_config import MATCH_INFO, AUTONOMOUS, TELEOP, ENDGAME, PERFORMANCE_RATINGS, ANALYSIS, MATCH_OUTCOME, STRATEGY
from utils.form_config import PIT_INFO, ROBOT_SPECIFICATIONS, CAPABILITIES, PIT_STRATEGY, PIT_NOTES
from utils.utils import save_data, setup_sidebar_navigation, upload_photo_to_storage, get_firebase_instances

# Set page configuration
st.set_page_config(
    page_title="Scouting Form",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Firebase
try:
    db, bucket = get_firebase_instances()
    st.session_state.firebase_db = db
    st.session_state.firebase_bucket = bucket
except Exception as e:
    st.error(f"Failed to initialize Firebase: {str(e)}")
    st.stop()

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in to access this page.")
    st.stop()

# Set up the sidebar navigation
setup_sidebar_navigation()

# Check user authority
allowed_authorities = ["Scouter", "Admin", "Owner","Alliance"]
if st.session_state.get("authority") not in allowed_authorities:
    st.error("You do not have the required authority to access this page. Required: Scouter, Admin, or Owner.")
    st.stop()

# Custom CSS for button styling (shared for both tabs)
st.markdown("""
    <style>
    .stNumberInput, .stTextInput, .stSelectbox, .stCheckbox, .stSlider, .stTextArea {
        margin-bottom: 15px;
    }
    /* Style for the Submit buttons */
    button[kind="primary"][key="match_submit_button"],
    button[kind="primary"][key="pit_submit_button"] {
        background-color: #007BFF; /* Blue */
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
    }
    button[kind="primary"][key="match_submit_button"]:hover,
    button[kind="primary"][key="pit_submit_button"]:hover {
        background-color: #0056b3; /* Darker blue on hover */
    }
    /* Style for the Clear Form buttons */
    button[kind="primary"][key="match_clear_button"],
    button[kind="primary"][key="pit_clear_button"] {
        background-color: #DC3545; /* Red */
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
    }
    button[kind="primary"][key="match_clear_button"]:hover,
    button[kind="primary"][key="pit_clear_button"]:hover {
        background-color: #b02a37; /* Darker red on hover */
    }
    </style>
""", unsafe_allow_html=True)

# Page content
st.title("📝 Scouting Form")
st.markdown("Use the tabs below to submit Match Scouting or Pit Scouting data.")

# Create tabs for Match Scouting and Pit Scouting
match_tab, pit_tab = st.tabs(["Match Scouting", "Pit Scouting"])

# --- Match Scouting Tab ---
with match_tab:
    st.markdown("Fill out the form below to scout a match.")

    # Initialize session state for Match Scouting form
    if 'match_form_data' not in st.session_state:
        st.session_state.match_form_data = {}
    if 'match_form_cleared' not in st.session_state:
        st.session_state.match_form_cleared = False

    # Function to get the current value of a field, considering form clearing
    def get_match_field_value(name, default_value):
        if st.session_state.match_form_cleared:
            if name in ["scouter_name", "alliance_color"]:
                return st.session_state.match_form_data.get(name, default_value)
            if name in ["team_number", "match_number", "starting_position", "match_outcome", "primary_role"]:
                return None
            return default_value
        if name in ["team_number", "match_number", "alliance_color", "starting_position", "match_outcome", "primary_role"] and name not in st.session_state.match_form_data:
            return None
        return st.session_state.match_form_data.get(name, default_value)

    # Callback function to update session state
    def update_match_number_input(name):
        st.session_state.match_form_data[name] = st.session_state[f'match_{name}']

    # Form data dictionary
    match_form_data = {}

    # Add custom CSS for responsiveness and compact layout
    st.markdown("""
        <style>
        .stNumberInput, .stTextInput, .stSelectbox, .stCheckbox, .stSlider, .stTextArea {
            margin-bottom: 5px; /* Reduce spacing for compactness */
        }
        .st-expander {
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        /* Responsive columns: stack on small screens */
        @media (max-width: 600px) {
            div[data-testid="column"] {
                width: 100% !important;
                display: block;
            }
            div[data-testid="column"] > div {
                margin-bottom: 10px;
            }
        }
        /* Reduce input field width */
        .stNumberInput > div > div > input {
            width: 80px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Match Info Section (not in expander, foundational info)
    st.markdown('<div style="color: #007BFF; font-size: 24px; font-weight: bold; margin-bottom: 10px">Match Information</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        for item in MATCH_INFO['basic_info'][:2]:  # Team Number, Match Number
            name = item['name']
            match_form_data[name] = st.number_input(
                item["label"],
                min_value=1,
                step=1,
                key=f"match_{name}",
                value=get_match_field_value(name, None),
                on_change=update_match_number_input,
                args=(name,)
            )
    with col2:
        for item in MATCH_INFO['basic_info'][2:3]:  # Alliance Color
            name = item['name']
            options = item['options']
            current_value = get_match_field_value(name, None)
            display_options = [None] + options
            def format_option(value):
                if value is None:
                    return "Choose an option"
                return value
            index = 0 if current_value is None else options.index(current_value) + 1
            match_form_data[name] = st.selectbox(
                item["label"],
                options=display_options,
                index=index,
                key=f"match_{name}",
                format_func=format_option
            ) if current_value is not None else st.selectbox(
                item["label"],
                options=display_options,
                index=0,
                key=f"match_{name}",
                format_func=format_option
            )
        item = MATCH_INFO['starting_position']
        name = item['name']
        options = item['options']
        current_value = get_match_field_value(name, None)
        display_options = [None] + options
        index = 0 if current_value is None else options.index(current_value) + 1
        match_form_data[name] = st.selectbox(
            item["label"],
            options=display_options,
            index=index,
            key=f"match_{name}",
            format_func=format_option
        ) if current_value is not None else st.selectbox(
            item["label"],
            options=display_options,
            index=0,
            key=f"match_{name}",
            format_func=format_option
        )
    with col3:
        for item in MATCH_INFO['basic_info'][3:4]:  # Scouter Name
            name = item['name']
            match_form_data[name] = st.text_input(
                item["label"],
                key=f"match_{name}",
                value=get_match_field_value(name, "")
            )

    # Autonomous Section
    with st.expander("Autonomous Period", expanded=True):
        st.markdown('<div style="color: #28A745; font-size: 20px; font-weight: bold;">Autonomous</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            st.markdown("**Mobility**")
            for mobility_item in AUTONOMOUS['mobility']:
                name = mobility_item['name']
                match_form_data[name] = st.checkbox(
                    mobility_item["label"],
                    key=f"match_{name}",
                    value=get_match_field_value(name, False)
                )
        with col2:
            st.markdown("**Coral Scored**")
            for scoring_item in AUTONOMOUS['scoring']:
                name = scoring_item['name']
                match_form_data[name] = st.number_input(
                    scoring_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col3:
            st.markdown("**Coral Missed**")
            for missed_item in AUTONOMOUS['missed_attempts']:
                name = missed_item['name']
                match_form_data[name] = st.number_input(
                    missed_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            st.markdown("**Algae Scored**")
            for algae_item in AUTONOMOUS['algae_management'][:2]:
                name = algae_item['name']
                match_form_data[name] = st.number_input(
                    algae_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col2:
            st.markdown("**Algae Missed**")
            for algae_item in AUTONOMOUS['algae_management'][2:4]:
                name = algae_item['name']
                match_form_data[name] = st.number_input(
                    algae_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col3:
            st.markdown("**Algae Removed**")
            for algae_item in AUTONOMOUS['algae_management'][4:5]:
                name = algae_item['name']
                match_form_data[name] = st.number_input(
                    algae_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col4:
            pass

    # Teleop Section
    with st.expander("Teleop Period", expanded=True):
        st.markdown('<div style="color: #FD7E14; font-size: 20px; font-weight: bold;">Teleop</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Coral Scored**")
            for scoring_item in TELEOP['scoring']:
                name = scoring_item['name']
                match_form_data[name] = st.number_input(
                    scoring_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col2:
            st.markdown("**Coral Missed**")
            for missed_item in TELEOP['missed_attempts']:
                name = missed_item['name']
                match_form_data[name] = st.number_input(
                    missed_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            st.markdown("**Algae Scored**")
            for algae_item in TELEOP['algae_management'][:2]:
                name = algae_item['name']
                match_form_data[name] = st.number_input(
                    algae_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col2:
            st.markdown("**Algae Missed**")
            for algae_item in TELEOP['algae_management'][2:4]:
                name = algae_item['name']
                match_form_data[name] = st.number_input(
                    algae_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col3:
            st.markdown("**Algae Removed**")
            for algae_item in TELEOP['algae_management'][4:5]:
                name = algae_item['name']
                match_form_data[name] = st.number_input(
                    algae_item["label"],
                    min_value=0,
                    value=get_match_field_value(name, 0),
                    step=1,
                    key=f"match_{name}",
                    on_change=update_match_number_input,
                    args=(name,)
                )
        with col4:
            pass

    # Endgame Section
    with st.expander("Endgame", expanded=True):
        st.markdown('<div style="color: #6F42C1; font-size: 20px; font-weight: bold;">Endgame</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 3])
        with col1:
            item = ENDGAME['climb_status']
            name = item['name']
            options = item['options']
            default_index = 0
            current_value = get_match_field_value(name, options[default_index])
            if current_value not in options:
                current_value = options[default_index]
            match_form_data[name] = st.selectbox(
                item["label"],
                options=options,
                index=options.index(current_value),
                key=f"match_{name}"
            )
        with col2:
            pass

    # Performance Ratings Section
    with st.expander("Performance Ratings", expanded=True):
        st.markdown('<div style="color: #20C997; font-size: 20px; font-weight: bold;">Performance Ratings</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        for idx, rating_item in enumerate(PERFORMANCE_RATINGS['ratings']):
            with [col1, col2, col3][idx % 3]:
                name = rating_item['name']
                match_form_data[name] = st.slider(
                    rating_item["label"],
                    min_value=rating_item['min'],
                    max_value=rating_item['max'],
                    value=get_match_field_value(name, 3),
                    step=1,
                    key=f"match_{name}"
                )

    # Strategy Section
    with st.expander("Strategy", expanded=True):
        st.markdown('<div style="color: #6610F2; font-size: 20px; font-weight: bold;">Strategy</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 3])
        with col1:
            item = STRATEGY['primary_role']
            name = item['name']
            options = item['options']
            current_value = get_match_field_value(name, None)
            display_options = [None] + options
            def format_option(value):
                if value is None:
                    return "Choose an option"
                return value
            if current_value is None:
                index = 0
            else:
                index = options.index(current_value) + 1
            selected_value = st.selectbox(
                item["label"],
                options=display_options,
                index=index,
                key=f"match_{name}",
                format_func=format_option,
                help=item.get('help', '')
            )
            match_form_data[name] = selected_value if selected_value is not None else None
        with col2:
            pass

    # Qualitative Analysis Section
    with st.expander("Qualitative Analysis", expanded=True):
        st.markdown('<div style="color: #17A2B8; font-size: 20px; font-weight: bold;">Qualitative Analysis</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        for idx, question_item in enumerate(ANALYSIS['questions']):
            with [col1, col2][idx % 2]:
                name = question_item['name']
                match_form_data[name] = st.text_area(
                    question_item["label"],
                    help=question_item.get('help', ''),
                    key=f"match_{name}",
                    value=get_match_field_value(name, ""),
                    height=100  # Fixed height to keep it compact
                )

    # Match Outcome Section
    with st.expander("Match Outcome", expanded=True):
        st.markdown('<div style="color: #DC3545; font-size: 20px; font-weight: bold;">Match Outcome</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 3])
        with col1:
            item = MATCH_OUTCOME['outcome']
            name = item['name']
            options = item['options']
            current_value = get_match_field_value(name, None)
            display_options = [None] + options
            def format_option(value):
                if value is None:
                    return "Choose an option"
                return value
            if current_value is None:
                index = 0
            else:
                index = options.index(current_value) + 1
            selected_value = st.selectbox(
                item["label"],
                options=display_options,
                index=index,
                key=f"match_{name}",
                format_func=format_option,
                help=item.get('help', '')
            )
            match_form_data[name] = selected_value if selected_value is not None else None
        with col2:
            pass

    # Submit and Clear buttons
    col1, col2 = st.columns(2)
    with col1:
        match_submit_button = st.button(label="Submit Match Data", key="match_submit_button")
    with col2:
        match_clear_button = st.button(label="Clear Form", key="match_clear_button")

    # Update session state
    st.session_state.match_form_data = match_form_data

    # Handle form submission
    if match_submit_button:
        if not match_form_data.get("team_number") or match_form_data["team_number"] <= 0:
            st.error("Please enter a valid team number (must be greater than 0).")
        elif not match_form_data.get("match_number") or match_form_data["match_number"] <= 0:
            st.error("Please enter a valid match number (must be greater than 0).")
        elif not match_form_data.get("scouter_name"):
            st.error("Please enter the scouter's name (cannot be empty).")
        elif not match_form_data.get("alliance_color"):
            st.error("Please select an alliance color (Red or Blue).")
        elif not match_form_data.get("starting_position"):
            st.error("Please select a starting position.")
        elif not match_form_data.get("match_outcome"):
            st.error("Please select the match outcome (Win, Loss, or Tie).")
        elif not match_form_data.get("primary_role"):
            st.error("Please select the team's primary role.")
        else:
            numeric_fields = [
                "team_number", "match_number",
                "auto_coral_l1", "auto_coral_l2", "auto_coral_l3", "auto_coral_l4",
                "auto_missed_coral_l1", "auto_missed_coral_l2", "auto_missed_coral_l3", "auto_missed_coral_l4",
                "auto_algae_barge", "auto_algae_processor", "auto_missed_algae_barge", "auto_missed_algae_processor",
                "auto_algae_removed",
                "teleop_coral_l1", "teleop_coral_l2", "teleop_coral_l3", "teleop_coral_l4",
                "teleop_missed_coral_l1", "teleop_missed_coral_l2", "teleop_missed_coral_l3", "teleop_missed_coral_l4",
                "teleop_algae_barge", "teleop_algae_processor", "teleop_missed_algae_barge", "teleop_missed_algae_processor",
                "teleop_algae_removed",
                "defense_rating", "speed_rating", "driver_skill_rating"
            ]
            for field in numeric_fields:
                if field in match_form_data and match_form_data[field] is not None:
                    match_form_data[field] = int(match_form_data[field])

            success, result = save_data("match_scout_data", match_form_data)
            if success:
                doc_id = result
                st.success(f"Match data submitted successfully! Document ID: {doc_id}")
                st.balloons()
                preserved_data = {
                    "scouter_name": match_form_data.get("scouter_name", ""),
                    "alliance_color": match_form_data.get("alliance_color", None)
                }
                st.session_state.match_form_data = preserved_data
                st.session_state.match_form_cleared = True
            else:
                st.error(f"Failed to submit match data: {result}")
    if match_clear_button:
        preserved_data = {
            "scouter_name": st.session_state.match_form_data.get("scouter_name", ""),
            "alliance_color": st.session_state.match_form_data.get("alliance_color", None)
        }
        st.session_state.match_form_data = preserved_data
        st.session_state.match_form_cleared = True

    if st.session_state.match_form_cleared and not match_submit_button and not match_clear_button:
        st.session_state.match_form_cleared = False

# --- Pit Scouting Tab ---
with pit_tab:
    st.markdown("Fill out the form below to scout a team in the pit.")

    # Initialize session state for Pit Scouting form
    if 'pit_form_data' not in st.session_state:
        st.session_state.pit_form_data = {}
    if 'pit_form_cleared' not in st.session_state:
        st.session_state.pit_form_cleared = False

    # Function to get the current value of a field, considering form clearing
    def get_pit_field_value(name, default_value):
        if st.session_state.pit_form_cleared:
            if name == "scouter_name":
                return st.session_state.pit_form_data.get(name, default_value)
            if name in ["team_number", "drivetrain_type", "endgame_capability", "preferred_role", 
                        "programming_language", "coral_pickup_method", "algae_pickup_method"]:
                return None
            return default_value
        if name in ["team_number", "drivetrain_type", "endgame_capability", "preferred_role", 
                    "programming_language", "coral_pickup_method", "algae_pickup_method"] and name not in st.session_state.pit_form_data:
            return None
        return st.session_state.pit_form_data.get(name, default_value)

    # Callback function to update session state when a number input changes
    def update_pit_number_input(name):
        st.session_state.pit_form_data[name] = st.session_state[f'pit_{name}']

    # Form data dictionary for Pit Scouting
    pit_form_data = {}

    # Team Information Section (Blue: #007BFF)
    st.markdown('<div style="color: #007BFF; font-size: 24px; font-weight: bold; margin-bottom: 10px">Team Information</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        for item in PIT_INFO['basic_info'][:1]:  # Team Number
            name = item['name']
            pit_form_data[name] = st.number_input(
                item["label"],
                min_value=1,
                step=1,
                key=f"pit_{name}",
                value=get_pit_field_value(name, None),
                on_change=update_pit_number_input,
                args=(name,)
            )
    with col2:
        for item in PIT_INFO['basic_info'][1:2]:  # Scouter Name
            name = item['name']
            pit_form_data[name] = st.text_input(
                item["label"],
                key=f"pit_{name}",
                value=get_pit_field_value(name, "")
            )
    with col3:
        pass  # Empty column for spacing

    # Horizontal line after Team Information (Blue: #007BFF)
    st.markdown('<hr style="border-top: 5px solid #007BFF; margin: 20px 0;">', unsafe_allow_html=True)

    # Robot Specifications Section (Green: #28A745)
    st.markdown('<div style="color: #28A745; font-size: 24px; font-weight: bold; margin-bottom: 10px">Robot Specifications</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        # Drivetrain
        item = ROBOT_SPECIFICATIONS['drivetrain']
        name = item['name']
        options = item['options']
        current_value = get_pit_field_value(name, None)
        display_options = [None] + options
        def format_option(value):
            if value is None:
                return "Choose an option"
            return value
        if current_value is None:
            index = 0
        else:
            index = options.index(current_value) + 1
        selected_value = st.selectbox(
            item["label"],
            options=display_options,
            index=index,
            key=f"pit_{name}",
            format_func=format_option
        )
        pit_form_data[name] = selected_value if selected_value is not None else None
    with col2:
        # Programming Language (New Question)
        name = "programming_language"
        options = ["Java", "C++", "Python", "Other"]
        current_value = get_pit_field_value(name, None)
        display_options = [None] + options
        if current_value is None:
            index = 0
        else:
            index = options.index(current_value) + 1
        selected_value = st.selectbox(
            "Programming Language",
            options=display_options,
            index=index,
            key=f"pit_{name}",
            format_func=format_option
        )
        pit_form_data[name] = selected_value if selected_value is not None else None
    with col3:
        pass  # Empty column for spacing

    # Horizontal line after Robot Specifications (Green: #28A745)
    st.markdown('<hr style="border-top: 5px solid #28A745; margin: 20px 0;">', unsafe_allow_html=True)

    # Capabilities Section (Orange: #FD7E14)
    st.markdown('<div style="color: #FD7E14; font-size: 24px; font-weight: bold; margin-bottom: 10px">Capabilities</div>', unsafe_allow_html=True)
    # Scoring Capabilities
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Coral Scoring**")
        for item in CAPABILITIES['scoring']:
            name = item['name']
            pit_form_data[name] = st.checkbox(
                item["label"],
                key=f"pit_{name}",
                value=get_pit_field_value(name, False)
            )
    with col2:
        st.markdown("**Algae Management**")
        for item in CAPABILITIES['algae_management']:
            name = item['name']
            pit_form_data[name] = st.checkbox(
                item["label"],
                key=f"pit_{name}",
                value=get_pit_field_value(name, False)
            )

    # Endgame Capability and New Pickup Questions
    col1, col2, col3 = st.columns(3)
    with col1:
        item = CAPABILITIES['endgame']
        name = item['name']
        options = item['options']
        current_value = get_pit_field_value(name, None)
        display_options = [None] + options
        def format_option(value):
            if value is None:
                return "Choose an option"
            return value
        if current_value is None:
            index = 0
        else:
            index = options.index(current_value) + 1
        selected_value = st.selectbox(
            item["label"],
            options=display_options,
            index=index,
            key=f"pit_{name}",
            format_func=format_option
        )
        pit_form_data[name] = selected_value if selected_value is not None else None
    with col2:
        # Coral Pickup Method (New Question)
        name = "coral_pickup_method"
        options = ["Station", "Ground", "Both", "Neither"]
        current_value = get_pit_field_value(name, None)
        display_options = [None] + options
        if current_value is None:
            index = 0
        else:
            index = options.index(current_value) + 1
        selected_value = st.selectbox(
            "Coral Pickup Method",
            options=display_options,
            index=index,
            key=f"pit_{name}",
            format_func=format_option
        )
        pit_form_data[name] = selected_value if selected_value is not None else None
    with col3:
        # Algae Pickup Method (New Question)
        name = "algae_pickup_method"
        options = ["Ground", "Reef", "Both", "Neither"]
        current_value = get_pit_field_value(name, None)
        display_options = [None] + options
        if current_value is None:
            index = 0
        else:
            index = options.index(current_value) + 1
        selected_value = st.selectbox(
            "Algae Pickup Method",
            options=display_options,
            index=index,
            key=f"pit_{name}",
            format_func=format_option
        )
        pit_form_data[name] = selected_value if selected_value is not None else None

    # Horizontal line after Capabilities (Orange: #FD7E14)
    st.markdown('<hr style="border-top: 5px solid #FD7E14; margin: 20px 0;">', unsafe_allow_html=True)

    # Strategy Section (Indigo: #6610F2)
    st.markdown('<div style="color: #6610F2; font-size: 24px; font-weight: bold; margin-bottom: 10px">Strategy</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        item = PIT_STRATEGY['preferred_role']
        name = item['name']
        options = item['options']
        current_value = get_pit_field_value(name, None)
        display_options = [None] + options
        def format_option(value):
            if value is None:
                return "Choose an option"
            return value
        if current_value is None:
            index = 0
        else:
            index = options.index(current_value) + 1
        selected_value = st.selectbox(
            item["label"],
            options=display_options,
            index=index,
            key=f"pit_{name}",
            format_func=format_option,
            help=item.get('help', '')
        )
        pit_form_data[name] = selected_value if selected_value is not None else None
    with col2:
        item = PIT_STRATEGY['auto_strategy']
        name = item['name']
        pit_form_data[name] = st.text_area(
            item["label"],
            help=item.get('help', ''),
            key=f"pit_{name}",
            value=get_pit_field_value(name, "")
        )

    # Horizontal line after Strategy (Indigo: #6610F2)
    st.markdown('<hr style="border-top: 5px solid #6610F2; margin: 20px 0;">', unsafe_allow_html=True)

    # Robot Photo Section (Purple: #800080)
    st.markdown('<div style="color: #800080; font-size: 24px; font-weight: bold; margin-bottom: 10px">Robot Photo</div>', unsafe_allow_html=True)
    robot_photo = st.file_uploader("Upload a Photo of the Robot", type=["jpg", "jpeg", "png"], key="pit_robot_photo")
    if robot_photo and not st.session_state.pit_form_cleared:
        st.image(robot_photo, caption="Uploaded Robot Photo Preview", width=300)

    # Horizontal line after Robot Photo (Purple: #800080)
    st.markdown('<hr style="border-top: 5px solid #800080; margin: 20px 0;">', unsafe_allow_html=True)

    # Notes Section (Cyan: #17A2B8)
    st.markdown('<div style="color: #17A2B8; font-size: 24px; font-weight: bold; margin-bottom: 10px">Notes</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    for idx, question_item in enumerate(PIT_NOTES['questions']):
        with [col1, col2][idx % 2]:
            name = question_item['name']
            pit_form_data[name] = st.text_area(
                question_item["label"],
                help=question_item.get('help', ''),
                key=f"pit_{name}",
                value=get_pit_field_value(name, "")
            )

    # Horizontal line after Notes (Cyan: #17A2B8)
    st.markdown('<hr style="border-top: 5px solid #17A2B8; margin: 20px 0;">', unsafe_allow_html=True)

    # Submit and Clear buttons for Pit Scouting
    col1, col2 = st.columns(2)
    with col1:
        pit_submit_button = st.button(label="Submit Pit Data", key="pit_submit_button")
    with col2:
        pit_clear_button = st.button(label="Clear Form", key="pit_clear_button")

    # Update session state with the current form data
    st.session_state.pit_form_data = pit_form_data

    # Handle form submission for Pit Scouting
    if pit_submit_button:
        # Validate required fields, including new ones
        if not pit_form_data.get("team_number") or pit_form_data["team_number"] <= 0:
            st.error("Please enter a valid team number (must be greater than 0).")
        elif not pit_form_data.get("scouter_name"):
            st.error("Please enter the scouter's name (cannot be empty).")
        elif not pit_form_data.get("drivetrain_type"):
            st.error("Please select a drivetrain type.")
        elif not pit_form_data.get("endgame_capability"):
            st.error("Please select an endgame capability.")
        elif not pit_form_data.get("preferred_role"):
            st.error("Please select the team's preferred role.")
        elif not pit_form_data.get("programming_language"):
            st.error("Please select a programming language.")
        elif not pit_form_data.get("coral_pickup_method"):
            st.error("Please select a coral pickup method.")
        elif not pit_form_data.get("algae_pickup_method"):
            st.error("Please select an algae pickup method.")
        else:
            # Ensure numeric fields are integers
            numeric_fields = ["team_number"]
            for field in numeric_fields:
                if field in pit_form_data and pit_form_data[field] is not None:
                    pit_form_data[field] = int(pit_form_data[field])

            # Handle photo upload to Firebase Storage
            if robot_photo:
                photo_url = upload_photo_to_storage(robot_photo, pit_form_data["team_number"])
                if photo_url:
                    pit_form_data["robot_photo_url"] = photo_url
                    st.success(f"Photo uploaded successfully! URL: {photo_url}")
                else:
                    st.warning("Photo upload failed, but form data will still be saved.")

            # Save data to Firestore
            success, result = save_data("pit_scout_data", pit_form_data)
            if success:
                doc_id = result
                st.success(f"Pit data submitted successfully! Document ID: {doc_id}")
                st.balloons()
                preserved_data = {
                    "scouter_name": pit_form_data.get("scouter_name", "")
                }
                st.session_state.pit_form_data = preserved_data
                st.session_state.pit_form_cleared = True
            else:
                st.error(f"Failed to submit pit data: {result}")

    # Handle form clearing for Pit Scouting
    if pit_clear_button:
        preserved_data = {
            "scouter_name": st.session_state.pit_form_data.get("scouter_name", "")
        }
        st.session_state.pit_form_data = preserved_data
        st.session_state.pit_form_cleared = True

    # Reset the form_cleared state after clearing
    if st.session_state.pit_form_cleared and not pit_submit_button and not pit_clear_button:
        st.session_state.pit_form_cleared = False

# --- Inspect Errors in Scouting Data ---
st.markdown("---")
st.header("Inspect Scouting Data Errors")
st.markdown("This section allows you to inspect potential errors in the submitted Match Scouting and Pit Scouting data.")

# Define required fields and expected types
match_required_fields = [
    "team_number", "match_number", "scouter_name", "alliance_color",
    "starting_position", "match_outcome", "primary_role"
]
match_numeric_fields = [
    "team_number", "match_number",
    "auto_coral_l1_scored", "auto_coral_l2_scored", "auto_coral_l3_scored", "auto_coral_l4_scored",
    "auto_coral_l1_missed", "auto_coral_l2_missed", "auto_coral_l3_missed", "auto_coral_l4_missed",
    "auto_algae_to_barge", "auto_algae_to_processor", "auto_algae_to_barge_missed", "auto_algae_to_processor_missed",
    "auto_algae_removed",
    "teleop_coral_l1_scored", "teleop_coral_l2_scored", "teleop_coral_l3_scored", "teleop_coral_l4_scored",
    "teleop_coral_l1_missed", "teleop_coral_l2_missed", "teleop_coral_l3_missed", "teleop_coral_l4_missed",
    "teleop_algae_to_barge", "teleop_algae_to_processor", "teleop_algae_to_barge_missed", "teleop_algae_to_processor_missed",
    "teleop_algae_removed",
    "offensive_rating", "defensive_rating", "mobility_rating", "driver_skill_rating"
]
match_rating_fields = [
    "offensive_rating", "defensive_rating", "mobility_rating", "driver_skill_rating"
]

pit_required_fields = [
    "team_number", "scouter_name", "drivetrain_type", "endgame_capability", "preferred_role"
]
pit_numeric_fields = ["team_number"]

# Function to fetch data
def fetch_data(collection_name):
    try:
        db, _ = get_firebase_instances()
        docs = db.collection(collection_name).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['doc_id'] = doc.id
            data.append(doc_data)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching data from {collection_name}: {e}")
        return pd.DataFrame()

# Function to inspect errors
def inspect_scouting_errors(data, required_fields, numeric_fields, rating_fields=None, duplicate_fields=None):
    errors = []
    
    for idx, row in data.iterrows():
        doc_id = row.get('doc_id', 'Unknown')
        
        # Check for missing required fields
        for field in required_fields:
            if field not in row or pd.isna(row[field]):
                errors.append({
                    "doc_id": doc_id,
                    "error_type": "Missing Required Field",
                    "field": field,
                    "value": None,
                    "message": f"Required field '{field}' is missing or None"
                })
        
        # Check for invalid data types in numeric fields
        for field in numeric_fields:
            if field in row and not pd.isna(row[field]):
                if not isinstance(row[field], (int, float)) or isinstance(row[field], bool):
                    errors.append({
                        "doc_id": doc_id,
                        "error_type": "Invalid Data Type",
                        "field": field,
                        "value": row[field],
                        "message": f"Field '{field}' should be a number, got {type(row[field])}"
                    })
                # Check for negative values in counts
                if field not in (rating_fields or []) and row[field] < 0:
                    errors.append({
                        "doc_id": doc_id,
                        "error_type": "Out of Range",
                        "field": field,
                        "value": row[field],
                        "message": f"Field '{field}' should not be negative"
                    })
        
        # Check rating fields (1-5)
        if rating_fields:
            for field in rating_fields:
                if field in row and not pd.isna(row[field]):
                    if not isinstance(row[field], (int, float)):
                        errors.append({
                            "doc_id": doc_id,
                            "error_type": "Invalid Data Type",
                            "field": field,
                            "value": row[field],
                            "message": f"Rating field '{field}' should be a number, got {type(row[field])}"
                        })
                    elif row[field] < 1 or row[field] > 5:
                        errors.append({
                            "doc_id": doc_id,
                            "error_type": "Out of Range",
                            "field": field,
                            "value": row[field],
                            "message": f"Rating field '{field}' should be between 1 and 5"
                        })
    
    # Check for duplicates
    if duplicate_fields and not data.empty:
        duplicates = data.duplicated(subset=duplicate_fields, keep=False)
        for idx, is_duplicate in enumerate(duplicates):
            if is_duplicate:
                row = data.iloc[idx]
                doc_id = row.get('doc_id', 'Unknown')
                duplicate_values = {field: row[field] for field in duplicate_fields}
                errors.append({
                    "doc_id": doc_id,
                    "error_type": "Duplicate Entry",
                    "field": ", ".join(duplicate_fields),
                    "value": duplicate_values,
                    "message": f"Duplicate entry for {duplicate_values}"
                })
    
    return pd.DataFrame(errors)

# Inspect Match Scouting Data
st.subheader("Match Scouting Data Errors")
match_data = fetch_data("match_scout_data")
if not match_data.empty:
    match_errors = inspect_scouting_errors(
        match_data,
        required_fields=match_required_fields,
        numeric_fields=match_numeric_fields,
        rating_fields=match_rating_fields,
        duplicate_fields=["team_number", "match_number"]
    )
    if not match_errors.empty:
        st.dataframe(match_errors, use_container_width=True)
        csv = match_errors.to_csv(index=False)
        st.download_button(
            label="Download Match Scouting Errors as CSV",
            data=csv,
            file_name="match_scouting_errors.csv",
            mime="text/csv",
            key="download_match_errors_csv"
        )
    else:
        st.success("No errors found in the Match Scouting data.")
else:
    st.info("No Match Scouting data available to inspect.")

# Inspect Pit Scouting Data
st.subheader("Pit Scouting Data Errors")
pit_data = fetch_data("pit_scout_data")
if not pit_data.empty:
    pit_errors = inspect_scouting_errors(
        pit_data,
        required_fields=pit_required_fields,
        numeric_fields=pit_numeric_fields,
        duplicate_fields=["team_number"]
    )
    if not pit_errors.empty:
        st.dataframe(pit_errors, use_container_width=True)
        csv = pit_errors.to_csv(index=False)
        st.download_button(
            label="Download Pit Scouting Errors as CSV",
            data=csv,
            file_name="pit_scouting_errors.csv",
            mime="text/csv",
            key="download_pit_errors_csv"
        )
    else:
        st.success("No errors found in the Pit Scouting data.")
else:
    st.info("No Pit Scouting data available to inspect.")