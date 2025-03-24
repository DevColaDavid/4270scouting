# pages/1_Match_Scouting.py
import streamlit as st
from utils.form_config import MATCH_INFO, AUTONOMOUS, TELEOP, ENDGAME, PERFORMANCE_RATINGS, ANALYSIS, MATCH_OUTCOME, STRATEGY
from utils.utils import save_data
from utils.utils import setup_sidebar_navigation

st.set_page_config(page_title="Match Scouting", page_icon="📝", layout="wide",initial_sidebar_state="collapsed")

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please log in to access this page.")
    st.stop()

# Set up the sidebar navigation
setup_sidebar_navigation()

# Page content
st.title("Match Scouting")
st.write("This is the Match Scouting page.")
# Add your Match Scouting form or content here

# Check if the user is logged in and has the appropriate authority
if not st.session_state.get("logged_in", False):
    st.error("You must be logged in to access this page.")
    st.stop()

# Check user authority
allowed_authorities = ["Scouter", "Admin", "Owner"]
if st.session_state.get("authority") not in allowed_authorities:
    st.error("You do not have the required authority to access this page. Required: Scouter, Admin, or Owner.")
    st.stop()

# Custom CSS for button styling only
st.markdown("""
    <style>
    .stNumberInput, .stTextInput, .stSelectbox, .stCheckbox, .stSlider, .stTextArea {
        margin-bottom: 15px;
    }
    /* Style for the Submit Match Data button */
    button[kind="primary"][key="submit_button"] {
        background-color: #007BFF; /* Blue */
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
    }
    button[kind="primary"][key="submit_button"]:hover {
        background-color: #0056b3; /* Darker blue on hover */
    }
    /* Style for the Clear Form button */
    button[kind="primary"][key="clear_button"] {
        background-color: #DC3545; /* Red */
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
    }
    button[kind="primary"][key="clear_button"]:hover {
        background-color: #b02a37; /* Darker red on hover */
    }
    </style>
""", unsafe_allow_html=True)

st.title("📝 Match Scouting")
st.markdown("Fill out the form below to scout a match.")

# Initialize session state to manage form data and clearing
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'form_cleared' not in st.session_state:
    st.session_state.form_cleared = False

# Function to get the current value of a field, considering form clearing
def get_field_value(name, default_value):
    if st.session_state.form_cleared:
        # Preserve scouter_name and alliance_color
        if name in ["scouter_name", "alliance_color"]:
            return st.session_state.form_data.get(name, default_value)
        # Special case for team_number, match_number, starting_position, match_outcome, primary_role: default to None
        if name in ["team_number", "match_number", "starting_position", "match_outcome", "primary_role"]:
            return None
        return default_value
    # Special case for team_number, match_number, alliance_color, starting_position, match_outcome, primary_role: default to None if not set
    if name in ["team_number", "match_number", "alliance_color", "starting_position", "match_outcome", "primary_role"] and name not in st.session_state.form_data:
        return None
    return st.session_state.form_data.get(name, default_value)

# Callback function to update session state when a number input changes
def update_number_input(name):
    st.session_state.form_data[name] = st.session_state[name]

# Form data dictionary to store the current values
form_data = {}

# Match Info Section (Blue: #007BFF)
st.markdown('<div style="color: #007BFF; font-size: 24px; font-weight: bold; margin-bottom: 10px">Match Information</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    for item in MATCH_INFO['basic_info'][:2]:  # Team Number, Match Number
        name = item['name']
        form_data[name] = st.number_input(
            item["label"],
            min_value=1,
            step=1,
            key=name,
            value=get_field_value(name, None),
            on_change=update_number_input,
            args=(name,)
        )
with col2:
    # Alliance Color
    for item in MATCH_INFO['basic_info'][2:3]:  # Alliance Color (index 2)
        name = item['name']
        options = item['options']
        current_value = get_field_value(name, None)
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
            key=name,
            format_func=format_option
        )
        form_data[name] = selected_value if selected_value is not None else None

    # Starting Position
    item = MATCH_INFO['starting_position']
    name = item['name']
    options = item['options']
    current_value = get_field_value(name, None)
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
        key=name,
        format_func=format_option
    )
    form_data[name] = selected_value if selected_value is not None else None

with col3:
    # Scouter Name
    for item in MATCH_INFO['basic_info'][3:4]:  # Scouter Name (index 3)
        name = item['name']
        form_data[name] = st.text_input(
            item["label"],
            key=name,
            value=get_field_value(name, "")
        )

# Horizontal line after Match Info (Blue: #007BFF)
st.markdown('<hr style="border-top: 5px solid #007BFF; margin: 20px 0;">', unsafe_allow_html=True)

# Autonomous Section (Green: #28A745)
st.markdown('<div style="color: #28A745; font-size: 24px; font-weight: bold; margin-bottom: 10px">Autonomous Period</div>', unsafe_allow_html=True)
# Mobility at the start
col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    st.markdown("**Mobility**")
    for mobility_item in AUTONOMOUS['mobility']:
        name = mobility_item['name']
        form_data[name] = st.checkbox(
            mobility_item["label"],
            key=name,
            value=get_field_value(name, False)
        )
with col2:
    pass  # Empty column for spacing
with col3:
    pass  # Empty column for spacing

# Scoring and Missed Attempts side by side
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Coral Scored**")
    for scoring_item in AUTONOMOUS['scoring']:
        name = scoring_item['name']
        form_data[name] = st.number_input(
            scoring_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )
with col2:
    st.markdown("**Coral Missed**")
    for missed_item in AUTONOMOUS['missed_attempts']:
        name = missed_item['name']
        form_data[name] = st.number_input(
            missed_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )

# Algae Management
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown("**Algae Scored**")
    for algae_item in AUTONOMOUS['algae_management'][:2]:  # Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )
with col2:
    st.markdown("**Algae Missed**")
    for algae_item in AUTONOMOUS['algae_management'][2:4]:  # Missed Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )
with col3:
    st.markdown("**Algae Removed**")
    for algae_item in AUTONOMOUS['algae_management'][4:5]:  # Algae Removed
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )

# Horizontal line after Autonomous (Green: #28A745)
st.markdown('<hr style="border-top: 5px solid #28A745; margin: 20px 0;">', unsafe_allow_html=True)

# Teleop Section (Orange: #FD7E14)
st.markdown('<div style="color: #FD7E14; font-size: 24px; font-weight: bold; margin-bottom: 10px">Teleop Period</div>', unsafe_allow_html=True)
# Scoring and Missed Attempts side by side
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Coral Scored**")
    for scoring_item in TELEOP['scoring']:
        name = scoring_item['name']
        form_data[name] = st.number_input(
            scoring_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )
with col2:
    st.markdown("**Coral Missed**")
    for missed_item in TELEOP['missed_attempts']:
        name = missed_item['name']
        form_data[name] = st.number_input(
            missed_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )

# Algae Management
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown("**Algae Scored**")
    for algae_item in TELEOP['algae_management'][:2]:  # Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )
with col2:
    st.markdown("**Algae Missed**")
    for algae_item in TELEOP['algae_management'][2:4]:  # Missed Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )
with col3:
    st.markdown("**Algae Removed**")
    for algae_item in TELEOP['algae_management'][4:5]:  # Algae Removed
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item["label"],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name,
            on_change=update_number_input,
            args=(name,)
        )

# Horizontal line after Teleop (Orange: #FD7E14)
st.markdown('<hr style="border-top: 5px solid #FD7E14; margin: 20px 0;">', unsafe_allow_html=True)

# Endgame Section (Purple: #6F42C1)
st.markdown('<div style="color: #6F42C1; font-size: 24px; font-weight: bold; margin-bottom: 10px">Endgame</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    item = ENDGAME['climb_status']
    name = item['name']
    options = item['options']
    default_index = 0
    current_value = get_field_value(name, options[default_index])
    if current_value not in options:
        current_value = options[default_index]
    form_data[name] = st.selectbox(
        item["label"],
        options=options,
        index=options.index(current_value),
        key=name
    )
with col2:
    pass  # Empty column for spacing
with col3:
    pass  # Empty column for spacing

# Horizontal line after Endgame (Purple: #6F42C1)
st.markdown('<hr style="border-top: 5px solid #6F42C1; margin: 20px 0;">', unsafe_allow_html=True)

# Performance Ratings Section (Teal: #20C997)
st.markdown('<div style="color: #20C997; font-size: 24px; font-weight: bold; margin-bottom: 10px">Performance Ratings</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
for idx, rating_item in enumerate(PERFORMANCE_RATINGS['ratings']):
    with [col1, col2, col3][idx % 3]:
        name = rating_item['name']
        form_data[name] = st.slider(
            rating_item["label"],
            min_value=rating_item['min'],
            max_value=rating_item['max'],
            value=get_field_value(name, 3),
            step=1,
            key=name
        )

# Horizontal line after Performance Ratings (Teal: #20C997)
st.markdown('<hr style="border-top: 5px solid #20C997; margin: 20px 0;">', unsafe_allow_html=True)

# Strategy Section (Indigo: #6610F2)
st.markdown('<div style="color: #6610F2; font-size: 24px; font-weight: bold; margin-bottom: 10px">Strategy</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    item = STRATEGY['primary_role']
    name = item['name']
    options = item['options']
    current_value = get_field_value(name, None)
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
        key=name,
        format_func=format_option,
        help=item.get('help', '')
    )
    form_data[name] = selected_value if selected_value is not None else None
with col2:
    pass  # Empty column for spacing
with col3:
    pass  # Empty column for spacing

# Horizontal line after Strategy (Indigo: #6610F2)
st.markdown('<hr style="border-top: 5px solid #6610F2; margin: 20px 0;">', unsafe_allow_html=True)

# Analysis Section (Cyan: #17A2B8)
st.markdown('<div style="color: #17A2B8; font-size: 24px; font-weight: bold; margin-bottom: 10px">Qualitative Analysis</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
for idx, question_item in enumerate(ANALYSIS['questions']):
    with [col1, col2][idx % 2]:
        name = question_item['name']
        form_data[name] = st.text_area(
            question_item["label"],
            help=question_item.get('help', ''),
            key=name,
            value=get_field_value(name, "")
        )

# Horizontal line after Analysis (Cyan: #17A2B8)
st.markdown('<hr style="border-top: 5px solid #17A2B8; margin: 20px 0;">', unsafe_allow_html=True)

# Match Outcome Section (Red: #DC3545)
st.markdown('<div style="color: #DC3545; font-size: 24px; font-weight: bold; margin-bottom: 10px">Match Outcome</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    item = MATCH_OUTCOME['outcome']
    name = item['name']
    options = item['options']
    current_value = get_field_value(name, None)
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
        key=name,
        format_func=format_option,
        help=item.get('help', '')
    )
    form_data[name] = selected_value if selected_value is not None else None
with col2:
    pass  # Empty column for spacing
with col3:
    pass  # Empty column for spacing

# Horizontal line after Match Outcome (Red: #DC3545)
st.markdown('<hr style="border-top: 5px solid #DC3545; margin: 20px 0;">', unsafe_allow_html=True)

# Submit and Clear buttons
col1, col2 = st.columns(2)
with col1:
    submit_button = st.button(label="Submit Match Data", key="submit_button")
with col2:
    clear_button = st.button(label="Clear Form", key="clear_button")

# Update session state with the current form data
st.session_state.form_data = form_data

# Handle form submission
if submit_button:
    # Validate required fields
    if not form_data.get("team_number") or form_data["team_number"] <= 0:
        st.error("Please enter a valid team number.")
    elif not form_data.get("match_number") or form_data["match_number"] <= 0:
        st.error("Please enter a valid match number.")
    elif not form_data.get("scouter_name"):
        st.error("Please enter the scouter's name.")
    elif not form_data.get("alliance_color"):
        st.error("Please select an alliance color.")
    elif not form_data.get("starting_position"):
        st.error("Please select a starting position.")
    elif not form_data.get("match_outcome"):
        st.error("Please select the match outcome.")
    elif not form_data.get("primary_role"):
        st.error("Please select the team's primary role.")
    else:
        # Save data to Firestore
        success, doc_id = save_data(form_data)
        if success:
            st.success(f"Match data submitted successfully! Document ID: {doc_id}")
            st.balloons()
            preserved_data = {
                "scouter_name": form_data.get("scouter_name", ""),
                "alliance_color": form_data.get("alliance_color", None)
            }
            st.session_state.form_data = preserved_data
            st.session_state.form_cleared = True
        else:
            st.error("Failed to submit match data.")

# Handle form clearing
if clear_button:
    preserved_data = {
        "scouter_name": st.session_state.form_data.get("scouter_name", ""),
        "alliance_color": st.session_state.form_data.get("alliance_color", None)
    }
    st.session_state.form_data = preserved_data
    st.session_state.form_cleared = True

# Reset the form_cleared state after clearing
if st.session_state.form_cleared and not submit_button and not clear_button:
    st.session_state.form_cleared = False