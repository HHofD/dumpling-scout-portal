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
                        "event_name": action_data.get("event_name"),
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
                    clean_reply += f"\n\n---\n✅ **Action Completed:** Saved **'{action_data.get('event_name')}'** to Google Sheets! (Net Profit: **${finances['net_profit']:,.2f}**, Target: **{finances['prep_dumplings']} dumplings**, Griddles: **{finances['required_griddles']}**)."
                    
                elif action_data.get("action") == "update_event":
                    ev_id = action_data.get("event_id")
                    st_val = action_data.get("new_status", "Applied")
                    fmt_val = action_data.get("new_format", "Both Hot & Frozen")
                    db.update_event_status_and_format(ev_id, st_val, fmt_val)
                    clean_reply += f"\n\n---\n✅ **Action Completed:** Updated Event #{ev_id} to Status: **{st_val}** | Format: **{fmt_val}** in Google Sheets!"
            except Exception as e:
                clean_reply += f"\n\n*(Action could not complete: {e})*"

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
                "power_available": e_power
            }
            results = calculate_dumpling_finances(calc_input, config)
            db.add_event_to_pipeline({
                "event_name": e_name, "location": e_loc, "event_date": e_date,
                "category": e_cat, "product_format": e_format, "participation_status": e_status,
                "est_attendance": e_att, "operating_hours": e_hours,
                "distance_from_tucson_miles": e_dist, "vendor_fee_usd": e_fee, "power_available": e_power,
                "gross_revenue": results["gross_revenue"], "total_expenses": results["total_expenses"],
                "net_profit": results["net_profit"], "roi_text": results["roi_text"],
                "decision_tier": results["decision_tier"], "prep_dumplings": results["prep_dumplings"],
                "notes": f"Added by {current_user} (Griddles: {results['required_griddles']}) | Deadline: {e_deadline} | Src: " + st.session_state.prefill.get("source_url", "Manual")
            })
            st.success(f"Calculated: {results['decision_tier']} with Projected Net Profit of ${results['net_profit']:,.2f}! Saved to Tab 3.")

with tab_pipeline:
    st.subheader("📋 Active Opportunities Pipeline")
    pipeline_df = db.load_pipeline()
    
    def safe_float(val, default):
        try:
            if pd.isna(val) or val is None or str(val).strip() == "":
                return default
            return float(str(val).replace("$", "").replace(",", "").strip())
        except Exception:
            return default

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
                        "power_available": pwr_val
                    }
                    live_fin = calculate_dumpling_finances(recalc_input, config)
                    
                    rev_str = f"${live_fin['gross_revenue']:,.2f}"
                    cost_str = f"${live_fin['total_expenses']:,.2f}"
                    prof_str = f"${live_fin['net_profit']:,.2f}"
                    roi_str = live_fin['roi_text']
                    tier_str = live_fin['decision_tier']
                    tgt_str = f"{live_fin['prep_dumplings']:,}"
                    grid_str = f"{live_fin['required_griddles']} pcs"
                except Exception as e:
                    # If recalculation fails, display the actual error message
                    rev_str = f"Error: {e}"
                    cost_str = str(row.get("total_expenses", "$0.00"))
                    prof_str = str(row.get("net_profit", "$0.00"))
                    roi_str = str(row.get("roi_text", "0%"))
                    tier_str = str(row.get("decision_tier", "Review"))
                    tgt_str = str(row.get("prep_dumplings", "0"))
                    grid_str = "2 pcs"

                display_rows.append({
                    "ID": str(row.get("id", "")),
                    "Event Name": ev_name,
                    "Location": loc_val,
                    "Date": str(row.get("event_date", "")),
                    "Crowd": f"{int(att_val):,}",
                    "Griddles": grid_str,
                    "Format": fmt_val,
                    "Status": str(row.get("participation_status", "Discovered")),
                    "Tier": tier_str,
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
            "ID", "Event Name", "Location", "Date", "Crowd", "Griddles", "Format", "Status",
            "Tier", "Revenue", "Costs", "Profit", "ROI", "Target (pcs)", "Notes"
        ])

    st.caption("📊 Showing all columns responsively across screen width • Double-click any cell below to edit in-line!")
    
    edited_df = st.data_editor(
        final_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn(width="small", disabled=True),
            "Event Name": st.column_config.TextColumn(width="medium"),
            "Location": st.column_config.TextColumn(width="small"),
            "Date": st.column_config.TextColumn(width="small"),
            "Crowd": st.column_config.TextColumn(width="small"),
            "Griddles": st.column_config.TextColumn(width="small", disabled=True),
            "Format": st.column_config.SelectboxColumn(width="small", options=["Both Hot & Frozen", "Hot Cooked Only", "Frozen Only"]),
            "Status": st.column_config.SelectboxColumn(width="small", options=["Discovered", "Already Participating", "Booked", "Applied", "Reviewing", "Completed", "Declined"]),
            "Tier": st.column_config.TextColumn(width="small", disabled=True),
            "Revenue": st.column_config.TextColumn(width="small", disabled=True),
            "Costs": st.column_config.TextColumn(width="small", disabled=True),
            "Profit": st.column_config.TextColumn(width="small", disabled=True),
            "ROI": st.column_config.TextColumn(width="small", disabled=True),
            "Target (pcs)": st.column_config.TextColumn(width="small", disabled=True),
            "Notes": st.column_config.TextColumn(width="medium")
        },
        key="pipeline_editor"
    )
    
    if st.session_state.get("pipeline_editor") and "edited_rows" in st.session_state.pipeline_editor:
        changes = st.session_state.pipeline_editor["edited_rows"]
        if changes:
            for row_idx, updated_cols in changes.items():
                try:
                    target_id = int(final_table.iloc[int(row_idx)]["ID"])
                    new_status_val = updated_cols.get("Status", final_table.iloc[int(row_idx)]["Status"])
                    new_format_val = updated_cols.get("Format", final_table.iloc[int(row_idx)]["Format"])
                    
                    db.update_event_status_and_format(target_id, new_status_val, new_format_val)
                    st.success(f"Successfully saved edits for Event #{target_id} directly to Google Sheets!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Failed to save in-line edits: {err}")
    
    if final_table.empty:
        st.info("The pipeline has no active events yet. Submit an opportunity in Tab 2 to populate this table.")
