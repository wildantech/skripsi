import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Wildantech | Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: MODERN GLASSMORPHISM & FULL SCREEN MAP ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > section:nth-child(2) { padding: 0 !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header, footer { visibility: hidden; }
    
    .floating-card {
        position: fixed;
        top: 20px;
        right: 20px;
        width: 300px;
        background: rgba(13, 17, 23, 0.85);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(222, 255, 154, 0.2);
        border-radius: 20px;
        padding: 20px;
        z-index: 1000;
        color: #f5f5f5;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    .metric-box {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 8px;
        border-left: 3px solid #deff9a;
    }

    .close-btn {
        position: absolute;
        top: 10px;
        right: 15px;
        color: #ff4b4b;
        cursor: pointer;
        font-weight: bold;
        font-size: 18px;
        text-decoration: none;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. LOAD DATA
@st.cache_data(ttl=60)
def load_gsheets_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_raw = conn.read(spreadsheet=url)
        df_raw.columns = df_raw.columns.str.strip()
        cols = ['lat', 'lon', 'n', 'p', 'k', 'ph', 'ec', 'temp', 'moist']
        for col in cols:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col].astype(str).str.replace(',', '.'), errors='coerce')
        return df_raw.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    except: return pd.DataFrame()

@st.cache_data
def load_map_json():
    try:
        with open('peta_desa.json') as f: return json.load(f)
    except: return None

# 3. LOGIKA KONTROL KARTU
if 'show_card' not in st.session_state:
    st.session_state.show_card = False
if 'clicked_id' not in st.session_state:
    st.session_state.clicked_id = None

df = load_gsheets_data()
geo_desa = load_map_json()

# PETA
m = folium.Map(location=[-7.35, 109.9], zoom_start=12, tiles="CartoDB dark_matter")
for row in df.itertuples():
    folium.CircleMarker(
        location=[row.lat, row.lon],
        radius=10,
        color="#deff9a" if row.n >= 80 else "#ff4b4b",
        fill=True,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

m_out = st_folium(m, width="100%", height=800, key="main_map")

# Logika Klik: Buka Kartu
if m_out and m_out.get("last_object_clicked_popup"):
    new_id = int(m_out["last_object_clicked_popup"].split(":")[1])
    st.session_state.clicked_id = new_id
    st.session_state.show_card = True
    st.rerun()

# --- TAMPILKAN KARTU JIKA AKTIF ---
if st.session_state.show_card and st.session_state.clicked_id is not None:
    sel = df[df['id'] == st.session_state.clicked_id].iloc[0]
    
    # Tombol Tutup (Streamlit Button yang dibuat melayang)
    with st.sidebar: # Kita selipkan di sidebar tersembunyi agar state-nya terjaga
        if st.button("Tutup Detail Lahan"):
            st.session_state.show_card = False
            st.rerun()

    # Render HTML Kartu
    html_content = f"""
    <div class="floating-card">
        <div style="margin-bottom:10px;">
            <small style="color:#deff9a">WILDANTECH MONITORING</small>
            <h3 style="margin:0">ID #{int(sel['id'])}</h3>
        </div>
        <div class="metric-box">
            <small>NITROGEN (N)</small><br>
            <b>{sel['n']} mg/kg</b>
        </div>
        <div class="metric-box">
            <small>KEASAMAN (PH)</small><br>
            <b>{sel['ph']}</b>
        </div>
        <div class="metric-box">
            <small>KELEMBAPAN</small><br>
            <b>{sel['moist']}%</b>
        </div>
        <p style="font-size:10px; opacity:0.5; margin-top:15px;">Klik tombol di kiri untuk menutup</p>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)
