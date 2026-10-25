import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

def authenticate_user():
    if "authenticated_user" in st.session_state and st.session_state.authenticated_user:
        return st.session_state.authenticated_user

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

st.sidebar.title(f"👤 Logged in as: {current_user}")
if st.sidebar.button("Log Out"):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Operational Economics")
config = {
    "item_menu_price": st.sidebar.number_input("Average Menu Item Price ($)", value=12.0, step=0.5, help="Average price per 4-dumpling serving"),
    "frozen_pack_price": st.sidebar.number_input("Frozen 4-Pack Price ($)", value=16.0, step=0.5),
    "ingredient_cogs": st.sidebar.number_input("Raw Ingredient Cost / Dumpling ($)", value=0.42, step=0.01),
    "hourly_wage": st.sidebar.number_input("Staff Hourly Wage ($)", value=20.0, step=1.0)
}

st.sidebar.caption("🍳 Griddle throughput rule: 24 dumplings / griddle every 12 mins (120 pcs/hr). 1 cook manages 2-3 griddles.")

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
    st.caption("Your confidential research workspace.")
    private_df = db.load_private_messages(current_user)
    ai_box = st.container(height=380)
    with ai_box:
        if private_df.empty:
            st.info(f"Welcome {current_user}! Ask Gemini to research any event, city, athletic race, or paste a URL to analyze.")
        for _, row in private_df.iterrows():
            with st.chat_message(row["role"]):
                st.write(row["message"])
                
    ai_input = st.chat_input("Ask about an event, festival, or date...", key="ai_scout_input")
    if ai_input:
        db.save_private_message(current_user, "user", ai_input)
        client = genai.Client(api_key=st.secrets.get("GEMINI_API_KEY", ""))
        prompt = f"""
        You are an event scouting and evaluation assistant for Huhu's House of Dumplings.
        The business offers all-natural, gluten-free, and plant-based/vegan Chinese dumplings based in Tucson, AZ.
        User prompt: '{ai_input}'
        
        Search the web for relevant upcoming events in Tucson, Phoenix metro, Southern AZ, or Utah.
        Extract location, dates, expected attendance, booth fees, and demographic alignment.
        Provide a concise evaluation and a clear recommendation.
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        db.save_private_message(current_user, "assistant", response.text)
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
                    client = genai.Client(api_key=st.secrets.get("GEMINI_API_KEY", ""))
                    enrich_prompt = f"""
                    Search the web for event details for: '{quick_query}'.
                    The user runs Huhu's House of Dumplings (gluten-free, vegan food company based in Tucson, AZ).
                    Extract the following into clean JSON:
                    - event_name (string)
                    - location (City, State)
                    - event_date (YYYY-MM-DD or date string)
                    - application_deadline (YYYY-MM-DD string when vendor/food registration closes; if unknown, estimate 30 days prior to event_date)
                    - distance_from_tucson_miles (float driving estimate from Tucson, AZ)
                    - estimated_attendance (integer estimate)
                    - operating_hours (float daily hours, default 6.0)
                    - vendor_fee_usd (float estimate, default 150.0)
                    - category ('Niche GF / Athletic', 'General Mass / Street Fair', 'Vegan / Wellness')
                    - power_available (boolean)
                    - primary_source_url (string URL where details were verified)
                    - source_summary (1-sentence summary of where data was verified, e.g. 'Found on official municipal arts festival vendor guide')
                    """
                    try:
                        import json
                        res = client.models.generate_content(
                            model='gemini-2.5-flash',
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
        st.info(f"🤖 **AI Auto-Enriched Data**: {st.session_state.prefill.get('source_summary', '')}{src_text}\n\n*Highlighted fields below contain parameters extracted directly by Gemini. Review and adjust any values as needed before saving.*")

    with st.form("quick_eval_form"):
        ai_tag = " 🤖 [AI]" if st.session_state.prefill.get("is_ai") else ""
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            e_name = st.text_input(f"Event Name{ai_tag}", value=st.session_state.prefill["name"])
            e_loc = st.text_input(f"Location{ai_tag}", value=st.session_state.prefill["loc"])
            e_date = st.text_input(f"Event Date{ai_tag}", value=st.session_state.prefill["date"])
            e_deadline = st.text_input(f"App Deadline{ai_tag}", value=st.session_state.prefill.get("deadline", "2026-10-25"))
            e_griddles = st.number_input("Number of Griddles in Setup", min_value=1, max_value=6, value=2, step=1)
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
                "estimated_attendance": e_att,
                "category": e_cat,
                "product_format": e_format,
                "operating_hours": e_hours,
                "num_griddles": e_griddles,
                "distance_from_tucson_miles": e_dist,
                "location": e_loc,
                "vendor_fee_usd": e_fee,
                "power_available": e_power
            }
            results = calculate_dumpling_finances(calc_input, config)
            db.add_event_to_pipeline({
                "event_name": e_name, "location": e_loc, "event_date": e_date,
                "category": e_cat, "product_format": e_format, "participation_status": e_status,
                "est_attendance": e_att, "gross_revenue": results["gross_revenue"],
                "total_expenses": results["total_expenses"], "net_profit": results["net_profit"],
                "roi_text": results["roi_text"], "decision_tier": results["decision_tier"],
                "prep_dumplings": results["prep_dumplings"],
                "notes": f"Added by {current_user} ({e_griddles} griddles) | Deadline: {e_deadline} | Src: " + st.session_state.prefill.get("source_url", "Manual")
            })
            st.success(f"Calculated: {results['decision_tier']} with Projected Net Profit of ${results['net_profit']:,.2f}! Saved to Tab 3.")

with tab_pipeline:
    st.subheader("📋 Active Opportunities Pipeline")
    pipeline_df = db.load_pipeline()
    
    column_map = {
        "id": "ID",
        "event_name": "Event Name",
        "location": "Location",
        "event_date": "Date",
        "product_format": "Format",
        "participation_status": "Status",
        "decision_tier": "Tier",
        "gross_revenue": "Gross Revenue ($)",
        "total_expenses": "Total Costs ($)",
        "net_profit": "Net Profit ($)",
        "roi_text": "ROI",
        "prep_dumplings": "Dumplings Target (pcs)",
        "notes": "Notes"
    }
    
    for key in column_map.keys():
        if key not in pipeline_df.columns:
            pipeline_df[key] = ""
            
    final_table = pipeline_df[list(column_map.keys())].copy()
    final_table = final_table.rename(columns=column_map)
    
    st.caption(f"📊 Showing all {len(final_table.columns)} columns across operations and finances")
    
    st.dataframe(
        final_table,
        use_container_width=True,
        hide_index=True
    )
    
    if len(pipeline_df.dropna(how="all")) == 0 or (pipeline_df["event_name"].astype(str).str.strip() == "").all():
        st.info("ℹ️ The pipeline has no active events yet. Submit an opportunity in Tab 2 to populate this table.")
        
    st.markdown("---")
    st.subheader("🔄 Update Event Status & Format")
    col_u1, col_u2, col_u3, col_u4 = st.columns([2, 2, 2, 1])
    with col_u1:
        numeric_ids = pd.to_numeric(pipeline_df["id"], errors="coerce").dropna().astype(int).tolist()
        selected_id = st.selectbox("Select Event ID", numeric_ids if numeric_ids else [1])
    with col_u2:
        new_stat = st.selectbox("Participation Status", ["Already Participating", "Booked", "Applied", "Reviewing", "Discovered", "Completed", "Declined"])
    with col_u3:
        new_fmt = st.selectbox("Product Format", ["Both Hot & Frozen", "Hot Cooked Only", "Frozen Only"])
    with col_u4:
        st.write("")
        st.write("")
        if st.button("Update"):
            db.update_event_status_and_format(selected_id, new_stat, new_fmt)
            st.success(f"Event #{selected_id} updated!")
            st.rerun()
