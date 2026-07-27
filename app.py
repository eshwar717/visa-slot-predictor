import os.path
import re
import base64
import pandas as pd
from datetime import datetime
import streamlit as st

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ==========================================
# 1. STREAMLIT PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Visa Slot Release Engine", 
    page_icon="🔥", 
    layout="wide"
)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# ==========================================
# 2. HELPER: TEXT EXTRACTION & REGEX
# ==========================================
def parse_subject_details(df):
    if df.empty or 'subject' not in df.columns:
        return df

    visa_types = []
    vac_locations = []
    target_cities = []

    for subj in df['subject']:
        visa_match = re.search(r'\d+\s+([A-Z0-9/]+\([A-Za-z]+\))', str(subj))
        visa_types.append(visa_match.group(1) if visa_match else "Unknown")
        
        vac_match = re.search(r'-([A-Z\s]+VAC)', str(subj))
        vac_locations.append(vac_match.group(1).strip() if vac_match else "Unknown")
        
        city_match = re.search(r'\|\s*([A-Z\s]+)\s+slot-dates', str(subj))
        target_cities.append(city_match.group(1).strip() if city_match else "Unknown")

    df['visa_type'] = visa_types
    df['vac_location'] = vac_locations
    df['target_city'] = target_cities
    return df

def get_email_body(payload):
    """Recursively extracts the plain text or HTML body from the Gmail payload."""
    body_data = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] in ['text/plain', 'text/html']:
                data = part.get('body', {}).get('data', '')
                if data:
                    body_data += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                body_data += get_email_body(part)
    else:
        data = payload.get('body', {}).get('data', '')
        if data:
            body_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return body_data

def extract_target_months(body_text):
    """
    Scans the email body to extract target appointment months.
    Matches patterns like 'August 2026' or 'September 2026'.
    """
    pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(202[6-9])'
    matches = re.findall(pattern, body_text, re.IGNORECASE)
    
    if not matches:
        return "Unknown"
        
    unique_months = list(set([f"{m[0].capitalize()} {m[1]}" for m in matches]))
    unique_months.sort(key=lambda d: datetime.strptime(d, "%B %Y"))
    
    return ", ".join(unique_months)

# ==========================================
# 3. GMAIL AUTHENTICATION
# ==========================================
@st.cache_resource
def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

# ==========================================
# 4. DATA FETCHING & CACHING LOGIC
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_and_analyze_1000():
    service = get_gmail_service()
    query = "in:anywhere from:alerts@checkvisaslots.com"
    
    messages = []
    page_token = None
    
    while len(messages) < 1000:
        results = service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=500, 
            pageToken=page_token
        ).execute()
        
        fetched = results.get('messages', [])
        messages.extend(fetched)
        page_token = results.get('nextPageToken')
        
        if not page_token or not fetched:
            break

    messages = messages[:1000]
    total = len(messages)
    
    if total == 0:
        return pd.DataFrame()

    email_data = []

    # Fetch each email individually to guarantee stability and prevent connection resets
    for i, msg in enumerate(messages):
        try:
            response = service.users().messages().get(
                userId='me', id=msg['id'], format='full'
            ).execute()
            
            payload = response.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            internal_date_ms = int(response.get('internalDate', 0))
            timestamp = datetime.fromtimestamp(internal_date_ms / 1000.0)
            
            body_text = get_email_body(payload)
            
            slot_match = re.search(r'Minimum Available Slots:\s*(\d+)', body_text, re.IGNORECASE)
            available_slots = int(slot_match.group(1)) if slot_match else 1
            
            target_appointment_months = extract_target_months(body_text)
            
            email_data.append({
                'id': response['id'],
                'subject': subject,
                'available_slots': available_slots,
                'target_months': target_appointment_months,
                'timestamp': timestamp,
                'day_of_week': timestamp.strftime('%A'),
                'hour': timestamp.hour,
                'date': timestamp.strftime('%Y-%m-%d')
            })
            
        except Exception as e:
            # If Google drops the connection on a single email, skip it and keep the dashboard running
            print(f"[*] Skipped email {msg.get('id')} due to API error: {e}")
            continue

    df = pd.DataFrame(email_data)
    
    if not df.empty and 'timestamp' in df.columns:
        df = df.sort_values(by='timestamp', ascending=False).reset_index(drop=True)
    
    df = parse_subject_details(df)
    df.to_csv("visa_alerts_history.csv", index=False)
    
    return df

# ==========================================
# 5. USER EXPLANATION CARD
# ==========================================
def display_prediction_explanation():
    with st.expander("ℹ️ **Why am I seeing these predictions? (How the Engine Works)**"):
        st.markdown("""
        ### 🧠 How Predictions & Peak Windows Are Calculated
        
        This prediction engine uses **Historical Frequency Analysis** built on real-time data from visa alert logs (`alerts@checkvisaslots.com`).

        ---

        #### 📊 1. Primary Data Sources
        * **Timestamp Density:** Alerts are grouped into **1-hour time buckets** to find exact release shifts.
        * **Slot Volume Extraction:** The engine scans the email body payload for specific phrases (e.g., *Minimum Available Slots: 55*) to log exact availability.
        * **Target Month Extraction:** The engine extracts the exact future months (e.g., *August 2026*) the consulate is filling.
        * **Metadata Extraction:** Subject lines are automatically parsed to extract Visa Category, VAC Location, and Interview Consulate.

        ---

        #### 🎯 2. How "High-Volume Surges" Are Defined
        * **20+ Slot Rule:** If any single email alert indicates **more than 20 available slots** dropping at once, that date is officially classified as a **High-Volume Surge**. Tracking when this last happened reveals if the consulate is currently in an active batch-release cycle.
        """)

# ==========================================
# 6. MAIN DASHBOARD APPLICATION
# ==========================================
def main():
    with st.sidebar:
        st.title("⚡ Control Center")
        st.markdown("---")
        
        if st.button("🔄 Force Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.checkbox("Enable Telegram Notifications")
        st.text_input("Telegram Bot Token", type="password")
        st.text_input("Telegram Chat ID", type="password")
        
        st.info("💡 Tip: Keep this page open on your desktop to automatically receive live browser updates.")

    st.title("🔥 Visa Slot Release Engine")
    st.markdown("Real-time monitoring and predictive probability analytics")
    
    with st.spinner("Fetching full email payloads from Gmail (this may take a moment)..."):
        df = fetch_and_analyze_1000()
        
    if df.empty:
        st.warning("No visa alert emails found matching 'from:alerts@checkvisaslots.com'.")
        return

    # --- METRIC CALCULATIONS ---
    total_drops = len(df)
    
    day_counts = df['day_of_week'].value_counts()
    peak_day = day_counts.idxmax() if not day_counts.empty else "N/A"
    peak_day_pct = (day_counts.max() / total_drops * 100) if total_drops > 0 else 0
    
    hour_counts = df['hour'].value_counts()
    peak_hour = hour_counts.idxmax() if not hour_counts.empty else 0
    peak_time_window = f"{peak_hour:02d}:00 - {peak_hour:02d}:59"

    high_vol_alerts = df[df['available_slots'] > 20].sort_values(by='timestamp', ascending=False)
    
    if not high_vol_alerts.empty:
        last_surge_date = high_vol_alerts.iloc[0]['date']
        last_surge_slots = high_vol_alerts.iloc[0]['available_slots']
        last_surge_day = high_vol_alerts.iloc[0]['day_of_week']
        surge_display_str = f"{last_surge_date} ({last_surge_day})"
        surge_delta_str = f"Massive drop of {last_surge_slots} slots"
    else:
        surge_display_str = "No Surges Detected"
        surge_delta_str = "Awaiting >20 slot drop"

    # --- TOP METRIC CARDS ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Total Observed Drops", value=f"{total_drops}")
    with col2:
        st.metric(label="Peak Day", value=peak_day, delta=f"{peak_day_pct:.1f}% of total drops", delta_color="normal")
    with col3:
        st.metric(label="Peak Time Window", value=peak_time_window, delta="High Density")
    with col4:
        st.metric(label="Current Status", value="Active Monitoring", delta="Refreshing every 300s")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- SURGE METRIC CARD ---
    col_surge1, col_surge2 = st.columns([1, 3])
    with col_surge1:
        st.metric(label="🚨 Last High-Volume Surge", value=surge_display_str, delta=surge_delta_str, delta_color="off")
    with col_surge2:
        st.info("**What this means:** The engine now scans the internal email body. Any day where the consulate dumps **more than 20 slots** in a single alert is flagged as a 'High-Volume Surge'.")

    st.markdown("---")
    display_prediction_explanation()
    st.markdown("---")

    # --- METADATA BREAKDOWN COLUMNS ---
    st.subheader("📊 Release Distribution Breakdown")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**Top Visa Categories**")
        st.dataframe(df['visa_type'].value_counts(), use_container_width=True)

    with col_b:
        st.markdown("**Top Target Months**")
        # Ensure we only count known target months, not empty ones
        valid_months = df[df['target_months'] != 'Unknown']['target_months']
        st.dataframe(valid_months.value_counts(), use_container_width=True)

    with col_c:
        st.markdown("**Top  Cities**")
        st.dataframe(df['target_city'].value_counts(), use_container_width=True)

    st.markdown("---")

    # --- TABLE DISPLAY ---
    st.subheader("🔥 Release Log (Showing Up to 500 Recent Alerts)")
    
    display_cols = ['id', 'target_months', 'available_slots', 'subject', 'timestamp', 'day_of_week', 'hour', 'date', 'visa_type', 'vac_location', 'target_city']
    available_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[available_cols].head(500), 
        height=500, 
        use_container_width=True
    )

if __name__ == '__main__':
    main()
