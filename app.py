import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI LAYOUT PENUH
st.set_page_config(
    page_title="Wildantech | Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed" # Sembunyikan sidebar agar fokus ke peta
)

# --- CSS: MODERN GLASSMORPHISM & FULL SCREEN MAP ---
st.markdown("""
    <style>
    /* Menghilangkan padding bawaan streamlit agar peta bisa penuh */
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header { visibility: hidden; }
    
    /* Efek Glassmorphism untuk Kartu Melayang */
    .floating-card {
        position: fixed;
        top: 20px;
        right: 20px;
        width: 350px;
        background: rgba(13, 17, 23, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(222, 255, 154, 0.2);
        border-radius: 20px;
        padding: 25px;
        z-index: 9999;
        color: white;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
    }
    
    .metric-box {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #deff9a;
    }
    
    .status-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 50px;
        font-size: 10px;
        font-weight: bold;
        text-transform: uppercase;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNGSI LOAD DATA (Sama seperti sebelumnya)
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

def ambil_info_lokasi(lat, lon, geo_data):
    if not geo_data: return "Luar Wilayah", "-"
    try:
        p = Point(lon, lat)
        for feat in geo_data['features']:
            if shape(feat['geometry']).contains(p):
                return feat['properties'].get('ds', 'Unknown'), feat['properties'].get('kec', '-')
    except: pass
    return "Luar Wilayah", "-"

# --- PROSES UTAMA ---
df = load_gsheets_data()
geo_desa = load_map_json()

if 'clicked_id' not in st.session_state:
    st.session_state.clicked_id = df.iloc[-1]['id']

selected_row = df[df['id'] == st.session_state.clicked_id].iloc[0]
ds, kc = ambil_info_lokasi(selected_row['lat'], selected_row['lon'], geo_desa)

# --- TAMPILAN PETA (FULL SCREEN) ---
m = folium.Map(
    location=[selected_row['lat'], selected_row['lon']], 
    zoom_start=13, 
    tiles="CartoDB dark_matter",
    control_scale=True
)

# Tambahkan Layer Satelit sebagai pilihan
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google',
    name='Google Satellite',
    overlay=False,
    control=True
).add_to(m)
folium.LayerControl().add_to(m)

if geo_desa:
    folium.GeoJson(geo_desa, style_function=lambda x: {'fillColor': '#238636', 'color': '#4caf50', 'weight': 1, 'fillOpacity': 0.1}).add_to(m)

for row in df.itertuples():
    is_opt = row.n >= 80 and 5.5 <= row.ph <= 6.8
    folium.CircleMarker(
        location=[row.lat, row.lon],
        radius=10,
        color="#deff9a" if is_opt else "#ff4b4b",
        fill=True,
        fill_opacity=0.9,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

# Tampilkan Peta
m_out = st_folium(m, width="100%", height=800, key=f"map_{st.session_state.clicked_id}")

# Logika Klik Peta
if m_out and m_out.get("last_object_clicked_popup"):
    try:
        new_id = int(m_out["last_object_clicked_popup"].split(":")[1])
        if new_id != st.session_state.clicked_id:
            st.session_state.clicked_id = new_id
            st.rerun()
    except: pass

# --- FLOATING CARD (INFORMASI ANALISIS) ---
st.markdown(f"""
    <div class="floating-card">
        <h4 style="margin:0; color:#deff9a; font-size:12px;">WILDANTECH MONITORING</h4>
        <h2 style="margin:5px 0 0 0; font-size:24px;">Desa {ds}</h2>
        <p style="margin:0; font-size:14px; opacity:0.7;">Kecamatan {kc} | ID #{int(selected_row['id'])}</p>
        <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:15px 0;">
        
        <div class="metric-box">
            <small>Nitrogen (N)</small><br>
            <b style="font-size:20px;">{selected_row['n']} <span style="font-size:12px;">mg/kg</span></b>
        </div>
        
        <div class="metric-box">
            <small>Keasaman (pH)</small><br>
            <b style="font-size:20px;">{selected_row['ph']}</b>
        </div>
        
        <div class="metric-box">
            <small>Kelembapan</small><br>
            <b style="font-size:20px;">{selected_row['moist']}%</b>
        </div>
        
        <div class="status-badge" style="background:{"#238636" if selected_row['n'] >= 80 else "#da3633"};">
            Status: {"Optimal" if selected_row['n'] >= 80 else "Perlu Nutrisi"}
        </div>
        
        <p style="font-size:11px; margin-top:20px; opacity:0.5;">
            Update Terakhir: {selected_row['tanggal']}<br>
            Wonosobo Precision Agriculture 2026
        </p>
    </div>
    """, unsafe_allow_html=True)
