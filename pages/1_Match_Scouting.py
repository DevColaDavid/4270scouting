import streamlit as st
from utils.form_config import MATCH_INFO, AUTONOMOUS, TELEOP, ENDGAME, PERFORMANCE_RATINGS, ANALYSIS
from utils.utils import save_data

st.set_page_config(page_title="Match Scouting", page_icon="📝", layout="wide")

# Custom CSS for better styling
st.markdown("""
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
    }
    .stNumberInput, .stTextInput, .stSelectbox, .stCheckbox, .stSlider, .stTextArea {
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📝 Match Scouting")
st.markdown("Fill out the form below to scout a match.")

# Initialize session state to manage form clearing
if 'form_cleared' not in st.session_state:
    st.session_state.form_cleared = False

# Create the form
with st.form(key="scouting_form"):
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
                value=1 if st.session_state.form_cleared else None
            )
    with col2:
        for item in MATCH_INFO['basic_info'][2:3]:  # Alliance Color
            name = item['name']
            form_data[name] = st.selectbox(
                item['label'],
                options=item['options'],
                key=name,
                index=0 if st.session_state.form_cleared else None
            )
        item = MATCH_INFO['starting_position']
        name = item['name']
        form_data[name] = st.selectbox(
            item['label'],
            options=item['options'],
            key=name,
            index=0 if st.session_state.form_cleared else None
        )
    with col3:
        for item in MATCH_INFO['basic_info'][3:]:  # Scouter Name
            name = item['name']
            form_data[name] = st.text_input(
                item['label'],
                key=name,
                value="" if st.session_state.form_cleared else None
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
                value=False if st.session_state.form_cleared else None
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
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
                value=0 if st.session_state.form_cleared else None,
                step=1,
                key=name
            )

    # Endgame Section
    st.subheader("Endgame")
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        item = ENDGAME['climb_status']
        name = item['name']
        form_data[name] = st.selectbox(
            item['label'],
            options=item['options'],
            key=name,
            index=0 if st.session_state.form_cleared else None
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
                value=3 if st.session_state.form_cleared else None,
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
                value="" if st.session_state.form_cleared else None
            )

    # Submit and Clear buttons
    col1, col2 = st.columns(2)
    with col1:
        submit_button = st.form_submit_button(label="Submit Match Data")
    with col2:
        clear_button = st.form_submit_button(label="Clear Form")

# Handle form submission and clearing
if submit_button:
    # Validate required fields
    if not form_data.get("team_number") or form_data["team_number"] <= 0:
        st.error("Please enter a valid team number.")
    elif not form_data.get("match_number") or form_data["match_number"] <= 0:
        st.error("Please enter a valid match number.")
    elif not form_data.get("scouter_name"):
        st.error("Please enter the scouter's name.")
    else:
        # Save data to Firestore
        success, doc_id = save_data(form_data)
        if success:
            st.success(f"Match data submitted successfully! Document ID: {doc_id}")  # Green confirmation
            st.balloons()  # Balloon effect
            st.session_state.form_cleared = False  # Reset the form_cleared state
        else:
            st.error("Failed to submit match data.")

if clear_button:
    st.session_state.form_cleared = True  # Trigger form clearing
    st.rerun()  # Rerun the app to reset the form fields

# Reset the form_cleared state after clearing
if st.session_state.form_cleared:
    st.session_state.form_cleared = False