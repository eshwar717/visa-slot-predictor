import streamlit as st
import pandas as pd
import os
import time
import plotly.express as px  # <-- New library for the beautiful charts

st.set_page_config(page_title="Visa Slot Release Engine", layout="wide")

@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists("visa_alerts_history.csv"):
        return pd.DataFrame()
    return pd.read_csv("visa_alerts_history.csv", parse_dates=["timestamp"])

def main():
    st.title("🔥 Visa Slot Release Engine")
    st.markdown("Real-time monitoring and predictive probability analytics")
    
    df = load_data()
    
    if df.empty:
        st.warning("Waiting for data. Ensure your background sync script is running.")
        time.sleep(10)
        st.rerun()
        return

    # --- METRICS ---
    total_drops = len(df)
    day_counts = df['day_of_week'].value_counts()
    peak_day = day_counts.idxmax() if not day_counts.empty else "N/A"
    
    hour_counts = df['hour'].value_counts()
    peak_hour = hour_counts.idxmax() if not hour_counts.empty else 0
    peak_time_window = f"{peak_hour:02d}:00 - {peak_hour:02d}:59"

    high_vol = df[df['available_slots'] > 20].sort_values(by='timestamp', ascending=False)
    if not high_vol.empty:
        surge_str = f"{high_vol.iloc[0]['date']} ({high_vol.iloc[0]['day_of_week']})"
        surge_delta = f"Drop of {high_vol.iloc[0]['available_slots']} slots"
    else:
        surge_str, surge_delta = "No Surges Detected", "Awaiting drop"

    # --- TOP ROW CARDS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Observed Drops", f"{total_drops}")
    col2.metric("Peak Day", peak_day)
    col3.metric("Peak Time Window", peak_time_window)
    col4.metric("🚨 Last Massive Surge", surge_str, delta=surge_delta, delta_color="off")

    st.markdown("---")

    # ==========================================
    # LATEST AVAILABILITY MATRIX 
    # ==========================================
    st.subheader("📍 Latest Availability by Consulate")
    
    available_visas = [v for v in df['visa_type'].unique() if v != "Unknown"]
    
    if available_visas:
        selected_visa = st.selectbox("Filter by Visa Type:", available_visas)
        visa_df = df[df['visa_type'] == selected_visa]
        latest_by_city = visa_df.sort_values('timestamp', ascending=False).drop_duplicates(subset=['target_city'], keep='first')
        
        display_df = latest_by_city[['target_city', 'target_months', 'available_slots', 'timestamp']].copy()
        display_df = display_df.rename(columns={
            'target_city': 'Consulate Location',
            'target_months': 'Availability Seen For',
            'available_slots': 'Volume (Slots)',
            'timestamp': 'Last Alert Received'
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Not enough parsed visa types yet to build the matrix.")

    st.markdown("---")

    # ==========================================
    # INTERACTIVE CHARTS (Like your screenshot)
    # ==========================================
    st.subheader("📊 Visa Slot Analytics")
    
    # Filter out 'Unknown' cities so the charts look clean
    chart_df = df[df['target_city'] != 'Unknown']
    
    if not chart_df.empty:
        # 1. The Donut Chart (Volume by Consulate)
        st.markdown("**Issuances (Slot Volume) by Consulate**")
        
        # Group the data to get total slots per city
        city_volume = chart_df.groupby('target_city')['available_slots'].sum().reset_index()
        
        fig_donut = px.pie(
            city_volume, 
            values='available_slots', 
            names='target_city', 
            hole=0.4, # This turns the pie chart into a donut chart
            color_discrete_sequence=px.colors.sequential.Blues_r # Blue theme from screenshot
        )
        
        # Put the labels on the outside and format the legend to match the screenshot
        fig_donut.update_traces(textposition='outside', textinfo='percent+label')
        fig_donut.update_layout(
            showlegend=True, 
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        
        st.plotly_chart(fig_donut, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. The Area Chart (Monthly/Daily issuances over time)
        st.markdown("**Slot Releases by Consulate Over Time**")
        
        # Group the data by Date AND City
        time_df = chart_df.groupby(['date', 'target_city'])['available_slots'].sum().reset_index()
        
        fig_area = px.area(
            time_df, 
            x='date', 
            y='available_slots', 
            color='target_city',
            markers=True # Adds the little dots on the lines like your screenshot
        )
        
        fig_area.update_layout(
            xaxis_title="Date", 
            yaxis_title="Total Slots Released",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_area, use_container_width=True)

    else:
        st.info("Gathering more data to build the charts...")

    st.markdown("---")

    # --- RAW DATA LOG ---
    with st.expander("View Raw Release Log"):
        display_cols = ['target_months', 'available_slots', 'subject', 'timestamp', 'visa_type', 'vac_location', 'target_city']
        st.dataframe(df[[c for c in display_cols if c in df.columns]].head(100), height=300)

    # Auto-refresh the dashboard every 60 seconds
    time.sleep(60)
    st.rerun()

if __name__ == '__main__':
    main()
    # ==========================================
    # LATEST VISUAL PROOF (SCREENSHOTS)
    # ==========================================
    st.subheader("📸 Latest Screenshot Evidence")
    
    # Check if the screenshots column exists (older CSVs might not have it yet)
    if 'screenshots' in df.columns:
        # Filter for rows that actually have an image saved
        has_images = df[df['screenshots'] != ""]
        
        if not has_images.empty:
            # Create columns to show the 3 most recent screenshots side-by-side
            img_cols = st.columns(3)
            
            for index, row in has_images.head(3).reset_index().iterrows():
                # Some emails might have multiple screenshots attached, grab the first one
                first_img_path = row['screenshots'].split(', ')[0]
                
                with img_cols[index]:
                    st.image(first_img_path, caption=f"{row['target_city']} - {row['visa_type']}")
                    st.caption(f"Alert time: {row['timestamp']}")
        else:
            st.info("No screenshots found in recent alerts yet.")
    else:
        st.info("Waiting for background engine to sync new screenshot data...")
        
    st.markdown("---")
