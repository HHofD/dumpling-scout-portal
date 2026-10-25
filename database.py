import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

PIPELINE_COLUMNS = [
    "id", "event_name", "location", "event_date", "product_format",
    "participation_status", "decision_tier", "gross_revenue",
    "total_expenses", "net_profit", "roi_text", "prep_dumplings", "notes",
    "estimated_attendance", "operating_hours", "num_griddles",
    "distance_from_tucson_miles", "vendor_fee_usd", "power_available", "category"
]

DEFAULT_SETTINGS = {
    "item_menu_price": 12.0,
    "frozen_pack_price": 16.0,
    "ingredient_cogs": 0.42,
    "hourly_wage": 20.0,
    "frozen_upsell_pct": 0.25,
    "fulfillment_time_target": 1.5
}

def get_gsheets_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def initialize_database():
    pass

def load_settings():
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Settings", ttl="30s")
        if not df.empty and "setting_key" in df.columns and "setting_value" in df.columns:
            settings_dict = dict(zip(df["setting_key"].astype(str), pd.to_numeric(df["setting_value"], errors="coerce")))
            result = DEFAULT_SETTINGS.copy()
            for k, v in settings_dict.items():
                if k in result and pd.notna(v):
                    result[k] = float(v)
            return result
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()

def save_settings(new_settings: dict):
    conn = get_gsheets_connection()
    try:
        df = pd.DataFrame([
            {"setting_key": k, "setting_value": float(v)}
            for k, v in new_settings.items()
        ])
        conn.update(worksheet="Settings", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save settings to Google Sheets: {e}")
        return False

def save_team_message(user_name: str, message: str):
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="TeamChat", ttl="30s")
    except Exception:
        df = pd.DataFrame(columns=["user_name", "message", "timestamp"])
        
    new_row = pd.DataFrame([{
        "user_name": user_name,
        "message": message,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="TeamChat", data=updated_df)
    st.cache_data.clear()

def load_team_messages():
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="TeamChat", ttl="30s")
        return df.fillna("")
    except Exception:
        return pd.DataFrame(columns=["user_name", "message", "timestamp"])

def save_private_message(user_name: str, role: str, message: str):
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="PrivateChats", ttl="30s")
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
        df = conn.read(worksheet="PrivateChats", ttl="30s")
        filtered_df = df[df["user_name"] == user_name]
        return filtered_df[["role", "message"]].fillna("")
    except Exception:
        return pd.DataFrame(columns=["role", "message"])

def add_event_to_pipeline(data: dict):
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="10s")
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
        "notes": data.get("notes", ""),
        "estimated_attendance": data.get("est_attendance", 500),
        "operating_hours": data.get("operating_hours", 6.0),
        "num_griddles": data.get("num_griddles", 2),
        "distance_from_tucson_miles": data.get("distance_from_tucson_miles", 100.0),
        "vendor_fee_usd": data.get("vendor_fee_usd", 150.0),
        "power_available": data.get("power_available", True),
        "category": data.get("category", "General Mass / Street Fair")
    }])
    
    updated_df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
    for c in PIPELINE_COLUMNS:
        if c not in updated_df.columns:
            updated_df[c] = ""
    conn.update(worksheet="Pipeline", data=updated_df[PIPELINE_COLUMNS])

def load_pipeline():
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="60s")
    except Exception:
        df = pd.DataFrame(columns=PIPELINE_COLUMNS)
        
    for col in PIPELINE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            
    return df.fillna("")[PIPELINE_COLUMNS]

def update_event_status_and_format(event_id: int, new_status: str, new_format: str):
    conn = get_gsheets_connection()
    try:
        df = conn.read(worksheet="Pipeline", ttl="5s")
        if not df.empty and "id" in df.columns:
            df["id"] = pd.to_numeric(df["id"], errors="coerce")
            idx = df[df["id"] == int(event_id)].index
            if not idx.empty:
                df.loc[idx, "participation_status"] = new_status
                df.loc[idx, "product_format"] = new_format
                conn.update(worksheet="Pipeline", data=df)
    except Exception as e:
        st.error(f"Failed to update event: {e}")
