import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- PASSWORD GATE (MUST BE AT THE VERY TOP OF THE FILE) ---
def check_password():
    """Returns True if the user enters the correct security credentials."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
        
    if st.session_state.password_correct:
        return True

    # Render a clean, standalone login page
    st.markdown("<h1 style='text-align: center; color: #E74C3C;'>🥟 Huhu's Command Portal</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Enter Team Workspace Password", type="password")
        # Matches against the encrypted Streamlit Secrets environment variable
        correct_pw = st.secrets.get("WORKSPACE_PASSWORD", "Dumps2026")
        
        if password == correct_pw:
            st.session_state.password_correct = True
            st.rerun()
        elif password:
            st.error("Incorrect security credentials. Please try again.")
            
    return False

if not check_password():
    st.stop() # 🛑 Stops execution immediately if wrong password

# ====================================================================
# SECURED APP CODE (Only runs after entering correct password)
# ====================================================================
import database as db
from engine import calculate_dumpling_finances

db.initialize_database()

st.sidebar.title("🥟 Huhu's Command Portal")
current_user = st.sidebar.selectbox("Active Team Member Profile", ["Andrew", "Whitney"])

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

st.sidebar.markdown("---")
st.sidebar.caption("All adjustments automatically recalculate downstream profit margins.")

tab_shared, tab_private, tab_pipeline = st.tabs([
    "👥 Shared Team Board", 
    "🤫 My Private AI Scout", 
    "📊 Opportunities Pipeline"
])

# --- TAB 1: SHARED TEAM BOARD ---
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

# --- TAB 2: PRIVATE AI SCOUT ---
with tab_private:
    st.subheader(f"🧠 Private Gemini Scout for {current_user}")
    st.caption(f"Your private scratchpad. Conversations here are strictly confidential to {current_user}.")
    
    private_df = db.load_private_messages(current_user)
    ai_box = st.container(height=380)
    with ai_box:
        if private_df.empty:
            st.info("Ask Gemini to research any event, city, athletic race, or paste a URL to analyze.")
        for _, row in private_df.iterrows():
            with st.chat_message(row["role"]):
                st.write(row["message"])
                
    ai_input = st.chat_input("Ask about an event, festival, or date...", key="ai_scout_input")
    if ai_input:
        db.save_private_message(current_user, "user", ai_input)
        
        # Grounded Gemini Execution
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
            e_fee = st.number_input("Vendor Booth Fee ($)", value=150.0, step=25.0)
            e_power = st.checkbox("Power & Water Provided", value=False)
            
        submit_btn = st.form_submit_button("Run Financial Evaluation & Log to Pipeline")
        
        if submit_btn:
            calc_input = {
                "estimated_attendance": e_att,
                "category": e_cat,
                "operating_hours": e_hours,
                "distance_from_tucson_miles": e_dist,
                "location": e_loc,
                "vendor_fee_usd": e_fee,
                "power_available": e_power
            }
            results = calculate_dumpling_finances(calc_input, config)
            
            db.add_event_to_pipeline({
                "event_name": e_name, "location": e_loc, "event_date": e_date,
                "category": e_cat, "est_attendance": e_att, "gross_revenue": results["gross_revenue"],
                "total_expenses": results["total_expenses"], "net_profit": results["net_profit"],
                "roi_text": results["roi_text"], "decision_tier": results["decision_tier"],
                "prep_dumplings": results["prep_dumplings"], "status": "Discovered",
                "notes": f"Added by {current_user}"
            })
            st.success(f"Calculated: {results['decision_tier']} with Projected Net Profit of ${results['net_profit']:,.2f}! Saved to Tab 3.")

# --- TAB 3: PIPELINE & ACTION TRACKER ---
with tab_pipeline:
    st.subheader("📋 Active Opportunities Pipeline")
    pipeline_df = db.load_pipeline()
    if pipeline_df.empty:
        st.info("The pipeline is currently empty. Add events via Tab 2.")
    else:
        st.dataframe(
            pipeline_df[["id", "event_name", "location", "event_date", "decision_tier", "gross_revenue", "total_expenses", "net_profit", "roi_text", "prep_dumplings", "status"]],
            use_container_width=True, hide_index=True
        )
        st.markdown("---")
        st.subheader("🔄 Update Event Status")
        col_u1, col_u2, col_u3 = st.columns([2, 2, 1])
        with col_u1:
            selected_id = st.selectbox("Select Event ID to Update", pipeline_df["id"].tolist())
        with col_u2:
            new_stat = st.selectbox("Set New Status", ["Discovered", "Reviewing", "Applied", "Booked", "Declined"])
        with col_u3:
            st.write("")
            st.write("")
            if st.button("Update Status"):
                db.update_event_status(selected_id, new_stat)
                st.success(f"Event #{selected_id} updated to '{new_stat}'!")
                st.rerun()
