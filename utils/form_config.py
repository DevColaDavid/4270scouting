# utils/form_config.py
MATCH_INFO = {
    'basic_info': [
        {'name': 'team_number', 'label': 'Team Number', 'type': 'number'},
        {'name': 'match_number', 'label': 'Match Number', 'type': 'number'},
        {'name': 'alliance_color', 'label': 'Alliance', 'type': 'select', 'options': ['Red', 'Blue']},
        {'name': 'scouter_name', 'label': 'Scouter Name', 'type': 'text'},
    ],
    'starting_position': {
        'name': 'starting_position',
        'label': 'Starting Position',
        'type': 'select',
        'options': ['Left', 'Center', 'Right']
    }
}

MATCH_OUTCOME = {
    'outcome': {
        'name': 'match_outcome',
        'label': 'Match Outcome',
        'type': 'select',
        'options': ['Won', 'Lost', 'Tie'],
        'help': "Select the outcome from this team's perspective: Won (their alliance won), Lost (opposing alliance won), or Tie (scores equal)."
    }
}

AUTONOMOUS = {
    'mobility': [
        {'name': 'auto_taxi_left', 'label': 'Taxi Auto Off the Starting Line', 'type': 'checkbox'}
    ],
    'scoring': [
        {'name': 'auto_coral_l1', 'label': 'Coral Scored on L1', 'type': 'number'},
        {'name': 'auto_coral_l2', 'label': 'Coral Scored on L2', 'type': 'number'},
        {'name': 'auto_coral_l3', 'label': 'Coral Scored on L3', 'type': 'number'},
        {'name': 'auto_coral_l4', 'label': 'Coral Scored on L4', 'type': 'number'}
    ],
    'missed_attempts': [
        {'name': 'auto_missed_coral_l1', 'label': 'Coral Missed on L1', 'type': 'number'},
        {'name': 'auto_missed_coral_l2', 'label': 'Coral Missed on L2', 'type': 'number'},
        {'name': 'auto_missed_coral_l3', 'label': 'Coral Missed on L3', 'type': 'number'},
        {'name': 'auto_missed_coral_l4', 'label': 'Coral Missed on L4', 'type': 'number'}
    ],
    'algae_management': [
        {'name': 'auto_algae_barge', 'label': 'Algae Scored on Barge', 'type': 'number'},
        {'name': 'auto_algae_processor', 'label': 'Algae Scored on Processor', 'type': 'number'},
        {'name': 'auto_missed_algae_barge', 'label': 'Algae Missed on Barge', 'type': 'number'},
        {'name': 'auto_missed_algae_processor', 'label': 'Algae Missed on Processor', 'type': 'number'},
        {'name': 'auto_algae_removed', 'label': 'Algae Removed from Reef', 'type': 'number'}
    ]
}

TELEOP = {
    'scoring': [
        {'name': 'teleop_coral_l1', 'label': 'Coral Scored on L1', 'type': 'number'},
        {'name': 'teleop_coral_l2', 'label': 'Coral Scored on L2', 'type': 'number'},
        {'name': 'teleop_coral_l3', 'label': 'Coral Scored on L3', 'type': 'number'},
        {'name': 'teleop_coral_l4', 'label': 'Coral Scored on L4', 'type': 'number'}
    ],
    'missed_attempts': [
        {'name': 'teleop_missed_coral_l1', 'label': 'Coral Missed on L1', 'type': 'number'},
        {'name': 'teleop_missed_coral_l2', 'label': 'Coral Missed on L2', 'type': 'number'},
        {'name': 'teleop_missed_coral_l3', 'label': 'Coral Missed on L3', 'type': 'number'},
        {'name': 'teleop_missed_coral_l4', 'label': 'Coral Missed on L4', 'type': 'number'}
    ],
    'algae_management': [
        {'name': 'teleop_algae_barge', 'label': 'Algae Scored on Barge', 'type': 'number'},
        {'name': 'teleop_algae_processor', 'label': 'Algae Scored on Processor', 'type': 'number'},
        {'name': 'teleop_missed_algae_barge', 'label': 'Algae Missed on Barge', 'type': 'number'},
        {'name': 'teleop_missed_algae_processor', 'label': 'Algae Missed on Processor', 'type': 'number'},
        {'name': 'teleop_algae_removed', 'label': 'Algae Removed from Reef', 'type': 'number'}
    ]
}

ENDGAME = {
    'climb_status': {
        'name': 'climb_status',
        'label': 'Climb Status',
        'type': 'select',
        'options': ['None', 'Parked', 'Shallow Climb', 'Deep Climb']
    }
}

PERFORMANCE_RATINGS = {
    'ratings': [
        {'name': 'defense_rating', 'label': 'Defense Rating', 'type': 'slider', 'min': 1, 'max': 5},
        {'name': 'speed_rating', 'label': 'Speed Rating', 'type': 'slider', 'min': 1, 'max': 5},
        {'name': 'driver_skill_rating', 'label': 'Driver Skill Rating', 'type': 'slider', 'min': 1, 'max': 5}
    ]
}

# New section for Strategy (Primary Role)
STRATEGY = {
    'primary_role': {
        'name': 'primary_role',
        'label': 'Primary Role',
        'type': 'select',
        'options': ['Offense', 'Defense', 'Both', 'Neither'],
        'help': "Select the team's primary role during the match: Offense (focused on scoring), Defense (focused on blocking opponents), Both (balanced), or Neither (minimal activity)."
    }
}

ANALYSIS = {
    'questions': [
        {'name': 'defense_qa', 'label': 'Defense Q/A', 'type': 'textarea', 'help': 'How did they play defense, push power or speed? (if not defense put N/A)'},
        {'name': 'teleop_qa', 'label': 'Teleop Q/A', 'type': 'textarea', 'help': 'How are they scoring (ground/station), speed, skill?'},
        {'name': 'auto_qa', 'label': 'Autonomous Q/A', 'type': 'textarea', 'help': 'Speed, Path, Accuracy'},
        {'name': 'comments', 'label': 'Additional Comments', 'type': 'textarea'}
    ]
}