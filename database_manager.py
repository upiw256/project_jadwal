import json
import os
import streamlit as st

DB_FILE = 'database_jadwal.json'

def read_database():
    """Reads the schedule database from JSON file."""
    if not os.path.exists(DB_FILE):
        return None
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def save_database(data):
    """Saves the schedule database to JSON file."""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def reset_database():
    """Deletes the database and token files to reset the app."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    if os.path.exists('token.pickle'):
        os.remove('token.pickle')
    st.success("Database and Token have been reset.")
    st.rerun()
