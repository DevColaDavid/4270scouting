import streamlit as st
from utils.form_config import MATCH_INFO, AUTONOMOUS, TELEOP, ENDGAME, PERFORMANCE_RATINGS, ANALYSIS
from utils.utils import save_data

st.set_page_config(page_title="Match Scouting", page_icon="📝", layout="wide")

# Custom CSS for better styling
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
        # Special case for team_number, match_number, alliance_color, and starting_position: default to None
        if name in ["team_number", "match_number", "alliance_color", "starting_position"]:
            return None
        return default_value
    # Special case for team_number, match_number, alliance_color, and starting_position: default to None if not set
    if name in ["team_number", "match_number", "alliance_color", "starting_position"] and name not in st.session_state.form_data:
        return None
    return st.session_state.form_data.get(name, default_value)

# Form data dictionary to store the current values
form_data = {}

# Match Info Section
st.subheader("Match Information")
col1, col2, col3 = st.columns(3)
with col1:
    for item in MATCH_INFO['basic_info'][:2]:  # Team Number, Match Number
        name = item['name']
        form_data[name] = st.number_input(
            item['label'],
            min_value=1,
            step=1,
            key=name,
            value=get_field_value(name, None)  # Default to None
        )
with col2:
    # Alliance Color
    for item in MATCH_INFO['basic_info'][2:3]:  # Alliance Color (index 2)
        name = item['name']
        options = item['options']
        current_value = get_field_value(name, None)
        # Add None as a valid option for the selectbox
        display_options = [None] + options
        # Format function to display "Choose an option" when value is None
        def format_option(value):
            if value is None:
                return "Choose an option"
            return value
        # If current_value is None, index should be 0 (None); otherwise, adjust for the None option
        if current_value is None:
            index = 0
        else:
            index = options.index(current_value) + 1  # +1 because None is at index 0
        selected_value = st.selectbox(
            item['label'],
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
    # Add None as a valid option for the selectbox
    display_options = [None] + options
    # Format function to display "Choose an option" when value is None
    def format_option(value):
        if value is None:
            return "Choose an option"
        return value
    # If current_value is None, index should be 0 (None); otherwise, adjust for the None option
    if current_value is None:
        index = 0
    else:
        index = options.index(current_value) + 1  # +1 because None is at index 0
    selected_value = st.selectbox(
        item['label'],
        options=display_options,
        index=index,
        key=name,
        format_func=format_option
    )
    form_data[name] = selected_value if selected_value is not None else None

with col3:
    for item in MATCH_INFO['basic_info'][3:]:  # Scouter Name
        name = item['name']
        form_data[name] = st.text_input(
            item['label'],
            key=name,
            value=get_field_value(name, "")
        )

# Autonomous Section
st.subheader("Autonomous Period")
# Mobility at the start
col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    st.markdown("**Mobility**")
    for mobility_item in AUTONOMOUS['mobility']:
        name = mobility_item['name']
        form_data[name] = st.checkbox(
            mobility_item['label'],
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
            scoring_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )
with col2:
    st.markdown("**Coral Missed**")
    for missed_item in AUTONOMOUS['missed_attempts']:
        name = missed_item['name']
        form_data[name] = st.number_input(
            missed_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )

# Algae Management
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown("**Algae Scored**")
    for algae_item in AUTONOMOUS['algae_management'][:2]:  # Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )
with col2:
    st.markdown("**Algae Missed**")
    for algae_item in AUTONOMOUS['algae_management'][2:4]:  # Missed Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )
with col3:
    st.markdown("**Algae Removed**")
    for algae_item in AUTONOMOUS['algae_management'][4:5]:  # Algae Removed
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )

# Teleop Section
st.subheader("Teleop Period")
# Scoring and Missed Attempts side by side
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Coral Scored**")
    for scoring_item in TELEOP['scoring']:
        name = scoring_item['name']
        form_data[name] = st.number_input(
            scoring_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )
with col2:
    st.markdown("**Coral Missed**")
    for missed_item in TELEOP['missed_attempts']:
        name = missed_item['name']
        form_data[name] = st.number_input(
            missed_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )

# Algae Management
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown("**Algae Scored**")
    for algae_item in TELEOP['algae_management'][:2]:  # Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )
with col2:
    st.markdown("**Algae Missed**")
    for algae_item in TELEOP['algae_management'][2:4]:  # Missed Algae to Barge, Processor
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )
with col3:
    st.markdown("**Algae Removed**")
    for algae_item in TELEOP['algae_management'][4:5]:  # Algae Removed
        name = algae_item['name']
        form_data[name] = st.number_input(
            algae_item['label'],
            min_value=0,
            value=get_field_value(name, 0),
            step=1,
            key=name
        )

# Endgame Section
st.subheader("Endgame")
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
        item['label'],
        options=options,
        index=options.index(current_value),
        key=name
    )
with col2:
    pass  # Empty column for spacing
with col3:
    pass  # Empty column for spacing

# Performance Ratings Section
st.subheader("Performance Ratings")
col1, col2, col3 = st.columns(3)
for idx, rating_item in enumerate(PERFORMANCE_RATINGS['ratings']):
    with [col1, col2, col3][idx % 3]:
        name = rating_item['name']
        form_data[name] = st.slider(
            rating_item['label'],
            min_value=rating_item['min'],
            max_value=rating_item['max'],
            value=get_field_value(name, 3),
            step=1,
            key=name
        )

# Analysis Section
st.subheader("Qualitative Analysis")
col1, col2 = st.columns(2)
for idx, question_item in enumerate(ANALYSIS['questions']):
    with [col1, col2][idx % 2]:
        name = question_item['name']
        form_data[name] = st.text_area(
            question_item['label'],
            help=question_item.get('help', ''),
            key=name,
            value=get_field_value(name, "")
        )

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
    else:
        # Save data to Firestore
        success, doc_id = save_data(form_data)
        if success:
            st.success(f"Match data submitted successfully! Document ID: {doc_id}")  # Green confirmation
            st.balloons()  # Balloon effect
            st.session_state.form_cleared = True  # Trigger form clearing after successful submission
            st.session_state.form_data = {}  # Clear the stored form data
        else:
            st.error("Failed to submit match data.")

# Handle form clearing
if clear_button:
    st.session_state.form_cleared = True  # Trigger form clearing
    st.session_state.form_data = {}  # Clear the stored form data
    st.rerun()  # Rerun the app to reset the form fields

# Reset the form_cleared state after clearing
if st.session_state.form_cleared and not submit_button and not clear_button:
    st.session_state.form_cleared = False