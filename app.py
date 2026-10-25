import streamlit as st

st.set_page_config(page_title="Huhu's Dumpling Scout Hub", layout="wide", page_icon="🥟")

import extra_streamlit_components as stx
import datetime
import time
import pandas as pd
import json
from google import genai
from google.genai import types

def get_cookie_manager():
    return stx.CookieManager()

def get_gemini_api_key():
    key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    if key and str(key).strip():
        return str(key).strip()
    for section in ["users", "connections"]:
        if section in st.secrets and isinstance(st.secrets[section], dict):
            if "GEMINI_API_KEY" in st.secrets[section]:
                return str(st.secrets[section]["GEMINI_API_KEY"]).strip()
    st.error("Gemini API Key missing from Secrets config.")
    return ""

def authenticate_user():
    cookie_manager = get_cookie_manager()
    
    if "authenticated_user" in st.session_state and st.session_state.authenticated_user:
        return st.session_state.authenticated_user

    saved_user = cookie_manager.get("huhu_auth_user")
    if saved_user:
        st.session_state.authenticated_user = saved_user
        return saved_user

    st.markdown("<h1 style='text-align: center; color: #E74C3C;'>🥟 Huhu's Command Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Private Scouting & Operations Hub</p>", unsafe_allow_html=True)
    st.write("")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username_input = st.text_input("Username").strip().lower()
        password_input = st.text_input("Password", type="password").strip()
        login_btn = st.button("Log In", use_container_width=True)

        if login_btn:
            default_users = {
                "andrew": "AndrewDumplings2026",
                "whitney": "WhitneyDumplings2026"
            }
            users_db = st.secrets.get("users", default_users)

            if username_input in users_db and password_input == users_db[username_input]:
                display_name = username_input.capitalize()
                st.session_state.authenticated_user = display_name
                expires = datetime.datetime.now() + datetime.timedelta(days=1)
                cookie_manager.set("huhu_auth_user", display_name, expires_at=expires)
                time.sleep(0.2)
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

    return None

current_user = authenticate_user()
if not current_user:
    st.stop()

import database as db
from engine import calculate_dumpling_finances

db.initialize_database()

# Load persistent settings directly from Google Sheets
saved_settings = db.load_settings()

st.sidebar.title(f"👤 Logged in as: {current_user}")
if st.sidebar.button("Log Out"):
    cookie_mgr = stx.CookieManager()
    cookie_mgr.delete("huhu_auth_user")
    time.sleep(0.2)
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Operational Economics")

val_price = st.sidebar.number_input(
    "Average Menu Item Price ($)",
    value=float(saved_settings.get("item_menu_price", 12.0)),
    step=0.5,
    help="Price per 4-dumpling serving"
)
val_frozen = st.sidebar.number_input(
    "Frozen 4-Pack Price ($)",
    value=float(saved_settings.get("frozen_pack_price", 16.0)),
    step=0.5
)
val_cogs = st.sidebar.number_input(
    "Raw Ingredient Cost / Dumpling ($)",
    value=float(saved_settings.get("ingredient_cogs", 0.42)),
    step=0.01,
    format="%.2f"
)
val_wage = st.sidebar.number_input(
    "Staff Hourly Wage ($)",
    value=float(saved_settings.get("hourly_wage", 20.0)),
    step=1.0
)
val_frozen_pct_input = st.sidebar.number_input(
    "Frozen Sales % at Mixed Events (%)",
    min_value=0.0,
    max_value=100.0,
    value=float(saved_settings.get("frozen_upsell_pct", 25.0)),
    step=5.0,
    help="Type e.g. 25 for 25% of customers buying frozen packs at 'Both Hot & Frozen' events"
)
val_fulfillment = st.sidebar.number_input(
    "Fulfillment Time Target (min/order)",
    min_value=0.2,
    max_value=10.0,
    value=float(saved_settings.get("fulfillment_time_target", 1.5)),
    step=0.1,
    format="%.1f",
    help="Desired checkout-to-handout window. App calculates required griddles."
)

config = {
    "item_menu_price": val_price,
    "frozen_pack_price": val_frozen,
    "ingredient_cogs": val_cogs,
    "hourly_wage": val_wage,
    "frozen_upsell_pct": val_frozen_pct_input / 100.0,
    "fulfillment_time_target": val_fulfillment
}

save_payload = {
    "item_menu_price": val_price,
    "frozen_pack_price": val_frozen,
    "ingredient_cogs": val_cogs,
    "hourly_wage": val_wage,
    "frozen_upsell_pct": val_frozen_pct_input,
    "fulfillment_time_target": val_fulfillment
}

if st.sidebar.button("💾 Save Settings Permanently", use_container_width=True):
    if db.save_settings(save_payload):
        st.sidebar.success("Settings saved to Google Sheets!")

st.sidebar.caption("🍳 Griddle math: 24 dumplings / griddle every 12 mins. 1 cook handles up to 3 griddles; 4+ griddles requires 2 cooks.")

tab_shared, tab_private, tab_pipeline = st.tabs([
    "👥 Shared Team Board", 
    "🤫 My Private AI Scout", 
    "📊 Opportunities Pipeline"
])

with tab_shared:
    st.subheader("💬 Team Collaboration Lounge")
    st.caption("Shared workspace for Andrew and Whitney to coordinate dates and batch schedules.")
    team_df = db.load_team_messages()
    chat_box = st.container(height=380)
    with chat_box:
        if team_df.empty:
            st.info("No messages posted yet. Start the conversation below!")
        for _, row in team_df.iterrows():
            with st.chat_message(row["user_name"]):
                st.markdown(f"**{row['user_name']}** `{row['timestamp']}`\n\n{row['message']}")
                
    team_input = st.chat_input("Write a message to the team...", key="team_chat_input")
    if team_input:
        db.save_team_message(current_user, team_input)
        st.rerun()

with tab_private:
    st.subheader(f"🧠 Private Gemini Scout for {current_user}")
    st.caption("Your autonomous research & operations agent. Ask it to search events or manage your pipeline.")
    private_df = db.load_private_messages(current_user)
    ai_box = st.container(height=380)
    with ai_box:
        if private_df.empty:
            st.info(f"Welcome {current_user}! Ask me to research events, or say: 'Add Tucson Meet Yourself to pipeline', or 'Mark event #2 as Applied'.")
        for _, row in private_df.iterrows():
            with st.chat_message(row["role"]):
                st.write(row["message"])
                
    ai_input = st.chat_input("Research an event, or tell me to add/edit the pipeline...", key="ai_scout_input")
    if ai_input:
        db.save_private_message(current_user, "user", ai_input)
        api_k = get_gemini_api_key()
        client = genai.Client(api_key=api_k)
        
        current_pipeline = db.load_pipeline()
        pipeline_summary = ""
        if not current_pipeline.empty and "event_name" in current_pipeline.columns:
            pipeline_summary = current_pipeline[["id", "event_name", "location", "event_date", "participation_status", "product_format"]].to_string(index=False)

        prompt = f"""
        You are the autonomous operations & event scout for Huhu's House of Dumplings (gluten-free, vegan dumplings based in Tucson, AZ).
        Current active user: {current_user}
        User instruction: '{ai_input}'

        Current Pipeline Database:
        {pipeline_summary if pipeline_summary else "No events in pipeline yet."}

        CAPABILITIES:
        1. If user asks to ADD or SAVE an event:
           Output a structured ACTION block at the end of your reply in this exact JSON format:
           ```action_json
           {{
             "action": "add_event",
             "event_name": "...",
             "location": "...",
             "event_date": "...",
             "category": "Niche GF / Athletic" | "General Mass / Street Fair" | "Vegan / Wellness",
             "product_format": "Both Hot & Frozen" | "Hot Cooked Only" | "Frozen Only",
             "participation_status": "Discovered" | "Already Participating" | "Booked" | "Applied" | "Reviewing",
             "estimated_attendance": 1000,
             "operating_hours": 6.0,
             "distance_from_tucson_miles": 115.0,
             "vendor_fee_usd": 150.0,
             "power_available": true
           }}
           ```

        2. If user asks to UPDATE or EDIT an existing event:
           Output a structured ACTION block:
           ```action_json
           {{
             "action": "update_event",
             "event_id": 1,
             "new_status": "Booked" | "Applied" | "Reviewing" | "Completed" | "Declined" | "Already Participating",
             "new_format": "Both Hot & Frozen" | "Hot Cooked Only" | "Frozen Only"
           }}
           ```

        3. If researching:
           Answer thoroughly with web research and clear advice. Do NOT include an action_json block.
        """
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        raw_reply = response.text
        clean_reply = raw_reply
        
        if "```action_json" in raw_reply:
            try:
                json_part = raw_reply.split("```action_json")[1].split("```")[0].strip()
                action_data = json.loads(json_part)
                clean_reply = raw_reply.split("```action_json")[0].strip()
                
                if action_data.get("action") == "add_event":
                    calc_input = {
                        "estimated_attendance": action_data.get("estimated_attendance", 800),
                        "category": action_data.get("category", "General Mass / Street Fair"),
                        "product_format": action_data.get("product_format", "Both Hot & Frozen"),
                        "operating_hours": action_data.get("operating_hours", 6.0),
                        "distance_from_tucson_miles": action_data.get("distance_from_tucson_miles", 100.0),
                        "location": action_data.get("location", "Arizona"),
                        "vendor_fee_usd": action_data.get("vendor_fee_usd", 150.0),
                        "power_available": action_data.get("power_available", True)
                    }
                    finances = calculate_dumpling_finances(calc_input, config)
                    db.add_event_to_pipeline({
                        "event_name": action_data.get("event_name"),
                        "location": action_data.get("location"),
                        "event_date": action_data.get("event_date"),
                        "category": action_data.get("category"),
                        "product_format": action_data.get("product_format"),
                        "participation_status": action_data.get("participation_status", "Discovered"),
                        "est_attendance": action_data.get("estimated_attendance"),
                        "operating_hours": action_data.get("operating_hours", 6.0),
                        "distance_from_tucson_miles": action_data.get("distance_from_tucson_miles", 100.0),
                        "vendor_fee_usd": action_data.get("vendor_fee_usd", 150.0),
                        "power_available": action_data.get("power_available", True),
                        "gross_revenue": finances["gross_revenue"],
                        "total_expenses": finances["total_expenses"],
                        "net_profit": finances["net_profit"],
                        "roi_text": finances["roi_text"],
                        "decision_tier": finances["decision_tier"],
                        "prep_dumplings": finances["prep_dumplings"],
                        "notes": f"Added via AI Chat by {current_user} (Griddles: {finances['required_griddles']})"
                    })
     
