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
st.sidebar.subheader("💰 Unit Economics & Assumptions")
config = {
    "hot_plate_price": st.sidebar.number_input("Hot Plate Menu Price ($)", value=13.0, step=0.5),
    "frozen_pack_price": st.sidebar.number_input("Frozen 4-Pack Price ($)", value=16.0, step=0.5),
    "ingredient_cogs": st.sidebar.number_input("Ingredient Cost / Dumpling ($)", value=0.42, step=0.01),
    "prep_labor_cogs": st.sidebar.number_input("Prep Labor / Dumpling ($)", value=0.18, step=0.01),
    "hourly_wage": st.sidebar.number_input("Staff Hourly Wage ($)", value=20.0, step=1.0),
    "max_plates_per_hour": st.sidebar.slider("Max Steamer Output (Plates/Hr)", 20, 90, 55),
    "frozen_upsell_pct": st.sidebar.slider("Frozen Take-Home Upsell %", 0.0, 0.5, 0.25)
}

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
    st.subheader("⚡ Quick Event Evaluator & Pipeline Adder")
    with st.form("quick_eval_form"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            e_name = st.text_input("Event Name", value="Scottsdale Celiac 5K + Treat")
            e_loc = st.text_input("Location", value="Scottsdale, AZ")
            e_date = st.text_input("Date", value="2026-11-01")
        with col_b:
            e_dist = st.number_input("Distance from Tucson (miles)", value=115.0, step=5.0)
            e_att = st.number_input("Estimated Attendance", value=800, step=50)
            e_hours = st.number_input("Operating Hours", value=5.0, step=0.5)
        with col_c:
            e_cat = st.selectbox("Category", ["Niche GF / Athletic", "General Mass / Street Fair", "Vegan / Wellness"])
            e_format = st.selectbox("Product Format", ["Both Hot & Frozen", "Hot Cooked Only", "Frozen Only"])
            e_status = st.selectbox("Participation Status", ["Discovered", "Already Participating", "Booked", "Applied", "Reviewing"])
            e_fee = st.number_input("Vendor Booth Fee ($)", value=150.0, step=25.0)
            e_power = st.checkbox("Power & Water Provided", value=False)
            
        submit_btn = st.form_submit_button("Run Financial Evaluation & Log to Pipeline")
        if submit_btn:
            calc_input = {
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
                "est_attendance": e_att, "gross_revenue": results["gross_revenue"],
                "total_expenses": results["total_expenses"], "net_profit": results["net_profit"],
                "roi_text": results["roi_text"], "decision_tier": results["decision_tier"],
                "prep_dumplings": results["prep_dumplings"], "notes": f"Added by {current_user}"
            })
            st.success(f"Calculated: {results['decision_tier']} with Projected Net Profit of ${results['net_profit']:,.2f}! Saved to Tab 3.")

with tab_pipeline:
    st.subheader("📋 Active Opportunities Pipeline")
    pipeline_df = db.load_pipeline()
    
    # EXACT 13 COLUMNS DEFINITION
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
    
    # Ensure every single key exists in the dataframe
    for key in column_map.keys():
        if key not in pipeline_df.columns:
            pipeline_df[key] = ""
            
    final_table = pipeline_df[list(column_map.keys())].copy()
    final_table = final_table.rename(columns=column_map)
    
    st.caption(f"📊 Showing all {len(final_table.columns)} columns across operations and finances")
    
    # Render with responsive container width
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
