import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# Page Configuration & Modern Dark Glass Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="Visa Slot Predictor AI",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Palantir / Linear / Vision Pro Glassmorphism Aesthetic
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #070B14;
        color: #F3F4F6;
    }
    
    /* Main Background Glow */
    .stApp {
        background: radial-gradient(circle at 15% 15%, rgba(139, 92, 246, 0.12) 0%, transparent 40%),
                    radial-gradient(circle at 85% 85%, rgba(59, 130, 246, 0.12) 0%, transparent 40%),
                    #070B14;
    }
    
    /* Glassmorphism Cards */
    div[data-testid="stMetric"], div[data-testid="stBlock"] {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        padding: 20px;
    }

    /* Metric Label and Value Styling */
    div[data-testid="stMetricValue"] {
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Custom AI Score Circular Display */
    .prediction-hero-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(139, 92, 246, 0.3);
        box-shadow: 0 0 30px rgba(139, 92, 246, 0.15);
        border-radius: 24px;
        padding: 30px;
        text-align: center;
        backdrop-filter: blur(20px);
    }
    
    .score-ring {
        width: 140px;
        height: 140px;
        border-radius: 50%;
        border: 4px solid transparent;
        border-top: 4px solid #8B5CF6;
        border-right: 4px solid #3B82F6;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 15px auto;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
        animation: rotate 10s linear infinite;
    }

    /* Glowing Status Badges */
    .status-badge-high {
        background: rgba(34, 197, 94, 0.15);
        color: #4ADE80;
        border: 1px solid rgba(34, 197, 94, 0.4);
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    .timeline-log {
        border-left: 2px solid rgba(139, 92, 246, 0.4);
        padding-left: 15px;
        margin-bottom: 12px;
        font-size: 0.88rem;
    }
    
    /* Hide Streamlit Native Footers */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Auto-refresh dashboard every 60 seconds
st_autorefresh(interval=60 * 1000, key="visapredictor_autorefresh")

# ---------------------------------------------------------
# Data Loader & Engine Mock Infrastructure
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def load_slot_data():
    np.random.seed(42)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    data = []
    for _ in range(425):
        day = np.random.choice(days, p=[0.1, 0.1, 0.15, 0.35, 0.15, 0.08, 0.07])
        hour = np.random.choice(range(24))
        city = np.random.choice(["Hyderabad", "Chennai", "Delhi", "Mumbai", "Kolkata"], p=[0.35, 0.25, 0.2, 0.1, 0.1])
        data.append({"Day": day, "Hour": hour, "City": city})
    return pd.DataFrame(data)

df = load_slot_data()

# ---------------------------------------------------------
# Sidebar Navigation (Palantir / Linear Style)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🌌 **VISA PREDICTOR AI**")
    st.caption("Enterprise Availability Engine")
    st.markdown("---")
    
    menu = st.radio(
        "NAVIGATION",
        ["Dashboard", "Live Monitoring", "AI Analytics", "Client Matrix", "Settings"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("#### 🔔 Alert Configuration")
    enable_telegram = st.checkbox("Telegram Dispatch", value=True)
    bot_token = st.text_input("Bot Token", value="••••••••••••", type="password")
    chat_id = st.text_input("Chat ID", value="8941318936")
    
    st.markdown("---")
    st.caption("Engine Version: v2.4-Enterprise")
    st.caption("Status: 🟢 AI Engine Active")

# ---------------------------------------------------------
# Top Header Bar
# ---------------------------------------------------------
col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h1:
    st.title("Visa Slot Predictor AI")
    st.caption("Neural availability forecasting driven by real-time telemetric monitoring.")
with col_h2:
    st.selectbox("Target Country", ["🇮🇳 India (US Embassy/VAC)", "🇪🇸 Spain (BLS)", "🇩🇪 Germany (VFS)"])
with col_h3:
    st.selectbox("Visa Type", ["F-1 Student", "B1/B2 Visitor", "H-1B Work"])

st.markdown("---")

# ---------------------------------------------------------
# Main View Switcher
# ---------------------------------------------------------
if menu == "Dashboard":
    
    # --- HERO SECTION ---
    col_hero_1, col_hero_2, col_hero_3 = st.columns([1.2, 1, 1])
    
    with col_hero_1:
        st.markdown("""
        <div class="prediction-hero-card">
            <div style="font-size: 0.9rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px;">Prediction Confidence Today</div>
            <div class="score-ring">
                <span style="font-size: 2.2rem; font-weight: 800; color: #FFFFFF;">91%</span>
            </div>
            <span class="status-badge-high">VERY HIGH CONFIDENCE</span>
            <div style="margin-top: 15px; font-size: 0.95rem; color: #D1D5DB;">
                Expected Opening Window:<br><strong style="color: #3B82F6; font-size: 1.1rem;">08:30 PM – 09:15 PM</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_hero_2:
        st.metric("Active Monitored Slots", "1,250", "+14% vs yesterday")
        st.metric("Data Signals Processed", "425,000", "+12.4k/hr")

    with col_hero_3:
        st.metric("Engine Accuracy", "94.2%", "+0.8% auto-tuned")
        st.metric("Peak Probability City", "Hyderabad", "35% of total drops")

    st.markdown("---")

    # --- LIVE 3D HEATMAP & ANALYTICS ---
    col_map, col_logs = st.columns([2.2, 1])

    with col_map:
        st.subheader("🔥 Hourly Release Distribution Matrix")
        
        # Heatmap Construction
        heatmap_df = df.groupby(["Day", "Hour"]).size().reset_index(name="Drops")
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        fig_heat = px.density_heatmap(
            heatmap_df,
            x="Hour",
            y="Day",
            z="Drops",
            category_orders={"Day": days_order},
            color_continuous_scale=[[0, "#070B14"], [0.5, "#3B82F6"], [1.0, "#8B5CF6"]],
            labels={"Hour": "Hour of Day (UTC)", "Day": "Day"},
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9CA3AF"),
            height=320,
            margin=dict(l=10, r=10, t=20, b=10)
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_logs:
        st.subheader("⚡ Live Events Stream")
        st.markdown(f"""
        <div class="timeline-log"><span style="color: #9CA3AF;">08:42:10 PM</span> – System check: <strong>Hyderabad VAC</strong></div>
        <div class="timeline-log"><span style="color: #9CA3AF;">08:43:05 PM</span> – Telemetry read: 0 slots detected</div>
        <div class="timeline-log"><span style="color: #8B5CF6;">08:44:12 PM</span> – Pattern Match: <strong style="color: #8B5CF6;">Thursday 08:30 PM Pattern</strong></div>
        <div class="timeline-log"><span style="color: #22C55E;">08:45:00 PM</span> – <span class="status-badge-high">HIGH PROBABILITY TRIGGER</span></div>
        """, unsafe_allow_html=True)
        
        st.button("⚡ Dispatch Manual Test Trigger", use_container_width=True)

    st.markdown("---")

    # --- CITY PROBABILITY & CLIENT MATRIX ---
    col_cities, col_types = st.columns([1.5, 1])

    with col_cities:
        st.subheader("📍 Consular Post Probability Breakdown")
        city_counts = df["City"].value_counts().reset_index()
        city_counts.columns = ["Consulate", "Historical Drops"]
        
        fig_bar = px.bar(
            city_counts,
            x="Consulate",
            y="Historical Drops",
            color="Historical Drops",
            color_continuous_scale=["#3B82F6", "#8B5CF6"]
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9CA3AF"),
            height=280
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_types:
        st.subheader("🎯 Visa Type Distribution")
        fig_donut = px.pie(
            values=[60, 25, 15],
            names=["F-1 Student", "B1/B2 Visitor", "H-1B Work"],
            hole=0.6,
            color_discrete_sequence=["#8B5CF6", "#3B82F6", "#22C55E"]
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9CA3AF"),
            height=280,
            showlegend=False
        )
        st.plotly_chart(fig_donut, use_container_width=True)

elif menu == "Client Matrix":
    st.subheader("👥 Monitored Client Queue")
    
    # Client Management Grid
    client_data = pd.DataFrame([
        {"Client": "Alex Vance", "Visa": "F-1 Student", "Location": "Hyderabad", "Status": "Active Engine", "Probability": "91%", "Priority": "High"},
        {"Client": "Elena Rostova", "Visa": "B1/B2 Visitor", "Location": "Chennai", "Status": "Active Engine", "Probability": "78%", "Priority": "Medium"},
        {"Client": "Marcus Chen", "Visa": "H-1B Work", "Location": "Delhi", "Status": "Queued", "Probability": "45%", "Priority": "Low"},
        {"Client": "Priya Sharma", "Visa": "F-1 Student", "Location": "Mumbai", "Status": "Active Engine", "Probability": "88%", "Priority": "High"},
    ])
    
    st.dataframe(client_data, use_container_width=True)

else:
    st.info(f"The **{menu}** module is active and auto-updating from telemetric nodes.")
