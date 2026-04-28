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
    /* Menghilangkan padding agar peta penuh selayar */
    [data-testid="stAppViewContainer"] > section:nth-child(2) {
        padding: 0 !important;
    }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Efek Glassmorphism untuk Kartu Melayang */
    .floating-card {
        position: fixed;
        top: 30px;
        right: 30px;
        width: 320px;
        background: rgba(13, 17, 23, 0.75);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(222, 255, 154, 0.2);
        border-radius: 24px;
        padding: 25px;
        z-index: 1000;
        color: #e1e4e8;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
        font-family: 'Inter', sans-serif;
    }
    
    .metric-box {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 15px;
        padding: 12px;
        margin-bottom: 12px;
        border-left: 3px solid #deff9a;
    }
    
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 50px;
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Memaksa elemen st_folium agar tidak ada margin */
    iframe {
        display: block;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNGSI LOAD DATA
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
                # Mengatasi masalah koma/titik desimal
                df_raw[col] = pd.to_numeric(df_raw[col].astype(str).str.replace(',', '.'), errors='coerce')
        return df_raw.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    except:
        return pd.DataFrame()

@st.cache_data
def load_map_json():
    try:
        with open('peta_desa.json') as f:
            return json.load(f)
    except:
        return None

def ambil_info_lokasi(lat, lon, geo_data):
    if not geo_data: return "Luar Wilayah", "-"
    try:
        p = Point(lon, lat)
        for feat in geo_data['features']:
            if shape(feat['geometry']).contains(p):
                ds = feat['properties'].get('ds', 'Unknown')
                kc = feat['properties'].get('kec', '-')
                return ds, kc
    except: pass
    return "Luar Wilayah", "-"

# --- EKSEKUSI DATA ---
df = load_gsheets_data()
geo_desa = load_map_json()

if df.empty:
    st.error("Gagal terhubung ke Google Sheets.")
    st.stop()

# State Management
if 'clicked_id' not in st.session_state:
    st.session_state.clicked_id = df.iloc[-1]['id']

try:
    selected_row = df[df['id'] == st.session_state.clicked_id].iloc[0]
except:
    selected_row = df.iloc[-1]
    st.session_state.clicked_id = selected_row['id']

ds, kc = ambil_info_lokasi(selected_row['lat'], selected_row['lon'], geo_desa)

# --- PETA FULL SCREEN ---
m = folium.Map(
    location=[selected_row['lat'], selected_row['lon']], 
    zoom_start=13, 
    tiles="CartoDB dark_matter",
    zoom_control=False # Agar UI lebih bersih
)

# Layer Satelit
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google Satellite',
    name='Satelit',
    overlay=False
).add_to(m)

if geo_desa:
    folium.GeoJson(
        geo_desa, 
        style_function=lambda x: {'fillColor': '#238636', 'color': '#deff9a', 'weight': 1, 'fillOpacity': 0.05}
    ).add_to(m)

# Gambar Titik Sensor
for row in df.itertuples():
    is_opt = row.n >= 80 and 5.5 <= row.ph <= 6.8
    folium.CircleMarker(
        location=[row.lat, row.lon],
        radius=10,
        color="#deff9a" if is_opt else "#ff4b4b",
        fill=True,
        fill_opacity=0.8,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

# Tampilkan Peta selayar penuh
m_out = st_folium(m, width="100%", height=850, key=f"map_v2_{st.session_state.clicked_id}")

# Logika Interaksi Klik
if m_out and m_out.get("last_object_clicked_popup"):
    try:
        new_id = int(m_out["last_object_clicked_popup"].split(":")[1])
        if new_id != st.session_state.clicked_id:
            st.session_state.clicked_id = new_id
            st.rerun()
    except: pass

# --- FLOATING CARD (INFORMASI ANALISIS) ---
label_status = "KONDISI OPTIMAL" if selected_row['n'] >= 80 else "PERLU PERBAIKAN"
warna_badge = "#238636" if selected_row['n'] >= 80 else "#da3633"

card_html = f"""
<div class="floating-card">
    <h4 style="margin:0; color:#deff9a; font-size:10px; letter-spacing:1px;">WILDANTECH SYSTEM</h4>
    <h2 style="margin:5px 0 0 0; font-size:22px; font-weight:700;">Desa {ds}</h2>
    <p style="margin:0; font-size:13px; opacity:0.6;">Kec. {kc} | ID #{int(selected_row['id'])}</p>
    
    <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:15px 0;">
    
    <div class="metric-box">
        <span style="font-size:11px; opacity:0.7;">NITROGEN (N)</span><br>
        <b style="font-size:18px;">{selected_row['n']} <span style="font-size:12px; font-weight:400;">mg/kg</span></b>
    </div>
    
    <div class="metric-box">
        <span style="font-size:11px; opacity:0.7;">KEASAMAN (PH)</span><br>
        <b style="font-size:18px;">{selected_row['ph']}</b>
    </div>
    
    <div class="metric-box">
        <span style="font-size:11px; opacity:0.7;">KELEMBAPAN</span><br>
        <b style="font-size:18px;">{selected_row['moist']}%</b>
    </div>
    
    <div style="text-align:center; margin-top:15px;">
        <span class="status-badge" style="background:{warna_badge};">{label_status}</span>
    </div>
    
    <p style="font-size:10px; margin-top:20px; opacity:0.4; text-align:center;">
        Terakhir Update: {selected_row['tanggal']}<br>
        © 2026 WONOSOBO PRECISION AGRI
    </p>
</div>
"""

st.markdown(card_html, unsafe_allow_html=True)
