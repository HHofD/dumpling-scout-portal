import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

PIPELINE_COLUMNS = [
    "id", "event_name", "location", "event_date", "product_format",
    "participation_status", "decision_tier", "gross_revenue",
    "total_expenses", "net_profit", "roi_text", "prep_dumplings", "notes",
    "estimated_attendance", "operating_hours", "num_griddles",
    "distance_from_tucson_miles", "vendor_fee_usd", "power_available", "category",
    "founders_working"
]

DEFAULT_SETTINGS = {
    "item_menu_price": 12.0,
    "frozen_pack_price": 16.0,
    "ingredient_cogs": 0.42,
    "hourly_wage": 20.0,
    "founders_working": 2,
    "frozen_upsell_pct": 25.0,
    "fulfillment_time_target": 1.5
}

def get_gsheets_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def initialize_database():
    pass

def load_settings():
    conn = get_gsheets_connection()
    result = DEFAULT_SETTINGS.copy()
    try:
        df = conn.read(worksheet="Settings", ttl="0s")
        if not df.empty and "setting_key" in df.columns and "setting_value" in df.columns:
            for _, r in df.iterrows():
                k = str(r["setting_key"]).strip().lower()
                v_raw = str(r["setting_value"]).replace("$", "").replace("%", "").replace(",", "").strip()
                try:
                    v = float(v_raw)
                    for def_k in result.keys():
                        if def_k.lower() == k:
                            if def_k == "frozen_upsell_pct" and v <= 1.0 and v > 0:
                                v = v * 100.0
                            result[def_k] = v
                except Exception:
                    continue
    except Exception:
        pass
    return result

def save_settings(new_settings: dict):
    conn = get_gsheets_connection()
    try:
        rows = []
        for k, v in new_settings.items():
            rows.append({"setting_key": str(k), "setting_value": float(v)})
        df = pd.DataFrame(rows)
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
  
