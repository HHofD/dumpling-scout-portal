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
default_founders = st.sidebar.selectbox(
    "Default Founders on Shift (Unpaid)",
    [2, 1, 0],
    index=[2, 1, 0].index(int(saved_settings.get("founders_working", 2))),
    help="Default founder attendance. 2 = both founders ($0 labor up to 2 staff). 1 = 1 founder. 0 = all crew paid hourly."
)
val_frozen_pct_input = st.sidebar.number_input(
    "Frozen Sales % at Mixed Events (%)",
    min_value=0.0,
    max_value=100.0,
    value=float(saved_settings.get("frozen_upsell_pct", 25.0)),
    step=5.0
)
val_fulfillment = st.sidebar.number_input(
    "Fulfillment Time Target (min/order)",
    min_value=0.2,
    max_value=10.0,
    value=float(saved_settings.get("fulfillment_time_target", 1.5)),
    step=0.1,
    format="%.1f"
)

config = {
    "item_menu_price": val_price,
    "frozen_pack_price": val_frozen,
    "ingredient_cogs": val_cogs,
    "hourly_wage": val_wage,
    "founders_working": default_founders,
    "frozen_upsell_pct": val_frozen_pct_input / 100.0,
    "fulfillment_time_target": val_fulfillment
}

save_payload = {
    "item_menu_price": val_price,
    "frozen_pack_price": val_frozen,
    "ingredient_cogs": val_cogs,
    "hourly_wage": val_wage,
    "founders_working": default_founders,
    "frozen_upsell_pct": val_frozen_pct_input,
    "fulfillment_time_target": val_fulfillment
}

if st.sidebar.button("💾 Save Settings Permanently", use_container_width=True):
    if db.save_settings(save_payload):
        st.sidebar.success("Settings saved to Google Sheets!")

st.sidebar.caption("🍳 Griddle math: 24 dumplings / griddle every 12 mins. Founders on shift reduce paid crew costs.")

# =====================================================================
# PERSISTENT 4-TAB HORIZONTAL NAVIGATION
# =====================================================================
nav_tabs = [
    "👥 Shared Team Board", 
    "🤫 My Private AI Scout", 
    "📊 Opportunities Pipeline",
    "💸 Cost Breakdown"
]

if "active_tab_nav" not in st.session_state:
    st.session_state.active_tab_nav = nav_tabs[0]

active_tab = st.radio(
    "Navigation Tabs",
    nav_tabs,
    horizontal=True,
    label_visibility="collapsed",
    key="active_tab_nav"
)

# Helper parsing utilities
def safe_float(val, default):
    try:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return default
        return float(str(val).replace("$", "").replace(",", "").strip())
    except Exception:
        return default

def safe_int(val, default):
    try:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return default
        return int(float(str(val).replace(",", "").strip()))
    except Exception:
        return default

# --- TAB 1: SHARED TEAM BOARD ---
if active_tab == "👥 Shared Team Board":
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

# --- TAB 2: PRIVATE AI SCOUT ---
elif active_tab == "🤫 My Private AI Scout":
    st.subheader(f"🧠 Private Gemini Scout for {current_user}")
    st.caption("Your autonomous research & operations agent. Ask it to search events or bulk-add to pipeline.")
    private_df = db.load_private_messages(current_user)
    ai_box = st.container(height=380)
    with ai_box:
        if private_df.empty:
            st.info(f"Welcome {current_user}! Ask me to research events, or say: 'Find 3 events in Phoenix and add them to our pipeline'.")
        for _, row in private_df.iterrows():
            with st.chat_message(row["role"]):
                st.write(row["message"])
                
    ai_input = st.chat_input("Research events or ask AI to add them...", key="ai_scout_input")
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
        1. If user asks to ADD or SAVE events:
           Output a structured ACTION block at the end in this format:
           ```action_json
           {{
             "action": "bulk_add_events",
             "events": [
               {{
                 "event_name": "...",
                 "location": "...",
                 "event_date": "...",
                 "category": "Niche GF / Athletic" | "General Mass / Street Fair" | "Vegan / Wellness",
                 "product_format": "Both Hot & Frozen" | "Hot Cooked Only" | "Frozen Only",
                 "participation_status": "Discovered",
                 "estimated_attendance": 1000,
                 "operating_hours": 6.0,
                 "distance_from_tucson_miles": 115.0,
                 "vendor_fee_usd": 150.0,
                 "power_available": true
               }}
             ]
           }}
           ```

        2. If user asks to UPDATE an event:
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
           Answer thoroughly with web research and clear advice. Do NOT include action_json.
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
                
                if action_data.get("action") in ["bulk_add_events", "add_event"]:
                    events_to_add = action_data.get("events", [])
                    if not events_to_add and action_data.get("event_name"):
                        events_to_add = [action_data]
                        
                    added_summaries = []
                    for ev in events_to_add:
                        calc_input = {
                            "event_name": ev.get("event_name"),
                            "estimated_attendance": ev.get("estimated_attendance", 800),
                            "category": ev.get("category", "General Mass / Street Fair"),
                            "product_format": ev.get("product_format", "Both Hot & Frozen"),
                            "operating_hours": ev.get("operating_hours", 6.0),
                            "distance_from_tucson_miles": ev.get("distance_from_tucson_miles", 100.0),
                            "location": ev.get("location", "Arizona"),
                            "vendor_fee_usd": ev.get("vendor_fee_usd", 150.0),
                            "power_available": ev.get("power_available", True),
                            "founders_working": default_founders
                        }
                        finances = calculate_dumpling_finances(calc_input, config)
                        db.add_event_to_pipeline({
                            "event_name": ev.get("event_name"),
                            "location": ev.get("location"),
                            "event_date": ev.get("event_date"),
                            "category": ev.get("category"),
                            "product_format": ev.get("product_format"),
                            "participation_status": ev.get("participation_status", "Discovered"),
                            "est_attendance": ev.get("estimated_attendance"),
                            "operating_hours": ev.get("operating_hours", 6.0),
                            "distance_from_tucson_miles": ev.get("distance_from_tucson_miles", 100.0),
                            "vendor_fee_usd": ev.get("vendor_fee_usd", 150.0),
                            "power_available": ev.get("power_available", True),
                            "founders_working": default_founders,
                            "gross_revenue": finances["gross_revenue"],
                            "total_expenses": finances["total_expenses"],
                            "net_profit": finances["net_profit"],
                            "roi_text": finances["roi_text"],
                            "decision_tier": finances["decision_tier"],
                            "prep_dumplings": finances["prep_dumplings"],
                            "notes": f"Auto-added by {current_user} (Griddles: {finances['required_griddles']} | Paid Helpers: {finances['paid_helpers']})"
                        })
                        added_summaries.append(f"• **{ev.get('event_name')}** ({finances['decision_tier']} | Profit: **${finances['net_profit']:,.2f}**)")
                        
                    clean_reply += f"\n\n---\n✅ **Bulk Action Completed:** Saved **{len(added_summaries)} event(s)** directly into Google Sheets!\n" + "\n".join(added_summaries)
                    
                elif action_data.get("action") == "update_event":
                    ev_id = action_data.get("event_id")
                    st_val = action_data.get("new_status", "Applied")
                    fmt_val = action_data.get("new_format", "Both Hot & Frozen")
                    db.update_event_field(ev_id, {"participation_status": st_val, "status": st_val, "product_format": fmt_val})
                    clean_reply += f"\n\n---\n✅ **Action Completed:** Updated Event #{ev_id} to Status: **{st_val}** | Format: **{fmt_val}** in Google Sheets!"
            except Exception as e:
                clean_reply += f"\n\n*(Could not execute action: {e})*"

        db.save_private_message(current_user, "assistant", clean_reply)
        st.rerun()

    st.markdown("---")
    st.subheader("⚡ Quick Event Evaluator & Auto-Enrich")
    st.caption("Enter an event name or web link to let Gemini research missing details with full source citations.")
    
    if "prefill" not in st.session_state:
        st.session_state.prefill = {
            "name": "Scottsdale Celiac 5K + Treat", "loc": "Scottsdale, AZ", "date": "2026-11-01", "deadline": "2026-10-25",
            "dist": 115.0, "att": 800, "hours": 5.0, "fee": 150.0, "cat": "Niche GF / Athletic",
            "power": False, "is_ai": False, "source_url": "", "source_summary": ""
        }

    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        quick_query = st.text_input("Event Name or Web Link to Research", placeholder="e.g., Bisbee Pirate Weekend or Tempe Festival of the Arts")
    with col_s2:
        st.write("")
        st.write("")
        if st.button("🔍 Auto-Fill with AI", use_container_width=True):
            if quick_query:
                with st.spinner("Gemini is searching web records for event details and sources..."):
                    api_k = get_gemini_api_key()
                    client = genai.Client(api_key=api_k)
                    enrich_prompt = f"""
                    Search web for event details: '{quick_query}'. Business: Huhu's House of Dumplings (gluten-free vegan food in Tucson, AZ).
                    Extract clean JSON:
                    - event_name (string)
                    - location (City, State)
                    - event_date (YYYY-MM-DD or date string)
                    - application_deadline (YYYY-MM-DD string, or 30 days before event)
                    - distance_from_tucson_miles (float driving estimate from Tucson, AZ)
                    - estimated_attendance (integer estimate)
                    - operating_hours (float daily hours, default 6.0)
                    - vendor_fee_usd (float estimate, default 150.0)
                    - category ('Niche GF / Athletic', 'General Mass / Street Fair', 'Vegan / Wellness')
                    - power_available (boolean)
                    - primary_source_url (string URL)
                    - source_summary (1-sentence summary of verification source)
                    """
                    try:
                        res = client.models.generate_content(
                            model='gemini-3.8-flash',
                            contents=enrich_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                tools=[types.Tool(google_search=types.GoogleSearch())]
                            )
                        )
                        data = json.loads(res.text)
                        st.session_state.prefill = {
                            "name": data.get("event_name", quick_query),
                            "loc": data.get("location", "Arizona"),
                            "date": str(data.get("event_date", "2026-11-01")),
                            "deadline": str(data.get("application_deadline", "2026-10-25")),
                            "dist": float(data.get("distance_from_tucson_miles", 100.0)),
                            "att": int(data.get("estimated_attendance", 1000)),
                            "hours": float(data.get("operating_hours", 6.0)),
                            "fee": float(data.get("vendor_fee_usd", 150.0)),
                            "cat": data.get("category", "General Mass / Street Fair"),
                            "power": bool(data.get("power_available", True)),
                            "is_ai": True,
                            "source_url": data.get("primary_source_url", ""),
                            "source_summary": data.get("source_summary", "Extracted via Google Grounded Search")
                        }
                        st.rerun()
                    except Exception as err:
                        st.error(f"Auto-fill error: {err}")

    if st.session_state.prefill.get("is_ai"):
        src_link = st.session_state.prefill.get("source_url", "")
        src_text = f" [🔗 Open Source Webpage]({src_link})" if src_link else ""
        st.info(f"🤖 **AI Auto-Enriched Data**: {st.session_state.prefill.get('source_summary', '')}{src_text}\n\n*Highlighted fields below were extracted by Gemini. Adjust values as needed before saving.*")

    with st.form("quick_eval_form"):
        ai_tag = " 🤖 [AI]" if st.session_state.prefill.get("is_ai") else ""
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            e_name = st.text_input(f"Event Name{ai_tag}", value=st.session_state.prefill["name"])
            e_loc = st.text_input(f"Location{ai_tag}", value=st.session_state.prefill["loc"])
            e_date = st.text_input(f"Event Date{ai_tag}", value=st.session_state.prefill["date"])
            e_deadline = st.text_input(f"App Deadline{ai_tag}", value=st.session_state.prefill.get("deadline", "2026-10-25"))
        with col_b:
            e_dist = st.number_input(f"Distance from Tucson (miles){ai_tag}", value=st.session_state.prefill["dist"], step=5.0)
            e_att = st.number_input(f"Estimated Attendance{ai_tag}", value=st.session_state.prefill["att"], step=50)
            e_hours = st.number_input(f"Operating Hours{ai_tag}", value=st.session_state.prefill["hours"], step=0.5)
            e_founders_on_shift = st.selectbox("Founders on Shift (Unpaid)", [2, 1, 0], index=[2, 1, 0].index(default_founders))
        with col_c:
            cats = ["Niche GF / Athletic", "General Mass / Street Fair", "Vegan / Wellness"]
            idx = cats.index(st.session_state.prefill["cat"]) if st.session_state.prefill["cat"] in cats else 1
            e_cat = st.selectbox(f"Category{ai_tag}", cats, index=idx)
            e_format = st.selectbox("Product Format", ["Both Hot & Frozen", "Hot Cooked Only", "Frozen Only"])
            e_status = st.selectbox("Participation Status", ["Discovered", "Already Participating", "Booked", "Applied", "Reviewing"])
            e_fee = st.number_input(f"Vendor Booth Fee ($){ai_tag}", value=st.session_state.prefill["fee"], step=25.0)
            e_power = st.checkbox(f"Power & Water Provided{ai_tag}", value=st.session_state.prefill["power"])
            
        submit_btn = st.form_submit_button("Run Financial Evaluation & Log to Pipeline")
        if submit_btn:
            calc_input = {
                "event_name": e_name,
                "estimated_attendance": e_att,
                "category": e_cat,
                "product_format": e_format,
                "operating_hours": e_hours,
                "distance_from_tucson_miles": e_dist,
                "location": e_loc,
                "vendor_fee_usd": e_fee,
                "power_available": e_power,
                "founders_working": e_founders_on_shift
            }
            results = calculate_dumpling_finances(calc_input, config)
            db.add_event_to_pipeline({
                "event_name": e_name, "location": e_loc, "event_date": e_date,
                "category": e_cat, "product_format": e_format, "participation_status": e_status,
                "est_attendance": e_att, "operating_hours": e_hours,
                "distance_from_tucson_miles": e_dist, "vendor_fee_usd": e_fee, "power_available": e_power,
                "founders_working": e_founders_on_shift,
                "gross_revenue": results["gross_revenue"], "total_expenses": results["total_expenses"],
                "net_profit": results["net_profit"], "roi_text": results["roi_text"],
                "decision_tier": results["decision_tier"], "prep_dumplings": results["prep_dumplings"],
                "notes": f"Added by {current_user} (Griddles: {results['required_griddles']} | Paid Helpers: {results['paid_helpers']}) | Deadline: {e_deadline}"
            })
            st.success(f"Calculated: {results['decision_tier']} with Projected Net Profit of ${results['net_profit']:,.2f}! Saved to Tab 3.")

# --- TAB 3: PIPELINE OVERVIEW ---
elif active_tab == "📊 Opportunities Pipeline":
    st.subheader("📋 Active Opportunities Pipeline")
    
    with st.expander("ℹ️ How are Tiers calculated? (Click to view breakdown)", expanded=False):
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.markdown("### 🟢 Tier 1: Green Light")
            st.markdown(
                "**Net Profit $\ge$ $1,100 & ROI $\ge$ 75%**\n\n"
                "**Action:** High-priority booking. Highly lucrative events that easily absorb travel and lodging overhead with strong returns."
            )
        with col_t2:
            st.markdown("### 🟡 Tier 2: Tactical Fill-In")
            st.markdown(
                "**Net Profit $\ge$ $450 & Distance $\le$ 140 miles**\n\n"
                "**Action:** Profitable local day trip. Great for keeping weekend kitchen production active without overnight hotel costs."
            )
        with col_t3:
            st.markdown("### 🔴 Tier 3: Pass / Archive")
            st.markdown(
                "**Net Profit $<$ $450 or Negative ROI**\n\n"
                "**Action:** Low-margin or high-risk. Booth fees, wages, or travel drag exceed addressable customer demand. Pass on booking."
            )

    pipeline_df = db.load_pipeline()
    display_rows = []
    
    if not pipeline_df.empty and "event_name" in pipeline_df.columns:
        for _, row in pipeline_df.iterrows():
            ev_name = str(row.get("event_name", "")).strip()
            if ev_name:
                att_val = safe_float(row.get("estimated_attendance"), 800.0)
                hrs_val = max(1.0, safe_float(row.get("operating_hours"), 6.0))
                dist_val = safe_float(row.get("distance_from_tucson_miles"), 100.0)
                fee_val = safe_float(row.get("vendor_fee_usd"), 150.0)
                cat_val = str(row.get("category") or "General Mass / Street Fair")
                fmt_val = str(row.get("product_format") or "Both Hot & Frozen")
                loc_val = str(row.get("location") or "Arizona")
                pwr_val = True if str(row.get("power_available", "True")).lower() in ["true", "1", "yes"] else False
                
                event_founders = safe_int(row.get("founders_working"), default_founders)
                if event_founders not in [0, 1, 2]:
                    event_founders = default_founders
                
                try:
                    recalc_input = {
                        "event_name": ev_name,
                        "estimated_attendance": att_val,
                        "category": cat_val,
                        "product_format": fmt_val,
                        "operating_hours": hrs_val,
                        "distance_from_tucson_miles": dist_val,
                        "location": loc_val,
                        "vendor_fee_usd": fee_val,
                        "power_available": pwr_val,
                        "founders_working": event_founders
                    }
                    live_fin = calculate_dumpling_finances(recalc_input, config)
                    
                    rev_str = f"${live_fin['gross_revenue']:,.2f}"
                    cost_str = f"${live_fin['total_expenses']:,.2f}"
                    prof_str = f"${live_fin['net_profit']:,.2f}"
                    roi_str = live_fin['roi_text']
                    
                    tier_raw = live_fin['decision_tier']
                    if "Tier 1" in tier_raw:
                        tier_display = "🟢 Tier 1: Green Light"
                    elif "Tier 2" in tier_raw:
                        tier_display = "🟡 Tier 2: Fill-In"
                    else:
                        tier_display = "🔴 Tier 3: Pass"
                        
                    tgt_str = f"{live_fin['prep_dumplings']:,}"
                    grid_str = f"{live_fin['required_griddles']} pcs"
                except Exception as e:
                    rev_str = str(row.get("gross_revenue", "$0.00"))
                    cost_str = str(row.get("total_expenses", "$0.00"))
                    prof_str = str(row.get("net_profit", "$0.00"))
                    roi_str = str(row.get("roi_text", "0%"))
                    tier_display = "🔴 Tier 3: Pass"
                    tgt_str = str(row.get("prep_dumplings", "0"))
                    grid_str = "2 pcs"

                display_rows.append({
                    "ID": str(row.get("id", "")),
                    "Event Name": ev_name,
                    "Location": loc_val,
                    "Date": str(row.get("event_date", "")),
                    "Crowd": f"{int(att_val):,}",
                    "Griddles": grid_str,
                    "Founders": str(event_founders),
                    "Format": fmt_val,
                    "Status": str(row.get("participation_status", "Discovered")),
                    "Tier": tier_display,
                    "Revenue": rev_str,
                    "Costs": cost_str,
                    "Profit": prof_str,
                    "ROI": roi_str,
                    "Target (pcs)": tgt_str,
                    "Notes": str(row.get("notes", ""))
                })

    final_table = pd.DataFrame(display_rows)
    
    if final_table.empty:
        final_table = pd.DataFrame(columns=[
            "ID", "Event Name", "Location", "Date", "Crowd", "Griddles", "Founders", "Format", "Status",
            "Tier", "Revenue", "Costs", "Profit", "ROI", "Target (pcs)", "Notes"
        ])

    st.caption("📊 Overview Grid • Double-click Founders, Format, or Status to edit directly!")
    
    edited_df = st.data_editor(
        final_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", width=60, disabled=True),
            "Event Name": st.column_config.TextColumn("Event Name", width=220),
            "Location": st.column_config.TextColumn("Location", width=115),
            "Date": st.column_config.TextColumn("Date", width=105),
            "Crowd": st.column_config.TextColumn("Crowd", width=80),
            "Griddles": st.column_config.TextColumn("Griddles", width=80, disabled=True),
            "Founders": st.column_config.SelectboxColumn("Founders", width=95, options=["2", "1", "0"]),
            "Format": st.column_config.SelectboxColumn("Format", width=140, options=["Both Hot & Frozen", "Hot Cooked Only", "Frozen Only"]),
            "Status": st.column_config.SelectboxColumn("Status", width=145, options=["Discovered", "Already Participating", "Booked", "Applied", "Reviewing", "Completed", "Declined"]),
            "Tier": st.column_config.TextColumn("Tier", width=155, disabled=True),
            "Revenue": st.column_config.TextColumn("Revenue", width=95, disabled=True),
            "Costs": st.column_config.TextColumn("Costs", width=95, disabled=True),
            "Profit": st.column_config.TextColumn("Profit", width=95, disabled=True),
            "ROI": st.column_config.TextColumn("ROI", width=75, disabled=True),
            "Target (pcs)": st.column_config.TextColumn("Target (pcs)", width=95, disabled=True),
            "Notes": st.column_config.TextColumn("Notes", width=240)
        },
        key="pipeline_editor"
    )
    
    if st.session_state.get("pipeline_editor") and "edited_rows" in st.session_state.pipeline_editor:
        changes = st.session_state.pipeline_editor["edited_rows"]
        if changes:
            for row_idx, updated_cols in changes.items():
                try:
                    target_id = int(float(str(final_table.iloc[int(row_idx)]["ID"]).strip()))
                    fields_to_update = {}
                    
                    if "Founders" in updated_cols:
                        fields_to_update["founders_working"] = int(float(str(updated_cols["Founders"]).strip()))
                    if "Status" in updated_cols:
                        fields_to_update["participation_status"] = str(updated_cols["Status"]).strip()
                        fields_to_update["status"] = str(updated_cols["Status"]).strip()
                    if "Format" in updated_cols:
                        fields_to_update["product_format"] = str(updated_cols["Format"]).strip()
                    
                    if fields_to_update:
                        db.update_event_field(target_id, fields_to_update)
                        st.success(f"Saved edits for Event #{target_id} to Google Sheets!")
                        st.rerun()
                except Exception as err:
                    st.error(f"Failed to save in-line edits: {err}")

# =====================================================================
# TAB 4: DEDICATED COST BREAKDOWN & EDITABLE EXPENSE LEDGER
# =====================================================================
elif active_tab == "💸 Cost Breakdown":
    st.subheader("💸 Operational Cost Breakdown & Expense Ledger")
    st.caption("Itemized expense ledger per event. Double-click any cost cell to override with exact receipts or custom fees!")
    
    pipeline_df = db.load_pipeline()
    cost_rows = []
    
    if not pipeline_df.empty and "event_name" in pipeline_df.columns:
        for _, row in pipeline_df.iterrows():
            ev_name = str(row.get("event_name", "")).strip()
            if ev_name:
                att_val = safe_float(row.get("estimated_attendance"), 800.0)
                hrs_val = max(1.0, safe_float(row.get("operating_hours"), 6.0))
                dist_val = safe_float(row.get("distance_from_tucson_miles"), 100.0)
                fee_val = safe_float(row.get("vendor_fee_usd"), 150.0)
                cat_val = str(row.get("category") or "General Mass / Street Fair")
                fmt_val = str(row.get("product_format") or "Both Hot & Frozen")
                loc_val = str(row.get("location") or "Arizona")
                pwr_val = True if str(row.get("power_available", "True")).lower() in ["true", "1", "yes"] else False
                event_founders = safe_int(row.get("founders_working"), default_founders)
                
                # Calculate detailed cost categories
                calc_input = {
                    "event_name": ev_name,
                    "estimated_attendance": att_val,
                    "category": cat_val,
                    "product_format": fmt_val,
                    "operating_hours": hrs_val,
                    "distance_from_tucson_miles": dist_val,
                    "location": loc_val,
                    "vendor_fee_usd": fee_val,
                    "power_available": pwr_val,
                    "founders_working": event_founders
                }
                live_fin = calculate_dumpling_finances(calc_input, config)
                
                # Granular cost mathematics
                dumplings_count = live_fin.get("prep_dumplings", 0)
                food_cogs = round(dumplings_count * config["ingredient_cogs"], 2)
                
                # Packaging split (safe from KeyError)
                frozen_pct = float(config.get("frozen_upsell_pct", 0.25))
                proj_cust = live_fin.get("projected_customers", 100)
                
                if fmt_val == "Frozen Only":
                    packaging = round(proj_cust * 0.50, 2)
                elif fmt_val == "Hot Cooked Only":
                    packaging = round(proj_cust * 0.75, 2)
                else:
                    hot_c = round(proj_cust * (1.0 - frozen_pct))
                    froz_c = round(proj_cust * frozen_pct)
                    packaging = round((hot_c * 0.75) + (froz_c * 0.50), 2)

                    
                # Labor expenses (safe lookup with fallback)
                tot_staff = live_fin.get("total_staff", 2)
                paid_helpers = live_fin.get("paid_helpers", max(0, tot_staff - event_founders))
                transit_hrs = (dist_val / 55.0) * 2.0
                labor_cost = round(paid_helpers * (hrs_val + 1.5 + transit_hrs) * config["hourly_wage"], 2)

                
                # Travel & Lodging
                mileage_cost = round(dist_val * 2.0 * 0.35, 2)
                lodging_cost = 220.00 if dist_val > 180 else 0.00
                
                # Permits
                loc_lower = loc_val.lower()
                permit_fee = 0.00 if dist_val <= 50 else (200.00 if "maricopa" in loc_lower or "phoenix" in loc_lower or "scottsdale" in loc_lower else 150.00)
                booth_fee = round(fee_val, 2)
                utility_fee = 40.00 if (not pwr_val and fmt_val != "Frozen Only") else 0.00
                
                total_cost = round(food_cogs + packaging + labor_cost + mileage_cost + lodging_cost + permit_fee + booth_fee + utility_fee, 2)
                
                cost_rows.append({
                    "ID": str(row.get("id", "")),
                    "Event Name": ev_name,
                    "Food COGS ($)": float(food_cogs),
                    "Packaging ($)": float(packaging),
                    "Crew Labor ($)": float(labor_cost),
                    "Mileage ($)": float(mileage_cost),
                    "Lodging ($)": float(lodging_cost),
                    "Permit ($)": float(permit_fee),
                    "Booth Fee ($)": float(booth_fee),
                    "Utilities ($)": float(utility_fee),
                    "Total Costs ($)": float(total_cost)
                })

    cost_df = pd.DataFrame(cost_rows)
    
    if cost_df.empty:
        cost_df = pd.DataFrame(columns=[
            "ID", "Event Name", "Food COGS ($)", "Packaging ($)", "Crew Labor ($)",
            "Mileage ($)", "Lodging ($)", "Permit ($)", "Booth Fee ($)", "Utilities ($)", "Total Costs ($)"
        ])
        st.info("The pipeline is empty. Add events via Tab 2 to populate cost breakdowns.")
    else:
        edited_cost_df = st.data_editor(
            cost_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", width=60, disabled=True),
                "Event Name": st.column_config.TextColumn("Event Name", width=220, disabled=True),
                "Food COGS ($)": st.column_config.NumberColumn("Food COGS ($)", format="$%.2f", width=110),
                "Packaging ($)": st.column_config.NumberColumn("Packaging ($)", format="$%.2f", width=110),
                "Crew Labor ($)": st.column_config.NumberColumn("Crew Labor ($)", format="$%.2f", width=110),
                "Mileage ($)": st.column_config.NumberColumn("Mileage ($)", format="$%.2f", width=105),
                "Lodging ($)": st.column_config.NumberColumn("Lodging ($)", format="$%.2f", width=105),
                "Permit ($)": st.column_config.NumberColumn("Permit ($)", format="$%.2f", width=105),
                "Booth Fee ($)": st.column_config.NumberColumn("Booth Fee ($)", format="$%.2f", width=110),
                "Utilities ($)": st.column_config.NumberColumn("Utilities ($)", format="$%.2f", width=105),
                "Total Costs ($)": st.column_config.NumberColumn("Total Costs ($)", format="$%.2f", width=120, disabled=True)
            },
            key="cost_breakdown_editor"
        )
        
        # Save cost overrides back to Google Sheets!
        if st.session_state.get("cost_breakdown_editor") and "edited_rows" in st.session_state.cost_breakdown_editor:
            cost_changes = st.session_state.cost_breakdown_editor["edited_rows"]
            if cost_changes:
                for row_idx, updated_costs in cost_changes.items():
                    try:
                        target_id = int(float(str(cost_df.iloc[int(row_idx)]["ID"]).strip()))
                        fields_to_sync = {}
                        if "Booth Fee ($)" in updated_costs:
                            fields_to_sync["vendor_fee_usd"] = float(updated_costs["Booth Fee ($)"])
                            
                        if fields_to_sync:
                            db.update_event_field(target_id, fields_to_sync)
                            st.success(f"Saved custom cost override for Event #{target_id} to Google Sheets!")
                            st.rerun()
                    except Exception as err:
                        st.error(f"Failed to save cost edit: {err}")
