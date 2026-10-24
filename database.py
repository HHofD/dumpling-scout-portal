import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def get_gsheets_connection():
    """Establishes a secure connection to your private Google Sheet database."""
    return st.connection("gsheets", type=GSheetsConnection)

def initialize_database():
    """
    Ensures that required worksheets exist.
    With Google Sheets, you should create three tabs manually: 'TeamChat', 'PrivateChats', and 'Pipeline'.
    This function acts as a safety validator.
    """
    try:
        conn = get_gsheets_connection()
        # Test connection by attempting to read headers
        conn.read(worksheet="Pipeline", ttl="10s")
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets. Verify your service account keys in Streamlit Secrets. Error: {e}")

def save_team_message(user_name: str, message: str):
    """Appends a new conversation row to your shared TeamChat worksheet."""
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="TeamChat", ttl="1s")
    except Exception:
        df = pd.DataFrame(columns=["user_name", "message", "timestamp"])
        
    new_row = pd.DataFrame([{
        "user_name": user_name,
        "message": message,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="TeamChat", data=updated_df)

def load_team_messages():
    """Loads all conversation rows from the shared TeamChat worksheet."""
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="TeamChat", ttl="1s")
        # Ensure correct column formats
        return df.fillna("")
    except Exception:
        return pd.DataFrame(columns=["user_name", "message", "timestamp"])

def save_private_message(user_name: str, role: str, message: str):
    """Appends a private chat message to the PrivateChats worksheet."""
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="PrivateChats", ttl="1s")
    except Exception:
        df = pd.DataFrame(columns=["user_name", "role", "message", "timestamp"])
        
    new_row = pd.DataFrame([{
        "user_name": user_name,
        "role": role,
        "message": message,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="PrivateChats", data=updated_df)

def load_private_messages(user_name: str):
    """Loads only private chat messages belonging to the active user."""
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="PrivateChats", ttl="1s")
        filtered_df = df[df["user_name"] == user_name]
        return filtered_df[["role", "message"]].fillna("")
    except Exception:
        return pd.DataFrame(columns=["role", "message"])

def add_event_to_pipeline(data: dict):
    """Appends a newly calculated event opportunity to the shared Google Sheet Pipeline."""
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="1s")
    except Exception:
        df = pd.DataFrame(columns=[
            "id", "event_name", "location", "event_date", "category", "est_attendance",
            "gross_revenue", "total_expenses", "net_profit", "roi_text",
            "decision_tier", "prep_dumplings", "status", "notes"
        ])
        
    next_id = int(df["id"].max() + 1) if not df.empty and "id" in df.columns else 1
    
    new_row = pd.DataFrame([{
        "id": next_id,
        "event_name": data.get("event_name"),
        "location": data.get("location"),
        "event_date": data.get("event_date"),
        "category": data.get("category"),
        "est_attendance": data.get("est_attendance"),
        "gross_revenue": data.get("gross_revenue"),
        "total_expenses": data.get("total_expenses"),
        "net_profit": data.get("net_profit"),
        "roi_text": data.get("roi_text"),
        "decision_tier": data.get("decision_tier"),
        "prep_dumplings": data.get("prep_dumplings"),
        "status": data.get("status", "Discovered"),
        "notes": data.get("notes", "")
    }])
    
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="Pipeline", data=updated_df)

def load_pipeline():
    """Loads all evaluated event rows from Google Sheets, ordered by profit."""
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="2s")
        if not df.empty and "net_profit" in df.columns:
            df["net_profit"] = pd.to_numeric(df["net_profit"], errors="coerce")
            df = df.sort_values(by="net_profit", ascending=False)
        return df.fillna("")
    except Exception:
        return pd.DataFrame()

def update_event_status(event_id: int, new_status: str):
    """Finds an event row by ID in Google Sheets and updates its active status."""
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="1s")
        if not df.empty and "id" in df.columns:
            # Force match ID type to numeric
            df["id"] = pd.to_numeric(df["id"], errors="coerce")
            idx = df[df["id"] == int(event_id)].index
            if not idx.empty:
                df.loc[idx, "status"] = new_status
                conn.update(worksheet="Pipeline", data=df)
    except Exception as e:
        st.error(f"Failed to update event status: {e}")
