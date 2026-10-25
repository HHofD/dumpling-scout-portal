import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

PIPELINE_COLUMNS = [
    "id", "event_name", "location", "event_date", "product_format",
    "participation_status", "decision_tier", "gross_revenue",
    "total_expenses", "net_profit", "roi_text", "prep_dumplings", "notes"
]

def get_gsheets_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def initialize_database():
    try:
        conn = get_gsheets_connection()
        conn.read(worksheet="Pipeline", ttl="10s")
    except Exception as e:
        st.error(f"Waiting for Google Sheets connection: {e}")

def save_team_message(user_name: str, message: str):
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
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="TeamChat", ttl="1s")
        return df.fillna("")
    except Exception:
        return pd.DataFrame(columns=["user_name", "message", "timestamp"])

def save_private_message(user_name: str, role: str, message: str):
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
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="PrivateChats", ttl="1s")
        filtered_df = df[df["user_name"] == user_name]
        return filtered_df[["role", "message"]].fillna("")
    except Exception:
        return pd.DataFrame(columns=["role", "message"])

def add_event_to_pipeline(data: dict):
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="1s")
    except Exception:
        df = pd.DataFrame(columns=PIPELINE_COLUMNS)
        
    next_id = 1
    if not df.empty and "id" in df.columns:
        numeric_ids = pd.to_numeric(df["id"], errors="coerce").dropna()
        if not numeric_ids.empty:
            next_id = int(numeric_ids.max() + 1)
    
    new_row = pd.DataFrame([{
        "id": next_id,
        "event_name": data.get("event_name", ""),
        "location": data.get("location", ""),
        "event_date": data.get("event_date", ""),
        "product_format": data.get("product_format", "Both Hot & Frozen"),
        "participation_status": data.get("participation_status", "Discovered"),
        "decision_tier": data.get("decision_tier", ""),
        "gross_revenue": data.get("gross_revenue", 0.0),
        "total_expenses": data.get("total_expenses", 0.0),
        "net_profit": data.get("net_profit", 0.0),
        "roi_text": data.get("roi_text", ""),
        "prep_dumplings": data.get("prep_dumplings", 0),
        "notes": data.get("notes", "")
    }])
    
    updated_df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
    for c in PIPELINE_COLUMNS:
        if c not in updated_df.columns:
            updated_df[c] = ""
    conn.update(worksheet="Pipeline", data=updated_df[PIPELINE_COLUMNS])

def load_pipeline():
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="2s")
    except Exception:
        df = pd.DataFrame(columns=PIPELINE_COLUMNS)
        
    for col in PIPELINE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            
    return df.fillna("")[PIPELINE_COLUMNS]

def update_event_status_and_format(event_id: int, new_status: str, new_format: str):
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="1s")
        if not df.empty and "id" in df.columns:
            df["id"] = pd.to_numeric(df["id"], errors="coerce")
            idx = df[df["id"] == int(event_id)].index
            if not idx.empty:
                df.loc[idx, "participation_status"] = new_status
                df.loc[idx, "product_format"] = new_format
                conn.update(worksheet="Pipeline", data=df)
    except Exception as e:
        st.error(f"Failed to update event: {e}")
