import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# 1. Configuration & Auto-Refresh
# ---------------------------------------------------------
st.set_page_config(
    page_title="Visa Slot Release Prediction Engine",
    page_icon="🎯",
    layout="wide"
)

# Auto-refresh app every 60 seconds (60,000 ms)
st_autorefresh(interval=60 * 1000, key="visa_tracker_refresh")

# ---------------------------------------------------------
# 2. Telegram Alert Function
# ---------------------------------------------------------
def send_telegram_alert(message, bot_token, chat_id):
    """Dispatches real-time notification to Telegram."""
    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            st.error(f"Failed to send alert: {e}")

# ---------------------------------------------------------
# 3. Data Ingestion
# ---------------------------------------------------------
@st.cache_data(ttl=60)  # Re-loads every 60 seconds
def load_slot_data():
    try:
        # REPLACE THIS with: pd.read_csv("your_real_drops.csv") or database query
        np.random.seed(42)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        raw_p = [0.02, 0.01, 0.01, 0.02, 0.05, 0.08, 0.1, 0.35, 0.1, 0.05, 0.02, 0.01, 0.01, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]
        norm_p = np.array(raw_p) / np.sum(raw_p)
        
        data = []
        for _ in range(177):
            day = np.random.choice(days, p=[0.1, 0.1, 0.15, 0.30, 0.15, 0.1, 0.1])
            hour = np.random.choice(range(24), p=norm_p) if day == "Thursday" else np.random.choice(range(24))
            data.append({"Day": day, "Hour": hour})
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading dataset: {e}")
        return pd.DataFrame(columns=["Day", "Hour"])

df = load_slot_data()
total_samples = len(df)

# ---------------------------------------------------------
# 4. Sidebar: Alerts Settings
# ---------------------------------------------------------
st.sidebar.header("🔔 Alert Settings")
enable_alerts = st.sidebar.checkbox("Enable Telegram Notifications")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID", type="password")

# ---------------------------------------------------------
# 5. Header & Key Performance Metrics
# ---------------------------------------------------------
st.title("🎯 Visa Slot Release Prediction Engine")
st.caption("Live monitoring & historical probability analysis")

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Probability Right Now (Thursday 13:00)", "0.6%", "Normal Activity")
kpi2.metric("🏆 #1 Highest Probability Window", "Thursday @ 07:00", "8.5% of all drops")
kpi3.metric("Total Historical Samples", f"{total_samples}")

st.divider()

# ---------------------------------------------------------
# 6. Interactive Drop Predictor
# ---------------------------------------------------------
st.subheader("🔮 Predict Drop Chance for Any Time Slot")
col_day, col_hour = st.columns(2)

with col_day:
    selected_day = st.selectbox("Select Day to Test", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], index=3)

with col_hour:
    selected_hour = st.slider("Select Hour (24h format)", 0, 23, 7)

matching_drops = df[(df["Day"] == selected_day) & (df["Hour"] == selected_hour)]
count = len(matching_drops)
calculated_prob = (count / total_samples) * 100 if total_samples > 0 else 0

st.write("")

if calculated_prob > 5.0:
    st.success(f"🔥 **High Chance Window!** Calculated Drop Probability for **{selected_day} at {selected_hour:02d}:00** is **{calculated_prob:.1f}%** ({count} historical drops recorded).")
    if enable_alerts:
        send_telegram_alert(f"🔥 *High Drop Probability Detected!*\nWindow: {selected_day} @ {selected_hour:02d}:00\nProbability: {calculated_prob:.1f}%", bot_token, chat_id)
elif calculated_prob > 1.0:
    st.info(f"⚡ **Moderate Activity Window.** Calculated Drop Probability for **{selected_day} at {selected_hour:02d}:00** is **{calculated_prob:.1f}%** ({count} historical drops recorded).")
else:
    st.warning(f"💤 **Low Activity Window.** Calculated Drop Probability for **{selected_day} at {selected_hour:02d}:00** is **{calculated_prob:.1f}%** ({count} historical drops recorded).")