# migrate_to_firestore.py
import pandas as pd
from google.cloud import firestore
from google.oauth2 import service_account
import streamlit as st

# Initialize Firestore
db = firestore.Client.from_service_account_json("firestore-key.json")
COLLECTION_NAME = "scouting_data"

# Load existing data from scouting_data.csv
df = pd.read_csv("scouting_data.csv")

# Migrate each row to Firestore
for _, row in df.iterrows():
    match_data = row.to_dict()
    # Convert NaN to None for Firestore compatibility
    match_data = {k: (None if pd.isna(v) else v) for k, v in match_data.items()}
    db.collection(COLLECTION_NAME).add(match_data)

print("Data migration to Firestore completed successfully!")